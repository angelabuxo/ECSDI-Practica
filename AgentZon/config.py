"""Shared configuration and bootstrap helpers for AgentZon agents."""

from pathlib import Path

from AgentUtil.ACLMessages import register_agent
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
from AgentUtil.OntoNamespaces import AGN


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_DIR = BASE_DIR / "web" / "templates"
ONTOLOGY_PATH = BASE_DIR / "ontologia" / "AgentZonOntology.rdf"
DEFAULT_BIND_HOST = "0.0.0.0"
DEFAULT_LOCAL_HOST = "127.0.0.1"


DEFAULT_PORTS = {
    "directory": 9000,
    "cercador": 9001,
    "compra": 9002,
    "centre_logistic": 9003,
    "opinador": 9004,
    "transport_fast": 9010,
    "transport_economy": 9011,
}


def build_agent(name, uri_name, port, host="127.0.0.1", endpoint="/comm"):
    return Agent(
        name=name,
        uri=AGN[uri_name],
        address=f"http://{host}:{port}{endpoint}",
        stop=f"http://{host}:{port}/stop",
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


def register_with_directory(agent, directory_agent, agent_type, msgcnt=0):
    try:
        register_agent(agent, directory_agent, agent_type, msgcnt)
    except Exception:
        return False
    return True
