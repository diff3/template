# PyPandariaEmu

Workspace containing the DSL runtime, proxy, authserver and worldserver.

## Layout

```text
.
├── authserver.py
├── worldserver.py
├── proxyserver.py
├── DSL/
├── proxy/
├── server/
├── shared/
├── config/
├── data/
└── logs/
```

## Configuration

YAML config files live in `config/`:

- [/home/magnus/projects/PyPandariaEmu/config/default.yaml](/home/magnus/projects/PyPandariaEmu/config/default.yaml)
- [/home/magnus/projects/PyPandariaEmu/config/authserver.yaml](/home/magnus/projects/PyPandariaEmu/config/authserver.yaml)
- [/home/magnus/projects/PyPandariaEmu/config/worldserver.yaml](/home/magnus/projects/PyPandariaEmu/config/worldserver.yaml)
- [/home/magnus/projects/PyPandariaEmu/config/client.yaml](/home/magnus/projects/PyPandariaEmu/config/client.yaml)

The proxy keeps its own JSON config, but it is now also stored under `config/`:

- [/home/magnus/projects/PyPandariaEmu/config/proxy.json](/home/magnus/projects/PyPandariaEmu/config/proxy.json)

## Data

Runtime data is centralized under `data/`:

- `data/def` for packet definitions
- `data/json` for expected/promoted decoded payloads
- `data/debug` for promoted raw/debug packet dumps
- `data/captures` for live captures and focus captures

## Logs

Current log files live under `logs/`:

- `authserver.log`
- `worldserver.log`
- `proxy.log`
- `dsl.log`

Service logs are reset on startup so they reflect the current session.

## Run

From project root:

```bash
python authserver.py
python worldserver.py
python proxyserver.py
```

## Component Notes

- `authserver` and `worldserver` use the shared DSL runtime for decode/encode
- packet output for auth/world is controlled by their own YAML files
- the proxy is read-only and forwards original bytes unchanged
- the proxy can still parse opcodes, decode payloads, dump captures and provide telnet control

## See Also

- [/home/magnus/projects/PyPandariaEmu/server/README.md](/home/magnus/projects/PyPandariaEmu/server/README.md)
- [/home/magnus/projects/PyPandariaEmu/proxy/README.md](/home/magnus/projects/PyPandariaEmu/proxy/README.md)
