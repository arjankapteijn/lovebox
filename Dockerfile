# ── Build ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS build
WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
COPY pyproject.toml ./
COPY src ./src
# Bouw een wheel + installeer 'm met dependencies in een prefix die we
# straks naar de runtime kopiëren.
RUN pip install --prefix=/install .

# ── Runtime (hardened) ─────────────────────────────────────────────────────
# Slank image, niet-root, met DejaVu-fonts (nodig voor de tekstrendering) en
# tzdata (voor de Europe/Amsterdam scheduler).
FROM python:3.12-slim
RUN apt-get update \
  && apt-get install -y --no-install-recommends fonts-dejavu-core tzdata \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd -g 10001 app \
  && useradd -u 10001 -g app -M -s /usr/sbin/nologin app \
  && mkdir -p /data && chown app:app /data
COPY --from=build /install /usr/local

USER app
ENV PYTHONUNBUFFERED=1 \
    LOVEBOX_DATA_DIR=/data \
    LOVEBOX_TZ=Europe/Amsterdam
VOLUME /data

# De scheduler raakt elke tick /data/heartbeat aan; als dat bestand ouder dan
# ~2 minuten is, is er iets mis en faalt de healthcheck.
HEALTHCHECK --interval=60s --timeout=5s --start-period=20s \
  CMD test "$(( $(date +%s) - $(stat -c %Y /data/heartbeat 2>/dev/null || echo 0) ))" -lt 150 || exit 1

CMD ["python", "-m", "lovebox.main"]
