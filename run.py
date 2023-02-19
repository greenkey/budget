#!/usr/bin/env python3
import logging
import os

import fire

from src import commands

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)

if __name__ == "__main__":
    fire.Fire(commands.Commands)
