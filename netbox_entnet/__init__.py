"""Top-level package for Netbox Enterprise Networks Plugin."""
from .version import __version__
from netbox.plugins import PluginConfig


class EntNetConfig(PluginConfig):
    name = "netbox_entnet"
    verbose_name = "Netbox Enterprise Networks Plugin"
    description = "Netbox Enterprise Networks Plugin"
    author = 'Nate Reeves'
    author_email = 'nathan.a.reeves@gmail.com'
    version = __version__
    base_url = "netbox_entnet"

    def ready(self):
        super().ready()
        import netbox_entnet.signals
        from .jobs import DeviceSwCurrencyReview

config = EntNetConfig
