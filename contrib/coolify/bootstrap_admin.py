"""Create the initial administrator, preserving existing accounts on redeploy."""

import os
import sys

import django


def main():
    # These helper scripts are outside the Django project directory.
    sys.path.insert(0, '/opt/netbox/netbox')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
    django.setup()

    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    username = os.environ['DJANGO_SUPERUSER_USERNAME']
    if not user_model.objects.filter(username=username).exists():
        user_model.objects.create_superuser(
            username=username,
            email=os.environ['DJANGO_SUPERUSER_EMAIL'],
            password=os.environ['DJANGO_SUPERUSER_PASSWORD'],
        )
        print('Initial NetBox administrator created.')
    else:
        print('NetBox administrator already exists; credentials left unchanged.')


if __name__ == '__main__':
    main()
