"""Build and exercise an isolated Compose deployment, then remove its resources."""

import http.cookiejar
import json
import os
import re
import secrets
import socket
import subprocess
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen


def main():
    repository = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='netbox-coolify-test-') as directory:
        temporary = Path(directory)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        url = f'http://localhost:{port}'
        values = {'SERVICE_URL_WEB': url}
        for key in ('SECRET', 'PEPPER', 'POSTGRES', 'REDIS', 'ADMIN'):
            values[f'SERVICE_PASSWORD_64_{key}'] = secrets.token_hex(32)
        env_file = temporary / 'stack.env'
        env_file.write_text('\n'.join(f'{key}={value}' for key, value in values.items()))
        os.chmod(env_file, 0o600)
        override = temporary / 'override.json'
        override.write_text(json.dumps({
            'services': {'web': {'ports': [f'127.0.0.1:{port}:8080']}},
        }))
        compose = [
            'docker', 'compose', '--project-name', f'netbox-test-{secrets.token_hex(4)}',
            '--env-file', str(env_file), '-f', str(repository / 'docker-compose.yml'),
            '-f', str(override),
        ]

        def run(*args, **kwargs):
            return subprocess.run([*compose, *args], cwd=repository, check=True, **kwargs)

        try:
            print('Building and starting the isolated stack (logs are captured)...', flush=True)
            log_file = temporary / 'deployment.log'
            with log_file.open('w') as log:
                try:
                    run('up', '--build', '-d', '--wait', '--wait-timeout', '600', stdout=log, stderr=log)
                except subprocess.CalledProcessError:
                    print('\n'.join(log_file.read_text().splitlines()[-60:]))
                    run('logs', '--tail', '60')
                    raise

            with urlopen(f'{url}/static/netbox.css', timeout=15) as response:
                assert response.status == 200
                assert 'text/css' in response.headers['Content-Type']

            # Repeating bootstrap with a new password must preserve the existing one.
            run('exec', '-T', '-e', f'DJANGO_SUPERUSER_PASSWORD={secrets.token_hex(32)}',
                'netbox', 'python', '/opt/netbox/contrib/coolify/bootstrap_admin.py')

            cookies = http.cookiejar.CookieJar()
            browser = build_opener(HTTPCookieProcessor(cookies))
            with browser.open(f'{url}/login/', timeout=15) as response:
                html = response.read().decode()
            token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
            form = urlencode({
                'username': 'admin',
                'password': values['SERVICE_PASSWORD_64_ADMIN'],
                'csrfmiddlewaretoken': token,
                'next': '/',
            }).encode()
            with browser.open(Request(f'{url}/login/', data=form, headers={'Origin': url}), timeout=30):
                assert any(cookie.name == 'sessionid' for cookie in cookies), 'Admin login failed'

            try:
                browser.open(Request(f'{url}/login/', data=form, headers={'Origin': 'https://invalid.example'}))
            except HTTPError as error:
                assert error.code == 403
            else:
                raise AssertionError('An untrusted CSRF origin was accepted')

            try:
                urlopen(Request(f'{url}/login/', headers={'Host': 'invalid.example'}), timeout=15)
            except HTTPError as error:
                assert error.code == 400
            else:
                raise AssertionError('An untrusted host was accepted')

            print('PASS: all services healthy, static CSS, admin login, bootstrap preservation, host and CSRF checks.')
        finally:
            run('down', '--volumes', '--remove-orphans')


if __name__ == '__main__':
    main()
