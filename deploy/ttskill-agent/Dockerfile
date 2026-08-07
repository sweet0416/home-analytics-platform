FROM debian:bookworm-slim

ARG TTSKILL_PACKAGE=ttskill-base-linux-x64-0.1.2.zip

ENV DEBIAN_FRONTEND=noninteractive \
    TTSKILL_HOME=/var/lib/ttskill \
    TTSKILL_BIN=/opt/ttskill/bin/ttskill

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        dbus \
        dbus-x11 \
        gnome-keyring \
        libsecret-tools \
        unzip \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --home-dir /home/ttskill --shell /bin/sh ttskill \
    && mkdir -p /var/lib/ttskill /opt/ttskill \
    && chown -R ttskill:ttskill /var/lib/ttskill /home/ttskill

COPY ${TTSKILL_PACKAGE} /tmp/ttskill-base.zip
RUN unzip -q /tmp/ttskill-base.zip -d /tmp/ttskill-base \
    && package_dir="$(find /tmp/ttskill-base -mindepth 1 -maxdepth 1 -type d -print -quit)" \
    && cp -a "$package_dir"/. /opt/ttskill/ \
    && chmod +x /opt/ttskill/bin/ttskill \
    && rm -rf /tmp/ttskill-base /tmp/ttskill-base.zip \
    && chown -R root:root /opt/ttskill

COPY entrypoint.sh /usr/local/bin/ttskill-entrypoint
RUN chmod 0755 /usr/local/bin/ttskill-entrypoint

USER ttskill
WORKDIR /home/ttskill
ENTRYPOINT ["/usr/local/bin/ttskill-entrypoint"]
CMD ["status", "--json"]
