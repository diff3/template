#!/usr/bin/env python3

import os
from proxy.main import run_proxy

if __name__ == "__main__":
    run_proxy(config_path=os.environ["PROXY_CONFIG"])