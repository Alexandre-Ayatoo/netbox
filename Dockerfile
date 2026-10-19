FROM python:3.13-slim-bookworm AS application

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NETBOX_CONFIGURATION=netbox.configuration_coolify

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/netbox
COPY requirements.txt ./
RUN pip install -r requirements.txt \
    && apt-get purge -y --auto-remove gcc libc6-dev libpq-dev \
    && apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY . .
COPY contrib/coolify/configuration.py netbox/netbox/configuration_coolify.py
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
