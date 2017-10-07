"""
import all modules

communication:
request channels - telegram, voice
response channels - =/=
"""
from src.communicators import Message
from src.config import parse_config
from src.core.controllers.communicator import Communicator
from src.core.controllers.plugin import Plugin
from src.logger import logger_init, get_logger

log = get_logger('core')


class Core(object):
    def __init__(self, config_path):
        self._config = parse_config(config_path)
        logger_init(self._config.core.logger)
        self._communicators = Communicator(self._config.communicators)
        self._plugins = Plugin(self._config.plugins)

    def user_message_handler(self, message):
        if not isinstance(message, Message):
            message = Message(msg=message)
        log.debug(message)
        response = self._plugins.process_message(message)
        if not response:
            response = 'Sorry, we cannot find processor for this request =('
        return response

    def run(self):
        self._communicators.set_handler(self.user_message_handler)
        self._communicators.start()
