# PyPandariaEmu Docker

This directory contains the Docker setup for the runtime services:

- `authserver`
- `worldserver`
- `proxyserver`
- `admin_panel`

MySQL/MariaDB is expected to run on an external server. Configure it in the
shared project config under `../config/`.

## Quick start

```bash
cd docker
make help
make config-env
make build
make start
make logs
```

## Config

Runtime configuration is shared from the project config directory:

- `../config/default.yaml`
- `../config/authserver.yaml`
- `../config/worldserver.yaml`
- `../config/proxy.json`
- `../config/proxy.state.json`

If the proxy should forward to the Docker services, set its shared proxy config
to forward to `authserver:3720` and `worldserver:8086`.

The Makefile generates `docker/.generated.env` from that shared config before
running compose. Docker publishes the ports read from config:

- `config/authserver.yaml` for `authserver`
- `config/worldserver.yaml` for `worldserver`
- `config/proxy.state.json` or `config/proxy.json` for proxy route listeners
- `config/proxy.json` for the proxy telnet console

The admin panel is published on `ADMIN_PANEL_PORT` from `.env`, default `5001`.
It uses `ADMIN_PANEL_PYTHON_IMAGE` from `.env` separately from the server
containers so the servers can stay on Python 3.14.

## Client data

If the worldserver needs external client data, set these in `.env` as needed:

- `DBC_HOST_PATH`
- `DB2_HOST_PATH`
- `MAPS_HOST_PATH`

They are mounted to the current `dbc_path`, `db2_path`, and `maps_path` read
from `../config/worldserver.yaml`.
