from dataclasses import dataclass


@dataclass(frozen=True)
class Agent:
    name: str
    uri: object
    address: str
    stop: str
