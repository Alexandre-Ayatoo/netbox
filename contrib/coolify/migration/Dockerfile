FROM python:3.13-slim-bookworm AS application

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NETBOX_CONFIGURATION=netbox.configuration_migration

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/netbox
RUN curl --fail --location --silent --show-error \
        https://codeload.github.com/netbox-community/netbox/tar.gz/refs/tags/v4.6.10 \
        --output /tmp/netbox.tar.gz \
    && echo 'b619f7eca409dc94707faf7b9c38e1dc9c476b7c88c312f91b66182124d997e4  /tmp/netbox.tar.gz' \
        | sha256sum --check - \
    && tar -xzf /tmp/netbox.tar.gz --strip-components=1 -C /opt/netbox \
    && rm /tmp/netbox.tar.gz

COPY contrib/coolify/migration/requirements.txt /tmp/plugin-requirements.txt
RUN pip install -r requirements.txt -r /tmp/plugin-requirements.txt \
    && pip check \
    && apt-get purge -y --auto-remove gcc libc6-dev libpq-dev \
    && apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY contrib/coolify/entrypoint.sh contrib/coolify/bootstrap_admin.py contrib/coolify/worker_health.py contrib/coolify/
COPY contrib/coolify/configuration.py netbox/netbox/configuration_coolify.py
COPY contrib/coolify/migration/configuration.py netbox/netbox/configuration_migration.py
RUN zensical build --clean \
    && groupadd --gid 1000 netbox \
    && useradd --uid 1000 --gid netbox --create-home netbox \
    && mkdir -p netbox/static netbox/media netbox/scripts netbox/reports \
    && chown -R netbox:netbox netbox/static netbox/media netbox/scripts netbox/reports \
    && chmod +x contrib/coolify/entrypoint.sh

USER netbox
WORKDIR /opt/netbox/netbox
EXPOSE 8001
ENTRYPOINT ["/opt/netbox/contrib/coolify/entrypoint.sh"]
CMD ["web"]

FROM nginx:1.28-alpine AS proxy
COPY contrib/coolify/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
