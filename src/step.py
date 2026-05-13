import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def step(name=None):
    def decorator(fn):
        step_name = name or fn.__name__

        @wraps(fn)
        def wrapper(*args, **kwargs):
            logger.info("step.start", extra={"step": step_name})
            t0 = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception:
                duration = time.perf_counter() - t0
                logger.exception(
                    "step.fail",
                    extra={"step": step_name, "duration_s": round(duration, 3)},
                )
                raise
            duration = time.perf_counter() - t0
            logger.info(
                "step.ok",
                extra={"step": step_name, "duration_s": round(duration, 3)},
            )
            return result

        return wrapper

    return decorator
