from abc import ABC, abstractmethod


class BaseResponder(ABC):
    @abstractmethod
    def __init__(self, config):
        pass

    @abstractmethod
    def update_users(self):
        pass

    @abstractmethod
    def update_kb(self):
        pass

    @abstractmethod
    def response(self, body):
        pass

    @abstractmethod
    def handle_response_user(self, body):
        pass

    @abstractmethod
    def handle_response_expert(self, body):
        pass
