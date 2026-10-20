"""Check the heartbeat of the RQ worker running in this container."""

import os
import socket
import sys

import django


def main():
    sys.path.insert(0, '/opt/netbox/netbox')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
    django.setup()

    from django_rq import get_connection
    from rq import Worker

    healthy = any(
        worker.hostname == socket.gethostname()
        and worker.last_heartbeat is not None
        # RQ can block for 405 seconds waiting for a job with its default TTL.
        # Use the heartbeat's Redis expiry instead of a shorter independent age limit.
        and worker.connection.ttl(worker.key) > 0
        for worker in Worker.all(connection=get_connection('default'))
    )
    sys.exit(0 if healthy else 1)


if __name__ == '__main__':
    main()
