import os
from tempfile import mkstemp

from ..router import Router
from ..utils.logger import logger


def lambda_handler(event, context):
    logger.info("context: %s", context)

    # TODO: Should use either AppConfig or retrieve router config from S3 location.
    # For now, reading router config body from ROUTER_CFG env variable then writing
    # to local file.
    router_cfg = os.environ["ROUTER_CFG"]
    fd, router_file = mkstemp(prefix="router_", suffix=".yaml", text=True)
    with os.fdopen(fd, "w") as f:
        f.write(router_cfg)
    router = Router(router_file)
    os.unlink(router_file)
    return router.execute_actions(event["payload"])
