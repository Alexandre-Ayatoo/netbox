"""Run with the OLD instance's manage.py shell; stdout contains private settings."""

import json
import os
from importlib import import_module

from django.conf import settings

expected_plugins = {
    'netbox_inventory', 'ipfabric_netbox', 'netbox_bgp',
    'netbox_interface_synchronization', 'netbox_branching',
}
if settings.VERSION != '4.6.10' or set(settings.PLUGINS) != expected_plugins:
    raise RuntimeError('This migration preparation expects NetBox 4.6.10 and the five inventoried plugins.')

configuration = import_module(os.environ.get('NETBOX_CONFIGURATION', 'netbox.configuration'))
payload = {
    'SECRET_KEY': settings.SECRET_KEY,
    'API_TOKEN_PEPPERS': settings.API_TOKEN_PEPPERS,
    'PLUGINS': settings.PLUGINS,
    'PLUGINS_CONFIG': settings.PLUGINS_CONFIG,
    'AUTHENTICATION_SETTINGS': {
        name: getattr(configuration, name)
        for name in dir(configuration)
        if name.isupper() and name.startswith(('REMOTE_AUTH_', 'SOCIAL_AUTH_'))
    },
}
# Serialize before writing, so unsupported custom values fail without a partial export.
serialized = json.dumps(payload, indent=2)
print(serialized)
