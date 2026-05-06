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
    logger.propagate = False

    # Silence Flask/Werkzeug per-request access logs such as:
    # 127.0.0.1 - - [..] "GET /comm?content=... HTTP/1.1" 200 -
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.disabled = True
    flask_app_logger = logging.getLogger("flask.app")
    flask_app_logger.handlers.clear()
    flask_app_logger.disabled = True
    return logger
