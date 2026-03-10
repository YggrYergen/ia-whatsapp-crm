import os
import logging
import sys
import json
from datetime import datetime

class CustomLogger:
    def __init__(self):
        self.env = os.getenv("ENVIRONMENT", "development")
        self.logger = logging.getLogger("whatsapp_crm")
        self.logger.setLevel(logging.DEBUG if self.env == "development" else logging.INFO)
        
        # Remove existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()

        if self.env == "development":
            # Rich, readable logs for development
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        else:
            # Structured JSON logs for production (Google Cloud Logging compatible)
            handler = logging.StreamHandler(sys.stdout)
            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    log_record = {
                        "severity": record.levelname,
                        "message": record.getMessage(),
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "logger": record.name,
                        "module": record.module,
                    }
                    if record.exc_info:
                        log_record["stack_trace"] = self.formatException(record.exc_info)
                    return json.dumps(log_record)
            
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)

    def get_logger(self):
        return self.logger

logger = CustomLogger().get_logger()
