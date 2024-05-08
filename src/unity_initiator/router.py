import json

from .evaluator import Evaluator
from .utils.conf_utils import YamlConf, YamlConfEncoder
from .utils.logger import logger


class Router:

    def __init__(self, config_file):
        self._config_file = config_file
        self._config = YamlConf(self._config_file)

    def get_evaluators_by_url(self, url):
        for url_cfg in (
            self._config.get("initiator_config").get("payload_type").get("url", [])
        ):
            for regex in url_cfg.get("regexes", []):
                logger.debug("regex: %s", regex)
                match = regex.search(url)
                logger.debug("match: %s", match)
                if match:
                    for eval_cfg in url_cfg.get("evaluators", []):
                        logger.info(
                            "eval_cfg: %s",
                            json.dumps(eval_cfg, cls=YamlConfEncoder, indent=2),
                        )
                        yield Evaluator(eval_cfg, url, match.groupdict())
