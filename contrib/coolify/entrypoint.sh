#!/bin/sh
set -eu

case "${1:-web}" in
    web)
        python manage.py upgrade --no-input
        python /opt/netbox/contrib/coolify/bootstrap_admin.py
        exec gunicorn netbox.wsgi:application \
            --bind 0.0.0.0:8001 \
            --workers "${GUNICORN_WORKERS:-3}" \
            --threads 2 \
            --timeout 120 \
            --access-logfile - \
            --error-logfile -
        ;;
    worker)
        exec python manage.py rqworker
        ;;
    *)
        exec "$@"
        ;;
esac
