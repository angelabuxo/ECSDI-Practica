"""Utilitats compartides entre agents Flask/ACL.

Aquest mòdul agrupa operacions repetides a múltiples agents:
- obtenció d'IP client des de la request
- transformació d'URLs d'agent cap a altres endpoints
- resolució d'agents via servei de directori
"""

from urllib.parse import urlsplit, urlunsplit

from protocols.directory import (
    build_search_message,
    parse_directory_response,
    parse_directory_responses,
)


def get_client_ip_from_request(flask_request):
    """Retorna la IP efectiva del client (compatible amb proxy)."""
    forwarded = flask_request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return flask_request.remote_addr or "unknown"


def replace_url_path(address, new_path):
    """Substitueix el path d'una URL mantenint host i esquema."""
    parsed = urlsplit(address)
    return urlunsplit((parsed.scheme, parsed.netloc, new_path, "", ""))


def resolve_agent_via_directory(agent, directory_agent, message_sender, next_counter, agent_type):
    """Resol un únic agent d'un tipus concret via directori."""
    message = build_search_message(agent, agent_type, directory_agent, msgcnt=next_counter())
    response = message_sender(message, directory_agent.address)
    return parse_directory_response(response)


def resolve_agents_via_directory(agent, directory_agent, message_sender, next_counter, agent_type):
    """Resol tots els agents d'un tipus concret via directori."""
    message = build_search_message(agent, agent_type, directory_agent, msgcnt=next_counter())
    response = message_sender(message, directory_agent.address)
    return parse_directory_responses(response)
