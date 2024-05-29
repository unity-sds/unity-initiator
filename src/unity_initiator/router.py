import asyncio
import json

from .evaluator import Evaluator
from .utils.conf_utils import YamlConf, YamlConfEncoder
from .utils.logger import logger


class NoEvaluatorRegexMatched(Exception):
    pass


class Router:
    def __init__(self, config_file):
        self._config_file = config_file
        self._config = YamlConf(self._config_file)

    def get_evaluators_by_url(self, url):
        found_match = False
        for url_cfg in (
            self._config.get("initiator_config").get("payload_type").get("url", [])
        ):
            for regex in url_cfg.get("regexes", []):
                logger.debug("regex: %s", regex)
                match = regex.search(url)
                logger.debug("match: %s", match)
                if match:
                    found_match = True
                    for eval_cfg in url_cfg.get("evaluators", []):
                        logger.debug(
                            "eval_cfg: %s",
                            json.dumps(eval_cfg, cls=YamlConfEncoder, indent=2),
                        )
                        yield Evaluator(eval_cfg, url, match.groupdict())
        if not found_match:
            raise NoEvaluatorRegexMatched(f"No regex matched url {url}.")

    async def resolve_async_actions(self, url):
        return await asyncio.gather(
            *[
                action.async_execute()
                for evaluator in self.get_evaluators_by_url(url)
                for action in evaluator.get_actions()
            ]
        )

    def execute_actions(self, url):
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
        results = loop.run_until_complete(self.resolve_async_actions(url))
        loop.close()
        return results
