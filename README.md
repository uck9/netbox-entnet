# Netbox Enterprise Networks Plugin

NetBox Enterprise Networks Plugin


* Free software: Apache-2.0
* Documentation: https://uck9.github.io/netbox-entnet/


## Features

A simple plugin to add some logic and functionality to the NetBox code without having to touch any of the core files.

Currently features:
    - Add a network mangement tag to ip addresses when:
        - The IP Address is set as the primary IP address
        - It's in a list of specific manufacturers.
    - Add a network discovery tag when
        - The discovery exempt tag isn't already there.
        - The tenant exists in the configured list with a specific discovery tag.
    - Set a default VRF in the event the user creates an IP in the Global space.

## Compatibility

| NetBox Version | Plugin Version |
|----------------|----------------|
|     4.0+       |      0.1.0     |

## Installing

For adding to a NetBox Docker setup see
[the general instructions for using netbox-docker with plugins](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins).

While this is still in development and not yet on pypi you can install with pip:

```bash
pip install git+https://github.com/uck9/netbox-entnet
```

or by adding to your `local_requirements.txt` or `plugin_requirements.txt` (netbox-docker):

```bash
git+https://github.com/uck9/netbox-entnet
```

Enable the plugin in `/opt/netbox/netbox/netbox/configuration.py`,
 or if you use netbox-docker, your `/configuration/plugins.py` file :

```python
PLUGINS = [
    'netbox-entnet'
]

PLUGINS_CONFIG = {
    'netbox_entnet': {
        'TENANT_TAG_TO_IP_TAG': {
            'tenant-a': 'tenant-a-discovery',
            'tenant-b': 'tenant-b-discovery',
            # Add more as needed
            },
        'MANUFACTURER_NAME_SLUGS': ['cisco', 'palo-alto'],
        'SKIP_DISCOVERY_TAG_SLUG': 'discovery-exempt',  # Tag on IP to skip automation
        'NETWORK_MGMT_TAG_SLUG': 'ipam-network-device-mgmt',
        'DEFAULT_VRF_NAME': 'VRF-DEFAULT',  # Default VRF name
    },
}
```

## Credits

Based on the NetBox plugin tutorial:

- [demo repository](https://github.com/netbox-community/netbox-plugin-demo)
- [tutorial](https://github.com/netbox-community/netbox-plugin-tutorial)

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [`netbox-community/cookiecutter-netbox-plugin`](https://github.com/netbox-community/cookiecutter-netbox-plugin) project template.
