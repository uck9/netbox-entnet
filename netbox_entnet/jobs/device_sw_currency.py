from core.choices import JobIntervalChoices
from netbox.jobs import JobRunner, system_job
from dcim.models import DeviceType
from enum import Enum
from typing import List, Dict, Optional
from netbox_entnet.utils import get_plugin_setting
import logging

logger = logging.getLogger('netbox.netbox_entnet.jobs')

name = "Device SW Currency Review"

class CurrencyStatus(str, Enum):
    TARGET_ACTIVE = get_plugin_setting('TARGET_ACTIVE')
    ACCEPTED_ACTIVE = get_plugin_setting('ACCEPTED_ACTIVE')
    EXEMPTED = get_plugin_setting('EXEMPTED')
    UPGRADE_REQUIRED = get_plugin_setting('UPGRADE_REQUIRED')
    UPGRADE_REQUIRED_RETIRED = get_plugin_setting('UPGRADE_REQUIRED_RETIRED')

@system_job(interval=JobIntervalChoices.INTERVAL_HOURLY)
class DeviceSwCurrencyReview(JobRunner):

    class Meta:
        name = "Netbox EntNet - Calculate Device Software Currency"

    SOFTWARE_VERSION_MGMT = "software_version_mgmt"
    CF_SOFTWARE_VERSION = "software_version"
    CF_CURRENCY_STATUS = "software_currency_status"
    CF_VERSION_TARGET = "software_version_target"
    CF_CURRENCY_NOTES = "software_currency_notes"

    def log(self, message: str):
        self.job.data.setdefault('log', []).append({'message': message})

    def check_for_role(self, version_data: List[Dict], role: str) -> Optional[Dict]:
        return next((entry for entry in version_data if entry.get('role') == role), None)

    def is_valid_version_data(self, version_data: List[Dict]) -> bool:
        default = self.check_for_role(version_data, 'default')
        if not default:
            self.log('Version data missing default role')
            return False

        for role_data in version_data:
            role = role_data.get('role')
            versions = role_data.get('versions', {})
            if not isinstance(role, str):
                return False
            if not isinstance(versions.get('accepted_active_versions'), list):
                return False
            if not isinstance(versions.get('retired_versions'), dict):
                return False
            target = versions.get('target_active_version')
            if not isinstance(target, list) or len(target) != 1:
                return False

        return True

    def lint_software_version_data(self, version_data: List[Dict]) -> bool:
        if not self.is_valid_version_data(version_data):
            self.log('Version data failed lint check')
            return False
        self.log('Version data passed lint check')
        return True

    def sw_currency_check(
        self,
        sw_version: str,
        current_status: str,
        current_target: str,
        version_data: List[Dict],
        device_role: str = 'default'
    ) -> Dict:

        role_data = self.check_for_role(version_data, device_role) or \
                    self.check_for_role(version_data, 'default')

        if not role_data:
            self.log("No valid role data found, skipping check")
            return {}

        versions = role_data['versions']
        target_version = versions['target_active_version'][0]
        status = CurrencyStatus.UPGRADE_REQUIRED
        notes = ""

        if sw_version in versions['retired_versions']:
            status = CurrencyStatus.UPGRADE_REQUIRED_RETIRED
            notes = f"Retirement Reason: {versions['retired_versions'][sw_version]}"
        elif sw_version in versions['accepted_active_versions']:
            status = CurrencyStatus.ACCEPTED_ACTIVE
        elif sw_version in versions['target_active_version']:
            status = CurrencyStatus.TARGET_ACTIVE

        update_required = current_status != status or current_target != target_version

        return {
            "current_version": sw_version,
            "software_version_target": target_version,
            "software_currency_status": status,
            "software_currency_notes": notes,
            "update_data": update_required
        }

    def update_custom_field(self, device, field: str, new_value) -> bool:
        current_value = device.cf.get(field)
        if current_value != new_value:
            self.log(f"[{device.name}] Updating '{field}'': [{current_value}] -> [{new_value}]")
            device.custom_field_data[field] = new_value
            return True
        return False

    def process_device_version_info(self):
        dev_types = [dt for dt in DeviceType.objects.all() if dt.cf.get(self.SOFTWARE_VERSION_MGMT)]

        for dev_type in dev_types:
            version_data = dev_type.cf.get(self.SOFTWARE_VERSION_MGMT)
            message = f'{dev_type.model} - Processing version data'
            self.job.data['log'].append({'message': f'{message}' })

            if not self.lint_software_version_data(version_data):
                continue

            for device in dev_type.instances.exclude(primary_ip4__isnull=True):

                result = self.sw_currency_check(
                    device.cf.get(self.CF_SOFTWARE_VERSION),
                    device.cf.get(self.CF_CURRENCY_STATUS),
                    device.cf.get(self.CF_VERSION_TARGET),
                    version_data,
                    device.role.slug
                )

                if not result.get("update_data"):
                    continue

                updated = False
                updated |= self.update_custom_field(device, self.CF_VERSION_TARGET, result['software_version_target'])

                if device.cf.get(self.CF_SOFTWARE_VERSION) is not None and \
                   device.cf.get(self.CF_CURRENCY_STATUS) != CurrencyStatus.EXEMPTED:

                    updated |= self.update_custom_field(device, self.CF_CURRENCY_STATUS, result['software_currency_status'])

                    if result['software_currency_status'] == CurrencyStatus.UPGRADE_REQUIRED_RETIRED:
                        updated |= self.update_custom_field(device, self.CF_CURRENCY_NOTES, result['software_currency_notes'])
                    elif "Retirement" in (device.cf.get(self.CF_CURRENCY_NOTES) or ''):
                        updated |= self.update_custom_field(device, self.CF_CURRENCY_NOTES, "")

                if updated:
                    device.full_clean()
                    device.save()

    def lint_device_version_info(self):
        for dev_type in DeviceType.objects.all():
            version_data = dev_type.cf.get(self.SOFTWARE_VERSION_MGMT)
            if version_data:
                self.log(f"Device-Type: {dev_type.model} - Linting version data")
                self.lint_software_version_data(version_data)
            else:
                self.log(f"Device-Type: {dev_type.model} - No software version data")

    def run(self, *args, **kwargs):
        if not self.job.data:
            self.job.data = {}
            self.job.data.update({'log': [] })
            self.job.save()

        try:
            self.process_device_version_info()
            self.job.save()

        except Exception as e:
            logger.warning('Job encountered a warning')
            logger.error(str(e))
            raise