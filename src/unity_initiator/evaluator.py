from .actions import ACTION_MAP
from .utils.logger import logger


class Evaluator:

    def __init__(self, config, action_map=ACTION_MAP):
        self._config = config
        self._action_map = action_map
        logger.debug("instantiated Evaluator object")
        logger.debug("")

    def get_actions(self):
        return
