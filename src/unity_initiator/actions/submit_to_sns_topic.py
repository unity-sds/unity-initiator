from ..utils.logger import logger
from .base import Action

__all__ = ["SubmitToSNSTopic"]


class SubmitToSNSTopic(Action):

    def __init__(self, config):
        super().__init__(config)
        logger.debug("instantiated SubmitToSNSTopic object")
