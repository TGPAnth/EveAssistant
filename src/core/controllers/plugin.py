from src.core.controllers import BaseController
from src.logger import get_logger

log = get_logger('plugins')


class Plugin(BaseController):
    def __init__(self, config, modules_folder='plugins'):
        super(Plugin, self).__init__(modules_folder)
        self._plugins = self._get_init_classes(self.modules_folder, config=config)

    def process_message(self, message):
        res = None
        for plugin in self._plugins:
            try:
                res = self._plugins[plugin].process_message(message)
            except Exception, e:
                log.error('Exception while processing %s: %s' % (plugin, str(e)))
                raise
            if res is not None:
                break
        return res
