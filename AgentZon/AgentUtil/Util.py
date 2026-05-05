import socket


def gethostname():
    try:
        return socket.getfqdn()
    except OSError:
        return socket.gethostname()
