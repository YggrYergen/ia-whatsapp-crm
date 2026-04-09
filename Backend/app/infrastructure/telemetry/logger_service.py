# ================================================================================
# ⚠️  DOCS FIRST:
#     - Cloud Logging Structured Logging: https://cloud.google.com/logging/docs/structured-logging
#     - Python standard logging: https://cloud.google.com/logging/docs/setup/python
#
#     Per Google Cloud docs, Cloud Run automatically sends stdout/stderr to Cloud Logging.
#     If the output is a JSON string on a SINGLE LINE, Cloud Logging parses it as structured log.
#     Recognized fields: "severity", "message", "timestamp", "logging.googleapis.com/trace"
#
#     PREVIOUS BUG: orjson.dumps() produced correct JSON but the QueueHandler/QueueListener
#     combo was interfering with the output format, causing Cloud Logging to display [object Object].
#     FIX: Use json.dumps() for maximum compatibility and add the StreamHandler directly to the
#     logger (no QueueHandler in production) to ensure clean single-line JSON output to stdout.
# ================================================================================
import logging
import logging.handlers
import queue
import sys
import json
from datetime import datetime, timezone
from app.core.config import settings


class CloudLoggingJSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON strings compatible with Google Cloud Logging.
    
    Per docs: https://cloud.google.com/logging/docs/structured-logging
    Cloud Logging recognizes these special fields:
      - severity: Maps to Cloud Logging severity levels
      - message: The log message text
      - timestamp: ISO 8601 timestamp  
      - logging.googleapis.com/trace: For trace correlation
    """
    
    # Map Python log levels to Cloud Logging severity levels
    # Ref: https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#LogSeverity
    SEVERITY_MAP = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
        "CRITICAL": "CRITICAL",
    }
    
    def format(self, record):
        log_entry = {
            "severity": self.SEVERITY_MAP.get(record.levelname, "DEFAULT"),
            "message": record.getMessage(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "module": record.module,
            "logger": record.name,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["error"] = self.formatException(record.exc_info)
        # json.dumps guarantees a single-line string (no newlines in output)
        # This is critical for Cloud Logging to parse it correctly
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(name: str = "whatsapp-crm"):
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger

    # Map dynamic levels safely based on validation strings
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    if settings.ENVIRONMENT == "development":
        # Development: human-readable format with QueueHandler for non-blocking IO
        log_queue = queue.Queue(-1)
        queue_handler = logging.handlers.QueueHandler(log_queue)
        logger.addHandler(queue_handler)
        
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | [%(module)s] | %(message)s",
            datefmt="%H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        
        listener = logging.handlers.QueueListener(log_queue, stream_handler)
        listener.start()
    else:
        # Production: JSON format directly to stdout for Cloud Logging
        # NO QueueHandler — write directly to ensure clean single-line JSON output.
        # The QueueHandler was causing the [object Object] issue by wrapping the output.
        # Per: https://cloud.google.com/logging/docs/structured-logging
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(CloudLoggingJSONFormatter())
        logger.addHandler(stream_handler)

    return logger


# Safely bootstrapped unique instance module-wide 
logger = setup_logger()
