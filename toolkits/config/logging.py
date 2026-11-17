import logging
import logging.config

# Libraries whose loggers set their own level and handlers and don't propagate,
# so they would otherwise ignore --quiet/--verbose.
LIBRARY_LOGGER_PREFIXES = ("five_safes_tes_workbench",)


class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level):
        self.max_level = max_level

    def filter(self, record):
        return record.levelno <= self.max_level


def library_log_level(level: str) -> int:
    """Return the log level for library loggers given the CLI's log level.

    Library INFO messages (such as the Workbench's progress messages and the
    full TES payload) are only shown in verbose mode; their warnings and
    errors are always shown.
    """

    cli_level = logging.getLevelName(level.upper())
    return cli_level if cli_level <= logging.DEBUG else max(cli_level, logging.WARNING)


def _route_library_loggers_to_root(level: int) -> None:
    """Send library log records through the root logger's handlers.

    Five Safes TES Workbench creates its module loggers at import time with a
    private stdout handler, a fixed INFO level and `propagate=False`. Replacing
    those settings makes them follow the CLI's verbosity and its stdout/stderr
    split.
    """

    for name in list(logging.Logger.manager.loggerDict):
        if not name.startswith(LIBRARY_LOGGER_PREFIXES):
            continue
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        logger.setLevel(level)
        logger.propagate = True


def configure_logging(level: str = "INFO") -> None:
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "stdout_max": {
                "()": MaxLevelFilter,
                "max_level": logging.INFO,
            },
        },
        "formatters": {
            "default": {
                "format": "%(levelname)s | %(message)s",
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "default",
                "stream": "ext://sys.stdout",
                "filters": ["stdout_max"],
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "level": level.upper(),
            "handlers": ["stdout", "stderr"],
        },
    }

    logging.config.dictConfig(config)
    _route_library_loggers_to_root(library_log_level(level))
