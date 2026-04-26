from pathlib import Path

from rdflib import Namespace


# Directori base del projecte AgentZon. La resta de rutes pengen d'aquí perquè
# tots els agents comparteixin la mateixa configuració.
ROOT_DIR = Path(__file__).resolve().parent

# Ontologia comuna del sistema.
ONTOLOGY_PATH = ROOT_DIR / "ontologia" / "AgentZonOntology.rdf"

# Dades compartides entre agents.
DATA_DIR = ROOT_DIR / "data"
PRODUCTES_PATH = DATA_DIR / "productes.json"
DADES_ENVIAMENT_USUARI_PATH = DATA_DIR / "dades_enviament_usuari.json"
UBICACIONS_PRODUCTES_PATH = DATA_DIR / "ubicacions_productes.json"
RESPONSABLE_ENVIAMENT_PRODUCTES_PATH = DATA_DIR / "responsable_enviament_productes.json"

# Recursos web compartits per les interfícies HTML dels agents.
WEB_DIR = ROOT_DIR / "web"

# Namespace de l'ontologia AgentZon.
AGENTZON = Namespace("http://www.semanticweb.org/upc/ontologies/2026/3/untitled-ontology-15#")
