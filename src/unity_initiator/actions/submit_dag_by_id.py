from ..utils.logger import logger
from .base import Action

__all__ = ["SubmitDagByID"]


class SubmitDagByID(Action):

    def __init__(self, payload, payload_info, params):
        super().__init__(payload, payload_info, params)
        logger.info("instantiated %s", __class__.__name__)

    def execute(self):
        return {"success": True}
