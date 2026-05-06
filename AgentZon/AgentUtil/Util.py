"""Network utility helpers used during AgentZon agent bootstrap.

@author: javier
"""

__author__ = "javier"

import socket


def gethostname():
    return socket.gethostname()
