from netbox.plugins import get_plugin_config

def get_plugin_setting(setting_name):
    return get_plugin_config('netbox_entnet', setting_name)