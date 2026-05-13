import logging
import sys
from datetime import datetime, timezone
import json
from pathlib import Path

_SKIP_ATTRS = frozenset({
    "name", "msg", "args", "created", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs", "message",
    "pathname", "process", "processName", "relativeCreated",
    "stack_info", "thread", "threadName", "exc_info", "exc_text",
    "taskName",
})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        log = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.message,
            "logger": record.name,
        }

        for key, val in record.__dict__.items():
            if key not in _SKIP_ATTRS:
                log[key] = val

        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)

        if record.stack_info:
            log["stack"] = self.formatStack(record.stack_info)

        return json.dumps(log, ensure_ascii=False, default=str)


def setup_logger(name: str = "src") -> logging.Logger:
    """Configure handlers on the given logger (idempotent).

    Call once at the entrypoint with the package name. Module-level loggers
    obtained via logging.getLogger(__name__) will propagate to this one.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False

    Path("logs").mkdir(exist_ok=True)
    formatter = JsonFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    file_handler = logging.FileHandler(f"logs/etl_{datetime.now():%Y%m%d}.log")
    file_handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.addHandler(file_handler)

    return logger
