"""
utils/logger.py
---------------
Central logger for the entire pipeline.
Har step ka record rakhta hai — S3 se leke CRM tak.
"""

import logging
import sys
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger with a consistent format.
    Usage: logger = get_logger(__name__)
    """
    logger = logging.getLogger(name)

    # Agar handler already set hai toh dobara mat lagao (duplicate logs avoid karne ke liye)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler — terminal mein dikhega
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Format: [TIME] LEVEL | module_name | message
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
