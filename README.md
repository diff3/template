# Project Template

Minimal workspace for running proxy + server + DSL together.

## Structure

    .
    ├── .env
    ├── authserver.py
    ├── proxyserver.py
    ├── worldserver.py
    ├── DSL/
    ├── proxy/
    ├── server/
    └── common/

---

## Setup

Clone required repositories:

    git clone https://github.com/diff3/BinaryPacketsDSL.git DSL
    git clone https://github.com/diff3/SwitchboardProxy.git proxy
    git clone https://github.com/diff3/PyPandaria.git server
    git clone https://github.com/diff3/shared.git common

Place them in this directory so the structure matches above.

---

## Build DSL output

Generate protocol code from DSL:

    cd DSL
    python build.py
    cd ..

---

## Environment

Load environment variables:

    source .env

Example `.env`:

    PYTHONPATH=./DSL/output:./proxy:./server:./common

    SERVER_CONFIG=./server/config.yaml
    AUTH_CONFIG=./server/auth_config.yaml
    PROXY_CONFIG=./proxy/config.yaml

Verify imports:

    python -c "import server, proxy, common; print('OK')"

---

## Run

Start proxy:

    ./proxyserver.py

Start world server:

    ./worldserver.py

Start auth server (optional):

    ./authserver.py

---

## Notes

- BinaryPacketsDSL generates protocol code into `output/`
- Only `output/` is required at runtime
- Each component manages its own configuration
- `.env` wires everything together

---

## Philosophy

- DSL = protocol engine  
- proxy = network tool  
- server = game logic  
- common = shared infrastructure  
- template = launcher