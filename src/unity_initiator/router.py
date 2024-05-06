from .utils.conf_utils import parse_router_file
from .utils.logger import logger


class Router:

    def __init__(self, config_file):
        self._config_file = config_file
        self._config = parse_router_file(self._config_file)
        logger.info("Successfully validated router config %s.", self._config_file)
