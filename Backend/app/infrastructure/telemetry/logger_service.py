import logging
import logging.handlers
import queue
import sys
import orjson
from datetime import datetime
from app.core.config import settings

def setup_logger(name: str = "whatsapp-crm"):
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger

    # Map dynamic levels safely based on validation strings
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    # Infinite Queue limits allowing Non-blocking loops from FastAPI main threat IOs
    log_queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    if settings.ENVIRONMENT == "development":
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | [%(module)s] | %(message)s",
            datefmt="%H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        return logger
    else:
        # Strictly structured JSON logic output
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_record = {
                    "severity": record.levelname,
                    "message": record.getMessage(),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "module": record.module
                }
                if record.exc_info:
                    log_record["error"] = self.formatException(record.exc_info)
                return orjson.dumps(log_record).decode('utf-8')

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(JSONFormatter())

    # Spawn thread dispatcher 
    listener = logging.handlers.QueueListener(log_queue, stream_handler)
    listener.start()

    return logger

# Safely bootstrapped unique instance module-wide 
logger = setup_logger()
