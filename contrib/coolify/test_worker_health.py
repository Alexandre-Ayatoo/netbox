"""Verify worker health follows RQ's heartbeat expiry, including idle workers."""

import importlib.util
import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


class WorkerHealthTest(unittest.TestCase):
    def check_health(self, workers):
        django = ModuleType('django')
        django.setup = Mock()
        django_rq = ModuleType('django_rq')
        django_rq.get_connection = Mock(return_value=object())
        rq = ModuleType('rq')
        rq.Worker = SimpleNamespace(all=Mock(return_value=workers))
        with (
            patch.dict(sys.modules, {'django': django, 'django_rq': django_rq, 'rq': rq}),
            patch.dict(os.environ),
            patch.object(sys, 'path', sys.path.copy()),
            patch('socket.gethostname', return_value='this-container'),
        ):
            spec = importlib.util.spec_from_file_location('worker_health_test_module',
                                                       Path(__file__).with_name('worker_health.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with self.assertRaises(SystemExit) as result:
                module.main()
        return result.exception.code

    @staticmethod
    def worker(ttl, hostname='this-container', heartbeat=True):
        return SimpleNamespace(
            hostname=hostname,
            last_heartbeat=datetime.now(UTC) - timedelta(seconds=400) if heartbeat else None,
            connection=SimpleNamespace(ttl=Mock(return_value=ttl)),
            key='rq:worker:test',
        )

    def test_idle_worker_with_unexpired_heartbeat_is_healthy(self):
        worker = self.worker(ttl=80)
        self.assertEqual(self.check_health([worker]), 0)
        worker.connection.ttl.assert_called_once_with(worker.key)

    def test_expired_or_missing_heartbeat_is_unhealthy(self):
        for ttl in (0, -2):
            with self.subTest(ttl=ttl):
                self.assertEqual(self.check_health([self.worker(ttl)]), 1)

    def test_key_without_expiry_is_unhealthy(self):
        self.assertEqual(self.check_health([self.worker(ttl=-1)]), 1)

    def test_another_containers_worker_is_not_enough(self):
        self.assertEqual(self.check_health([self.worker(ttl=80, hostname='another-container')]), 1)

    def test_worker_without_heartbeat_is_unhealthy(self):
        self.assertEqual(self.check_health([self.worker(ttl=80, heartbeat=False)]), 1)

    def test_no_workers_is_unhealthy(self):
        self.assertEqual(self.check_health([]), 1)


if __name__ == '__main__':
    unittest.main()
