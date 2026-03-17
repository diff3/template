#!/usr/bin/env python3

import os
from server.auth import run_auth

if __name__ == "__main__":
    run_auth(config_path=os.environ["AUTH_CONFIG"])