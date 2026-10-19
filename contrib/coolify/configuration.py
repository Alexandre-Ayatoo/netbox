"""Environment-based configuration for the bundled Coolify deployment."""

import os
from urllib.parse import urlsplit

_url = urlsplit(os.environ['NETBOX_URL'])
if _url.scheme not in ('http', 'https') or not _url.hostname or _url.path not in ('', '/'):
    raise ValueError('NETBOX_URL must be an http(s) URL without a subpath.')

ALLOWED_HOSTS = [_url.hostname, 'localhost', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = [f'{_url.scheme}://{_url.netloc}']
CSRF_COOKIE_SECURE = _url.scheme == 'https'
SESSION_COOKIE_SECURE = _url.scheme == 'https'
SECRET_KEY = os.environ['SECRET_KEY']
API_TOKEN_PEPPERS = {1: os.environ['API_TOKEN_PEPPER']}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'netbox',
        'USER': 'netbox',
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': 'postgres',
        'PORT': 5432,
        'CONN_MAX_AGE': 300,
    },
}

REDIS = {
    name: {
        'HOST': 'redis',
        'PORT': 6379,
        'PASSWORD': os.environ['REDIS_PASSWORD'],
        'DATABASE': database,
        'SSL': False,
    }
    for name, database in (('tasks', 0), ('caching', 1))
}
