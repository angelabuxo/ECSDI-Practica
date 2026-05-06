"""Minimal Agent record shared by the AgentZon runtime.

@author: javier
"""

__author__ = "javier"


class Agent:
    def __init__(self, name, uri, address, stop):
        self.name = name
        self.uri = uri
        self.address = address
        self.stop = stop
