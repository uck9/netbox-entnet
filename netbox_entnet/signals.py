import logging

from django.dispatch import receiver
from django.db.models.signals import post_save, m2m_changed
from django.db import transaction
from ipam.models import IPAddress, VRF
from dcim.models import Device
from tenancy.models import Tenant
from extras.models import Tag
from .utils import get_plugin_setting

logger = logging.getLogger('netbox.netbox_entnet.signals')

@receiver(post_save, sender=IPAddress)
def handle_ip_post_save(sender, instance, **kwargs):
    # Ensure assigned to interface
    if not instance.assigned_object_type or instance.assigned_object_type.model != 'interface':
        return

    if not instance.assigned_object_id:
        return

    # Defer execution until after full DB commit
    transaction.on_commit(lambda: apply_tags_and_vrf_to_primary_device_ip(instance))


def apply_tags_and_vrf_to_primary_device_ip(ip):
    try:
        NETWORK_MGMT_TAG_SLUG = get_plugin_setting('NETWORK_MGMT_TAG_SLUG') # Tag to track network management IP Addresses
        MANUFACTURER_NAME_SLUGS = get_plugin_setting('MANUFACTURER_NAME_SLUGS') # Devices we want to run this automation for
        SKIP_DISCOVERY_TAG_SLUG = get_plugin_setting('SKIP_DISCOVERY_TAG_SLUG')  # Tag on IP to skip automation
        TENANT_TAG_TO_IP_TAG = get_plugin_setting('TENANT_TAG_TO_IP_TAG') # Map tenant tag names to IP Address Tags

        # Only process IPs assigned to an interface
        if not ip.assigned_object_type or ip.assigned_object_type.model != 'interface':
            logger.info("IP not assigned to an interface")
            return

        interface = ip.assigned_object
        device = getattr(interface, 'device', None)
        if not device:
            logger.info("Not a device")
            return

        # Only process if this is the device’s primary IP
        if ip not in {device.primary_ip4, device.primary_ip6}:
            return

        # Only Selected Manufacturers devices
        if device.device_type.manufacturer.slug.lower() not in [m.lower() for m in MANUFACTURER_NAME_SLUGS]:
            return

        # Add network mgmt tag
        tag_slugs = {tag.slug for tag in ip.tags.all()}
        try:
            mgmt_tag = Tag.objects.get(slug=NETWORK_MGMT_TAG_SLUG)
            if mgmt_tag.slug not in tag_slugs:
                ip.tags.add(mgmt_tag)
        except Tag.DoesNotExist:
            logger.warning(f"Missing tag: '{NETWORK_MGMT_TAG_SLUG}'")

        # Skip if IP has the Discovery Exempt Tag 
        if SKIP_DISCOVERY_TAG_SLUG in tag_slugs:
            logger.info("Discovery Exempt tag exists - Exiting")
            return

        # Add tenant-specific tag only if none of the mapped tags already exist
        existing_ip_tag_slugs = {tag.slug for tag in ip.tags.all()}
        allowed_ip_tag_slugs = set(TENANT_TAG_TO_IP_TAG.values())

        # Skip if any tenant-based tag already exists
        if not existing_ip_tag_slugs & allowed_ip_tag_slugs:
            tenant_slug = getattr(ip.tenant, "slug", None)
            if tenant_slug in TENANT_TAG_TO_IP_TAG:
                target_tag_slug = TENANT_TAG_TO_IP_TAG[tenant_slug]
                try:
                    tenant_tag = Tag.objects.get(slug=target_tag_slug)
                    ip.tags.add(tenant_tag)
                except Tag.DoesNotExist:
                    logger.warning(f"Missing tag: '{target_tag_slug}'")
        
        # Ensure VRF is set to the default if nothing is selected.
        if ip.vrf is None:
            try:
                DEFAULT_VRF_NAME = get_plugin_setting('DEFAULT_VRF_NAME')
                default_vrf = VRF.objects.get(name=DEFAULT_VRF_NAME)
                ip.vrf = default_vrf
                ip.save()
                return
            except VRF.DoesNotExist:
                logger.warning(f"VRF '{DEFAULT_VRF_NAME}' not found. Skipping VRF assignment.")
                return  # Quit early if VRF is missing

    except Exception as e:
        logger.error(f"Error in m2m_changed for IP address: {e}")
