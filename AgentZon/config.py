from pathlib import Path

from AgentZon.AgentUtil.Agent import Agent
from AgentZon.AgentUtil.OntoNamespaces import AGN


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_DIR = BASE_DIR / "web" / "templates"
ONTOLOGY_PATH = BASE_DIR / "ontologia" / "AgentZonOntology.rdf"


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
