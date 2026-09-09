import logging
import logging.config


class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level):
        self.max_level = max_level

    def filter(self, record):
        return record.levelno <= self.max_level


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
