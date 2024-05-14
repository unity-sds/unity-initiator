import json

from .actions import ACTION_MAP
from .utils.logger import logger


class Evaluator:
    def __init__(self, config, payload, payload_info, action_map=ACTION_MAP):
        self._config = config
        self._payload = payload
        self._payload_info = payload_info
        self._action_map = action_map
        self._name = self._config.get("name")

    @property
    def name(self):
        return self._name

    def get_actions(self):
        for act_cfg in self._config.get("actions", []):
            logger.debug("act_cfg: %s", json.dumps(act_cfg, indent=2))
            act_name = act_cfg.get("name")
            yield ACTION_MAP[act_name](
                self._payload, self._payload_info, act_cfg["params"]
            )
