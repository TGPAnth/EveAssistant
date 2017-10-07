import importlib
import pkgutil

from collections import defaultdict
from src.core.utils.modules import ModuleImportMixin


class BaseController(ModuleImportMixin):
    def __init__(self, modules_folder):
        super(BaseController, self).__init__()
        self.modules_folder = modules_folder

    def _get_init_classes(self, module_name, config):
        comms = self._import_submodules(module_name)
        result = defaultdict()
        for channel in comms:
            comm_instance = comms[channel](config=getattr(config, channel))
            result[channel] = comm_instance
        return result
