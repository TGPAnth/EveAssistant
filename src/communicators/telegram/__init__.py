import config

from telegram.ext import Updater
from telegram.ext import MessageHandler, Filters

from src.communicators import BaseCommunicator, Message
from src.communicators.telegram.command_handler import CommandHandlers
from src.logger import get_logger

log = get_logger('comm.telegram')


class Telegram(BaseCommunicator):
    def __init__(self, config):
        self._updater = Updater(token=config.bot_token)
        self._dispatcher = self._updater.dispatcher
        self.commands = CommandHandlers(self._dispatcher)

    def set_handler(self, handler):
        def core_handler(bot, update):
            message = Message(msg=update.message.text,
                              source='telegram')
            resp = handler(message)
            if not isinstance(resp, basestring):
                resp = 'wat?'
            bot.send_message(chat_id=update.message.chat_id,
                             text=resp)

        message_handler = MessageHandler(Filters.text, core_handler)
        self._dispatcher.add_handler(message_handler)

    def start(self):
        self._updater.start_polling()

    def stop(self):
        self._updater.stop()
