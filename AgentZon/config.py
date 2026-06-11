# -*- coding: utf-8 -*-
"""
filename: config

Configuracio compartida i arrencada concurrent dels agents AgentZon
(patrons SimpleInfoAgent / SimpleDirectoryService del laboratori)
"""

import multiprocessing
import os
import queue as queue_lib
import socket
import time
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
OPINADOR_FEEDBACK_POLICY_DAYS = 14
OPINADOR_FEEDBACK_MIN_SECONDS = 60
OPINADOR_RECOMMENDATION_INTERVAL_SEC = 60
OPINADOR_FEEDBACK_INTERVAL_SEC = 120
DIRECTORY_REGISTER_RETRIES = 20
DIRECTORY_REGISTER_RETRY_DELAY_SEC = 0.5
SERVER_READY_TIMEOUT_SEC = 10.0
SERVER_READY_POLL_INTERVAL_SEC = 0.1


DEFAULT_PORTS = {
    "directory": 9000,
    "cercador": 9001,
    "compra": 9002,
    "centre_logistic": 9003,
    "opinador": 9004,
    "cobrador": 9005,
    "retornador": 9009,
    "transport_fast": 9010,
    "transport_economy": 9011,
    "venedor_extern": 9012,
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


def resolve_bind_hostname(args):
    configured_host = getattr(args, "host", None)
    if configured_host:
        return configured_host
    if getattr(args, "open", None) is None:
        return DEFAULT_BIND_HOST
    return gethostname()


def resolve_publish_hostname(args):
    publish_host = getattr(args, "publish_host", None)
    if publish_host:
        return publish_host
    return resolve_bind_hostname(args)


def resolve_agent_hosts(args):
    return resolve_bind_hostname(args), resolve_publish_hostname(args)


def resolve_runtime_hostname(args):
    return resolve_bind_hostname(args)


def add_runtime_arguments(parser, default_port):
    parser.add_argument("--host", default=None)
    parser.add_argument(
        "--publish-host",
        default=None,
        help="IP or hostname published to the Directory (defaults to --host).",
    )
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


def register_with_directory(
    agent,
    directory_agent,
    agent_type,
    msgcnt=0,
    metadata=None,
    retries=DIRECTORY_REGISTER_RETRIES,
    retry_delay=DIRECTORY_REGISTER_RETRY_DELAY_SEC,
):
    if directory_agent is None:
        _logger.warning("No es pot registrar %s: no hi ha agent de directori configurat", agent.name)
        return False

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            message = build_register_message(
                agent,
                agent_type,
                directory_agent,
                msgcnt=msgcnt,
                metadata=metadata,
            )
            send_message(message, directory_agent.address)
            _logger.info(
                "Agent %s registrat al directori com a %s (intent %d)",
                agent.name,
                agent_type,
                attempt,
            )
            return True
        except Exception as exc:
            last_error = exc
            _logger.warning(
                "Registre de %s al directori fallit (intent %d/%d): %s",
                agent.name,
                attempt,
                retries,
                exc,
            )
            if attempt < retries:
                time.sleep(retry_delay)

    _logger.error(
        "No s'ha pogut registrar %s al directori després de %d intents: %s",
        agent.name,
        retries,
        last_error,
    )
    return False


# Concurrent behaviour + Flask server (patró dels agents d'exemple del professor) -----
def _probe_server_host(hostname):
    if hostname in (None, "", DEFAULT_BIND_HOST):
        return DEFAULT_LOCAL_HOST
    return hostname


def _socket_family_for_host(hostname):
    return socket.AF_INET6 if hostname and ":" in hostname and hostname != DEFAULT_BIND_HOST else socket.AF_INET


def _ensure_port_available(hostname, port):
    with socket.socket(_socket_family_for_host(hostname), socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((hostname, port))


def _wait_until_server_ready_for_registration(
    queue,
    hostname,
    port,
    timeout=SERVER_READY_TIMEOUT_SEC,
    poll_interval=SERVER_READY_POLL_INTERVAL_SEC,
):
    probe_host = _probe_server_host(hostname)
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            if queue.get(timeout=poll_interval) == 0:
                return False
        except queue_lib.Empty:
            pass

        if os.getppid() == 1:
            return False

        try:
            with socket.create_connection((probe_host, port), timeout=poll_interval):
                return True
        except OSError:
            continue

    _logger.error(
        "El servidor %s:%s no ha quedat en escolta dins del temps previst; s'omet el registre al directori",
        probe_host,
        port,
    )
    return False


def _agent_behaviour(queue, register_fn, ready_host=None, ready_port=None):
    """Comportament concurrent de l'agent.

    Replica `agentbehavior1` dels exemples (SimpleInfoAgent/SimpleDirectoryService):
    fa el registre al directori (si escau) i després queda a l'espera fins que el
    procés principal hi diposita un 0 a la cua per aturar-lo netament.
    """
    if register_fn is not None:
        if ready_host is not None and ready_port is not None:
            if not _wait_until_server_ready_for_registration(queue, ready_host, ready_port):
                return
        register_fn()
    _wait_for_shutdown_signal(queue)


def _wait_for_shutdown_signal(queue):
    while True:
        try:
            if queue.get(timeout=1.0) == 0:
                return
        except queue_lib.Empty:
            # Si el procés principal (el servidor Flask) ha mort, ens aturem
            # per no quedar com a procés orfe.
            if os.getppid() == 1:
                return


def serve_agent(app, hostname, port, register_fn=None, behaviour_fn=None):
    """Arrenca el comportament concurrent en un Process + el servidor Flask.

    Segueix el patró dels exemples del professor:
    `Process(target=agentbehavior1, args=(cola,))` + `app.run(...)` + `join()`.
    El registre al directori passa dins del comportament concurrent.
    """
    _ensure_port_available(hostname, port)
    behaviour_target = behaviour_fn or _agent_behaviour
    try:
        context = multiprocessing.get_context("fork")
    except ValueError:  # plataformes sense fork (p.ex. Windows): context per defecte
        context = multiprocessing.get_context()
    queue = context.Queue()
    behaviour = context.Process(target=behaviour_target, args=(queue, register_fn, hostname, port))
    behaviour.daemon = True
    behaviour.start()
    try:
        app.run(host=hostname, port=port, debug=False, use_reloader=False)
    finally:
        queue.put(0)
        behaviour.join(timeout=5)
        if behaviour.is_alive():
            behaviour.terminate()
