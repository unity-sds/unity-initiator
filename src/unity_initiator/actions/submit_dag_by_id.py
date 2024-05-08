from ..utils.logger import logger
from .base import Action

__all__ = ["SubmitDagByID"]


class SubmitDagByID(Action):

    def __init__(self, config):
        super().__init__(config)
        logger.debug("instantiated SubmitDagByID object")
