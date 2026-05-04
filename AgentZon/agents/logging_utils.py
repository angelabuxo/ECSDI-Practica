import logging


class InternalAccessFilter(logging.Filter):
    """Hide noisy internal HTTP access logs used for agent-to-agent traffic."""

    INTERNAL_PATTERNS = (
        "GET /comm",
        "GET /Register?content=",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(pattern in message for pattern in self.INTERNAL_PATTERNS)


def configure_pretty_logging() -> None:
    """Configure readable console logging for local agent processes."""
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(levelname)-7s %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root_logger.addHandler(handler)

    root_logger.setLevel(logging.DEBUG)

    werkzeug_logger = logging.getLogger("werkzeug")
    if not any(isinstance(current_filter, InternalAccessFilter) for current_filter in werkzeug_logger.filters):
        werkzeug_logger.addFilter(InternalAccessFilter())
