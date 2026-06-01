"""Shared configuration and bootstrap helpers for AgentZon agents."""

import multiprocessing
import os
import queue as queue_lib
from pathlib import Path

from AgentUtil.ACLMessages import send_message
from AgentUtil.Agent import Agent
from AgentUtil.Logging import config_logger
from AgentUtil.Util import gethostname
from AgentUtil.OntoNamespaces import AGN
from protocols.directory import build_register_message


_logger = config_logger(level=1)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_DIR = BASE_DIR / "web" / "templates"
ONTOLOGY_PATH = BASE_DIR / "ontologia" / "AgentZonOntology.rdf"
DEFAULT_BIND_HOST = "0.0.0.0"
DEFAULT_LOCAL_HOST = "127.0.0.1"
MAX_LOT_WEIGHT_KG = 5.0
READY_DELIVERY_WINDOW_DAYS = 1


DEFAULT_PORTS = {
    "directory": 9000,
    "cercador": 9001,
    "compra": 9002,
    "centre_logistic": 9003,
    "opinador": 9004,
    "cobrador": 9005,
    "proveidor_pagament": 9006,
    "transport_fast": 9010,
    "transport_economy": 9011,
}


def build_agent(name, uri_name, port, host="127.0.0.1", endpoint="/comm"):
    return Agent(
        name=name,
        uri=AGN[uri_name],
        address=f"http://{host}:{port}{endpoint}",
        stop=f"http://{host}:{port}/Stop",
    )


def build_directory_agent(host=DEFAULT_LOCAL_HOST, port=DEFAULT_PORTS["directory"]):
    return build_agent("DirectoryAgent", "Directory", port, host=host, endpoint="/Register")


def resolve_runtime_hostname(args):
    configured_host = getattr(args, "host", None)
    if configured_host:
        return configured_host
    if getattr(args, "open", None) is None:
        return DEFAULT_BIND_HOST
    return gethostname()


def add_runtime_arguments(parser, default_port):
    parser.add_argument("--host", default=None)
    parser.add_argument(
        "--open",
        action="store_true",
        default=None,
        help="Publish the agent using the machine hostname instead of the default bind address.",
    )
    parser.add_argument("--port", type=int, default=default_port)


def add_directory_arguments(parser):
    parser.add_argument("--directory-host", default=DEFAULT_LOCAL_HOST)
    parser.add_argument("--directory-port", type=int, default=DEFAULT_PORTS["directory"])


def add_data_dir_argument(parser):
    parser.add_argument("--data-dir", default=str(DATA_DIR))


def register_with_directory(agent, directory_agent, agent_type, msgcnt=0, metadata=None):
    try:
        message = build_register_message(
            agent,
            agent_type,
            directory_agent,
            msgcnt=msgcnt,
            metadata=metadata,
        )
        send_message(message, directory_agent.address)
    except Exception:
        return False
    return True


# Concurrent behaviour + Flask server (patró dels agents d'exemple del professor) -----
def _agent_behaviour(queue, register_fn):
    """Comportament concurrent de l'agent.

    Replica `agentbehavior1` dels exemples (SimpleInfoAgent/SimpleDirectoryService):
    fa el registre al directori (si escau) i després queda a l'espera fins que el
    procés principal hi diposita un 0 a la cua per aturar-lo netament.
    """
    if register_fn is not None:
        register_fn()
    while True:
        try:
            if queue.get(timeout=1.0) == 0:
                return
        except queue_lib.Empty:
            # Si el procés principal (el servidor Flask) ha mort, ens aturem
            # per no quedar com a procés orfe.
            if os.getppid() == 1:
                return


def serve_agent(app, hostname, port, register_fn=None):
    """Arrenca el comportament concurrent en un Process + el servidor Flask.

    Segueix el patró dels exemples del professor:
    `Process(target=agentbehavior1, args=(cola,))` + `app.run(...)` + `join()`.
    El registre al directori passa dins del comportament concurrent.
    """
    try:
        context = multiprocessing.get_context("fork")
    except ValueError:  # plataformes sense fork (p.ex. Windows): context per defecte
        context = multiprocessing.get_context()
    queue = context.Queue()
    behaviour = context.Process(target=_agent_behaviour, args=(queue, register_fn))
    behaviour.daemon = True
    behaviour.start()
    try:
        app.run(host=hostname, port=port, debug=False, use_reloader=False)
    finally:
        queue.put(0)
        behaviour.join(timeout=5)
        if behaviour.is_alive():
            behaviour.terminate()
