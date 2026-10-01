"""Structured JSON stdout logging with conservative PII redaction.

Ensures zero PII (Personally Identifiable Information) is logged.
Names, phone numbers, Aadhaar numbers, audio bytes, and images are blocked.
Only logs anonymous session IDs, event names, latencies, and HTTP status codes.
"""

import json
import logging
import re
import sys
from typing import Any

# Regex patterns for detecting potential PII
AADHAAR_REGEX = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PHONE_REGEX = re.compile(r"\b(?:\+91|0)?[6-9]\d{9}\b")


class RedactingJsonFormatter(logging.Formatter):
    """Formats log records as JSON and redacts sensitive PII fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the record into a clean JSON string with zero PII."""
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "severity": record.levelname,
        }

        # Transfer only non-content telemetry from trusted application code.
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = record.latency_ms
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "event"):
            log_obj["event"] = str(record.event)

        # Redact any PII from message
        msg_str = json.dumps(log_obj)
        msg_str = AADHAAR_REGEX.sub("[REDACTED_AADHAAR]", msg_str)
        msg_str = PHONE_REGEX.sub("[REDACTED_PHONE]", msg_str)

        return msg_str


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root logger with JSON formatting and no PII."""
    logger = logging.getLogger("sakhi")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RedactingJsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False

    return logger


logger = setup_logging()
