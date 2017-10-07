from telegram.ext import CommandHandler

from src.core.utils.inspectors import ClassInspectorMixin


class CommandHandlers(ClassInspectorMixin):
    def __init__(self, dispatcher):
        _commands = self._find_commands(self, prefix='cmd_')
        self._dispatcher = dispatcher
        self.handlers = self._init_commands(_commands, self._dispatcher)

    @staticmethod
    def cmd_start(bot, update):
        bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")
    
    @staticmethod
    def cmd_hi(bot, update):
        bot.send_message(chat_id=update.message.chat_id, text="Hallo ma friend")

    @staticmethod
    def _init_commands(commands, dispatcher):
        handlers = {}
        for cmd, func in commands.iteritems():
            hndl = CommandHandler(cmd, func)
            dispatcher.add_handler(hndl)
            handlers[cmd] = hndl
        return handlers
