# -*- coding: utf-8 -*-
"""
Utilitats compartides entre agents Flask/ACL (resolucio de directori, URLs, IP client).
"""

import time
from urllib.parse import urlsplit, urlunsplit

from config import DIRECTORY_REGISTER_RETRY_DELAY_SEC

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


def resolve_agent_via_directory(
    agent,
    directory_agent,
    message_sender,
    msgcnt_fn,
    agent_type,
    retries=5,
    retry_delay=DIRECTORY_REGISTER_RETRY_DELAY_SEC,
):
    if directory_agent is None:
        raise ValueError("No hi ha agent de directori configurat")

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            message = build_search_message(agent, agent_type, directory_agent, msgcnt=msgcnt_fn())
            response = message_sender(message, directory_agent.address)
            return parse_directory_response(response)
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(retry_delay)
    raise last_error


def resolve_agents_via_directory(agent, directory_agent, message_sender, msgcnt_fn, agent_type):
    message = build_search_message(agent, agent_type, directory_agent, msgcnt=msgcnt_fn())
    response = message_sender(message, directory_agent.address)
    return parse_directory_responses(response)
