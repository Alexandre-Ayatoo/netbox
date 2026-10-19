"""Check the heartbeat of the RQ worker running in this container."""

import os
import socket
import sys
from datetime import timedelta

import django


def main():
    sys.path.insert(0, '/opt/netbox/netbox')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
    django.setup()

    from django.utils import timezone
    from django_rq import get_connection
    from rq import Worker

    healthy = any(
        worker.hostname == socket.gethostname()
        and worker.last_heartbeat is not None
        and timezone.now() - worker.last_heartbeat < timedelta(seconds=120)
        for worker in Worker.all(connection=get_connection('default'))
    )
    sys.exit(0 if healthy else 1)


if __name__ == '__main__':
    main()
