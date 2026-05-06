"""Reference-inspired logging helpers for AgentZon modules.

@author: javier
"""

__author__ = "javier"

import logging


def config_logger(level=0, file=None):
    if file is not None:
        logging.basicConfig(filename=f"{file}.log", filemode="w")

    logger = logging.getLogger("log")
    logger.setLevel(logging.INFO if level else logging.ERROR)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO if level else logging.ERROR)
    formatter = logging.Formatter(
        "[%(asctime)-15s] - %(filename)s - %(levelname)s - %(message)s"
    )
    console.setFormatter(formatter)
    logging.getLogger("log").handlers.clear()
    logging.getLogger("log").addHandler(console)
    return logger
