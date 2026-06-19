ARG ADMIN_PANEL_PYTHON_IMAGE=python:3.12-slim-bookworm
FROM ${ADMIN_PANEL_PYTHON_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-mysql-client \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY DSL/requirements.txt /tmp/dsl-requirements.txt
COPY admin_panel/requirements.txt /tmp/admin-requirements.txt
RUN pip install --no-cache-dir -r /tmp/dsl-requirements.txt -r /tmp/admin-requirements.txt

COPY . /app
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
