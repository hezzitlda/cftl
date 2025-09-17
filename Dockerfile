FROM alpine:3.22

ARG TARGETPLATFORM

RUN apk add --no-cache \
    nginx \
    python3 \
    py3-pip \
    gettext \
    curl \
    ca-certificates \
    wget

RUN case "$TARGETPLATFORM" in \
        "linux/amd64") CLOUDFLARED_ARCH="amd64" ;; \
        "linux/arm64") CLOUDFLARED_ARCH="arm64" ;; \
        "linux/arm/v7") CLOUDFLARED_ARCH="arm" ;; \
        *) echo "Unsupported platform: $TARGETPLATFORM" && exit 1 ;; \
    esac && \
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CLOUDFLARED_ARCH} -O /usr/local/bin/cloudflared && \
    chmod +x /usr/local/bin/cloudflared

RUN pip3 install --break-system-packages pyjwt aiohttp

RUN mkdir -p /var/log/nginx \
    /var/cache/nginx \
    /run/nginx \
    /etc/nginx/sites-enabled \
    /var/lib/nginx \
    /var/lib/nginx/tmp

COPY offline_fallback.conf /etc/nginx/sites-enabled/offline_fallback.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY service-template.conf /app/service-template.conf
COPY service-noauth-template.conf /app/service-noauth-template.conf
COPY auth.py /app/auth.py
COPY config.py /app/config.py
COPY start.py /app/start.py
COPY offline_fallback.py /app/offline_fallback.py

RUN chmod +x /app/*.py

RUN adduser -D -H -s /sbin/nologin nginx || true

RUN chown -R nginx:nginx /var/log/nginx \
    /var/cache/nginx \
    /run/nginx \
    /var/lib/nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -s -o /dev/null -w "%{http_code}" http://localhost:${PORT:-8080}/ | grep -q "^[1-4]" || exit 1

CMD ["python3", "/app/start.py"]
