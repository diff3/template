ARG PYTHON_IMAGE=python:3.14-slim-trixie
FROM ${PYTHON_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-mysql-client \
        netcat-openbsd \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY DSL/requirements.txt /tmp/dsl-requirements.txt
RUN pip install --no-cache-dir -r /tmp/dsl-requirements.txt

COPY . /app
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
