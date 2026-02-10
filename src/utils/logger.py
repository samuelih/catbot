"""Logging configuration for CatToy."""

import logging
import sys


def setup_logger(name="cattoy", debug=False):
    """Create and configure a logger.

    Args:
        name: Logger name.
        debug: If True, set level to DEBUG. Otherwise INFO.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    fmt = "[%(levelname)s] %(message)s"
    if debug:
        fmt = "[%(levelname)s %(name)s:%(lineno)d] %(message)s"

    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)

    return logger
