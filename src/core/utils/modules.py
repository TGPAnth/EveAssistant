import importlib
import pkgutil


class ModuleNotFound(Exception):
    pass


class ModuleImportMixin(object):
    @staticmethod
    def _import_submodules(package):
        if package is None:
            raise ModuleNotFound('Package path is None')
        if isinstance(package, basestring):
            package = importlib.import_module(package)
        results = {}
        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
            if name.startswith('_'):
                continue
            if '.' in name:
                continue
            full_name = package.__name__ + \
                        '.' + name
            imported_module = importlib.import_module(full_name)
            classname = name.title().replace('_', '')
            results[name] = getattr(imported_module, classname)
        return results
