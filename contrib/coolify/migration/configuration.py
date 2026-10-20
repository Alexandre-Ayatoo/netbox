"""Settings for restoring the legacy instance into an isolated migration stack."""

import json
from pathlib import Path

from netbox_branching.utilities import DynamicSchemaDict

from .configuration_coolify import *

_legacy = json.loads(Path('/etc/netbox-migration/settings.json').read_text())
SECRET_KEY = _legacy['SECRET_KEY']
API_TOKEN_PEPPERS = {int(key): value for key, value in _legacy['API_TOKEN_PEPPERS'].items()}
PLUGINS = _legacy['PLUGINS']
PLUGINS_CONFIG = _legacy['PLUGINS_CONFIG']
DATABASES = DynamicSchemaDict(DATABASES)
DATABASE_ROUTERS = ['netbox_branching.database.BranchAwareRouter']
