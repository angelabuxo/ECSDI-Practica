# -*- coding: utf-8 -*-
"""
Utilitats compartides entre agents Flask/ACL (resolucio de directori, URLs, IP client).
"""

from urllib.parse import urlsplit, urlunsplit

from protocols.directory import (
    build_search_message,
    parse_directory_response,
    parse_directory_responses,
)


def get_client_ip_from_request(flask_request):
    forwarded = flask_request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return flask_request.remote_addr or "unknown"


def replace_url_path(address, new_path):
    parsed = urlsplit(address)
    return urlunsplit((parsed.scheme, parsed.netloc, new_path, "", ""))


def resolve_agent_via_directory(agent, directory_agent, message_sender, msgcnt_fn, agent_type):
    message = build_search_message(agent, agent_type, directory_agent, msgcnt=msgcnt_fn())
    response = message_sender(message, directory_agent.address)
    return parse_directory_response(response)


def resolve_agents_via_directory(agent, directory_agent, message_sender, msgcnt_fn, agent_type):
    message = build_search_message(agent, agent_type, directory_agent, msgcnt=msgcnt_fn())
    response = message_sender(message, directory_agent.address)
    return parse_directory_responses(response)
