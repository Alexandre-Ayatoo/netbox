"""Tests for private settings export and loading, without a database or real secrets."""

import contextlib
import io
import json
import os
import runpy
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
PLUGINS = [
    'netbox_inventory', 'ipfabric_netbox', 'netbox_bgp',
    'netbox_interface_synchronization', 'netbox_branching',
]


class PrivateSettingsTest(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            VERSION='4.6.10', SECRET_KEY='fake-django-secret', API_TOKEN_PEPPERS={1: 'fake-pepper'},
            PLUGINS=PLUGINS, PLUGINS_CONFIG={'ipfabric_netbox': {'webhook_secrets': ['fake-webhook-secret']}},
        )
        self.original = ModuleType('original_configuration')
        self.original.REMOTE_AUTH_ENABLED = True
        self.original.REMOTE_AUTH_BACKEND = ['social_core.backends.keycloak.KeycloakOAuth2']
        self.original.SOCIAL_AUTH_KEYCLOAK_SECRET = 'fake-keycloak-secret'
        self.original.SOCIAL_AUTH_KEYCLOAK_SCOPE = ['openid', 'profile', 'email']
        self.original.DATABASES = {'default': {'HOST': 'old-database'}}

    def export(self, output):
        conf = ModuleType('django.conf')
        conf.settings = self.settings
        with (
            patch.dict(sys.modules, {
                'django': ModuleType('django'), 'django.conf': conf,
                'original_configuration': self.original,
            }),
            patch.dict(os.environ, {'NETBOX_CONFIGURATION': 'original_configuration'}),
            contextlib.redirect_stdout(output),
        ):
            runpy.run_path(str(ROOT / 'export_settings.py'))

    @staticmethod
    def load(payload):
        base = ModuleType('_migration_test.configuration_coolify')
        base.DATABASES = {'default': {'HOST': 'postgres', 'PASSWORD': 'fake-container-password'}}
        base.REMOTE_AUTH_ENABLED = False
        utilities = ModuleType('netbox_branching.utilities')
        utilities.DynamicSchemaDict = type('DynamicSchemaDict', (dict,), {})
        with (
            patch.dict(sys.modules, {
                '_migration_test': ModuleType('_migration_test'),
                '_migration_test.configuration_coolify': base,
                'netbox_branching': ModuleType('netbox_branching'),
                'netbox_branching.utilities': utilities,
            }),
            patch.object(Path, 'read_text', return_value=json.dumps(payload)),
        ):
            return runpy.run_path(str(ROOT / 'configuration.py'), run_name='_migration_test.configuration')

    def test_authentication_round_trip_keeps_container_database(self):
        output = io.StringIO()
        self.export(output)
        payload = json.loads(output.getvalue())
        self.assertNotIn('DATABASES', payload['AUTHENTICATION_SETTINGS'])
        loaded = self.load(payload)
        self.assertTrue(loaded['REMOTE_AUTH_ENABLED'])
        self.assertEqual(loaded['REMOTE_AUTH_BACKEND'], self.original.REMOTE_AUTH_BACKEND)
        self.assertEqual(loaded['SOCIAL_AUTH_KEYCLOAK_SECRET'], self.original.SOCIAL_AUTH_KEYCLOAK_SECRET)
        self.assertEqual(loaded['SOCIAL_AUTH_KEYCLOAK_SCOPE'], self.original.SOCIAL_AUTH_KEYCLOAK_SCOPE)
        self.assertEqual(loaded['DATABASES']['default']['HOST'], 'postgres')
        self.assertEqual(loaded['API_TOKEN_PEPPERS'], self.settings.API_TOKEN_PEPPERS)
        self.assertEqual(loaded['PLUGINS_CONFIG'], self.settings.PLUGINS_CONFIG)

    def test_original_export_without_authentication_still_loads(self):
        loaded = self.load(vars(self.settings))
        self.assertFalse(loaded['REMOTE_AUTH_ENABLED'])

    def test_authentication_section_cannot_replace_database_settings(self):
        payload = {**vars(self.settings), 'AUTHENTICATION_SETTINGS': {'DATABASES': {}}}
        with self.assertRaises(ValueError):
            self.load(payload)

    def test_unserializable_setting_writes_no_partial_export(self):
        self.original.SOCIAL_AUTH_CUSTOM_VALUE = object()
        output = io.StringIO()
        with self.assertRaises(TypeError):
            self.export(output)
        self.assertEqual(output.getvalue(), '')

    def test_wrong_source_version_writes_no_export(self):
        self.settings.VERSION = '4.7.3'
        output = io.StringIO()
        with self.assertRaises(RuntimeError):
            self.export(output)
        self.assertEqual(output.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
