FROM ghcr.io/astral-sh/uv:debian

# Make Python more friendly to running in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Make uv install content in well-known locations
ENV UV_PROJECT_ENVIRONMENT=/var/lib/venv \
  UV_CACHE_DIR=/var/cache/uv/cache \
  UV_PYTHON_INSTALL_DIR=/var/cache/uv/bin \
  # The uv cache and environment are expected to be mounted on different volumes,
  # so hardlinks won't work
  UV_LINK_MODE=symlink

RUN \
  rm -f /etc/apt/apt.conf.d/docker-clean; \
  echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt update && \
  apt-get --no-install-recommends install --yes \
    git-lfs
