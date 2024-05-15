import os

from ..router import Router
from ..utils.logger import logger


def lambda_handler(event, context):
    logger.info("context: %s", context)
    router_cfg = os.environ["ROUTER_CFG"]
    router_file = "/tmp/router.yaml"
    with open(router_file, "w", encoding="utf-8") as f:
        f.write(router_cfg)
    router = Router(router_file)
    return router.execute_actions(event["payload"])
