#!/usr/bin/env python3

import os
from server.world import run_world

if __name__ == "__main__":
    run_world(config_path=os.environ["SERVER_CONFIG"])
