ARG GIT_SHA=unknown
ARG BUILD_TIME=unknown
ARG IMAGE_REFERENCE=hap-ttskill-agent:local

FROM debian:bookworm-slim

ARG GIT_SHA
ARG BUILD_TIME
ARG IMAGE_REFERENCE

LABEL org.opencontainers.image.source="https://github.com/sweet0416/home-analytics-platform" \
      org.opencontainers.image.revision="$GIT_SHA" \
      org.opencontainers.image.created="$BUILD_TIME" \
      org.opencontainers.image.ref.name="$IMAGE_REFERENCE"

ARG TTSKILL_PACKAGE_URL=https://skills.tiantianfunds.com/ttskill/packages/base/0.1.2/linux/x64/ttskill-base-linux-x64-0.1.2.zip
ARG TTSKILL_PACKAGE_SHA256=a2a1203ea6e84c7d8af42bd943c2e8b5f8144aa72a75f64e04c44c4e5b44eb12

ENV DEBIAN_FRONTEND=noninteractive \
    TTSKILL_HOME=/var/lib/ttskill \
    TTSKILL_BIN=/opt/ttskill/bin/ttskill

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        dbus \
        dbus-x11 \
        gnome-keyring \
        libsecret-tools \
        unzip \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --home-dir /home/ttskill --shell /bin/sh ttskill \
    && mkdir -p /var/lib/ttskill /opt/ttskill \
    && chown -R ttskill:ttskill /var/lib/ttskill /home/ttskill

RUN curl --fail --location --retry 5 --retry-all-errors \
        --connect-timeout 20 --max-time 300 \
        --output /tmp/ttskill-base.zip "$TTSKILL_PACKAGE_URL" \
    && echo "$TTSKILL_PACKAGE_SHA256  /tmp/ttskill-base.zip" | sha256sum -c - \
    && unzip -q /tmp/ttskill-base.zip -d /tmp/ttskill-base \
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
