from abc import ABC, abstractmethod

__all__ = ["Action"]


class Action(ABC):

    def __init__(self, payload, payload_info, params):
        self._payload = payload
        self._payload_info = payload_info
        self._params = params

    @abstractmethod
    def execute(self):
        pass
