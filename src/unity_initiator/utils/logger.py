import logging
import traceback
from functools import wraps

# set logger and custom filter
log_format = "[%(asctime)s: %(levelname)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)


class LogFilter(logging.Filter):
    def filter(self, record):
        # placeholder for future log filtering logic
        # if not hasattr(record, "id"):
        #    record.id = "--"
        return True


logger = logging.getLogger("unity_initiator")
logger.setLevel(logging.INFO)
logger.addFilter(LogFilter())


def log_exceptions(lambda_handler):
    @wraps(lambda_handler)
    def wrapper(event, context):
        try:
            lambda_handler(event, context)
        except Exception as err:
            tb = traceback.format_exc()
            logger.exception("Got exception: %s\n%s", str(err), tb)
            raise

    return wrapper
