from flask import request


def shutdown_server():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        return False
    func()
    return True
