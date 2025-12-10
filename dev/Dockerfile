FROM python:3.11-slim
# Install system libraries for Python packages:
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
    libpq-dev libvips-dev gcc g++ libc6-dev gdal-bin libgdal-dev git libgl1 libglx-mesa0 && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Use system gdal-config instead of Python GDAL's version (which requires osgeo module)
ENV GDAL_CONFIG=/usr/bin/gdal-config

ARG TASKS

COPY ./setup.py /opt/geoinsight-server/setup.py
COPY ./manage.py /opt/geoinsight-server/manage.py
COPY ./geoinsight /opt/geoinsight-server/geoinsight

RUN pip install --find-links https://girder.github.io/large_image_wheels --editable /opt/geoinsight-server[dev]

RUN if [ "$TASKS" = "1" ]; \
    then pip install --editable /opt/geoinsight-server[tasks]; \
    fi

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/geoinsight-server
