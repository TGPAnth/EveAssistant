import importlib
import inspect
import os
import pkgutil

from .error import ConfigurationError, ConfigFormatError
from .readers import readers

module_list = [
    'src.logger',
    'src.communicators.*',
    'src.plugins.*',
]


def process_module_list(mlist):
    mlist_mod = []
    for module_t in mlist:
        if not module_t.endswith('.*'):
            mlist_mod.append(module_t)
            continue
        module_t = module_t[:-2]
        for importer, modname, ispkg in pkgutil.iter_modules(module_t.split('.')):
            if not ispkg:
                continue
            mlist_mod.append('.'.join([module_t, modname]))
    return mlist_mod


module_list = process_module_list(module_list)


class ConfigContainer(object):
    def __init__(self, data=None):
        if data:
            for key, value in data.items():
                if isinstance(value, dict):
                    setattr(self, key, ConfigContainer(value))
                elif isinstance(value, list):
                    setattr(self, key, container_from_list(value))
                else:
                    setattr(self, key, value)

    def items(self):
        return self.__dict__.items()

    def to_dict(self):
        result = {}
        for key, value in self.items():
            if isinstance(value, ConfigContainer):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = dict_from_list(value)
            elif isinstance(value, tuple):
                result[key] = dict_from_list(value)
            else:
                result[key] = value

        return result


class ImmutableConfigContainer(ConfigContainer):
    def __init__(self, data=None):
        if data:
            for key, value in data.items():
                if isinstance(value, dict) or isinstance(value, ConfigContainer):
                    super(ImmutableConfigContainer, self).__setattr__(key, ImmutableConfigContainer(value))
                elif isinstance(value, list):
                    super(ImmutableConfigContainer, self).__setattr__(key, container_from_list(value, True))
                else:
                    super(ImmutableConfigContainer, self).__setattr__(key, value)

    def __setattr__(self, name, value):
        raise TypeError("'%s' object does not support attribute setting" % self.__class__.__name__)


def container_from_list(data, immutable=False):
    result = []
    cls = ImmutableConfigContainer if immutable else ConfigContainer

    for item in data:
        if isinstance(item, dict) or isinstance(item, ConfigContainer):
            result.append(cls(item))
        elif isinstance(item, list):
            result.append(container_from_list(item, immutable))
        else:
            result.append(item)

    return tuple(result) if immutable else result


def dict_from_list(data):
    result = list()
    for item in data:
        if isinstance(item, list):
            result.append(dict_from_list(item))
        if isinstance(item, ConfigContainer):
            result.append(item.to_dict())
        else:
            result.append(item)

    return result


def parse_file(file_path):
    file_path = os.path.abspath(file_path)
    fmt = os.path.splitext(file_path)[1][1:].lower()
    if fmt not in readers:
        raise ConfigurationError('Unsupported configuration format')

    if not check_file_path(file_path):
        raise ConfigurationError('Can not open configuration file (%s)' % file_path)

    reader = readers[fmt]
    data = reader.from_file(file_path)

    return data


def parse_config(cfg_path):
    config = ConfigContainer(parse_file(cfg_path))
    _process(config, module_list)  # process kernel modules
    return ImmutableConfigContainer(config)


def _process(config, modules):
    # try:
    for module_name in modules:
        try:
            module_t = importlib.import_module('.config', package=module_name)
        except ImportError as e:
            raise Exception("Unknown module '%s' (%s)" % (module_name, e))

        # Search configurators
        for key, fn in inspect.getmembers(module_t, lambda x: hasattr(x, 'is_configurator')):
            old_branch = _get_config_branch(config, fn.config_path)
            new_branch = fn(ImmutableConfigContainer(config), **old_branch.__dict__)
            _set_config_branch(config, fn.config_path, new_branch)

            # except Exception as e:
            #     raise ConfigurationError(e)


def _get_config_branch(config, path):
    result = config
    try:
        for part in path.split('.'):
            result = getattr(result, part)
    except AttributeError:
        return ConfigContainer()
    return result


def _set_config_branch(config, path, branch):
    result = config
    parts = path.split('.')
    last = parts.pop()
    for part in parts:
        if not hasattr(result, part) or getattr(result, part) is None:
            setattr(result, part, ConfigContainer())
        result = getattr(result, part)

    setattr(result, last, branch)


def check_file_path(path, mode='r'):
    """
    Check whether a path is valid
    @param path: Filepath
    @type path: basestring
    @param mode: how the file is to be opened
    @type mode: basestring
    @return: True if file path is valid else - False
    @rtype: bool
    """

    if path is None:  # in case if path is not set in config file
        return True

    real_path = os.path.realpath(path)
    if not os.path.basename(real_path):
        return False

    try:
        fp = open(real_path, mode)
        fp.close()
    except IOError:
        return False

    return True


def configurator(path):
    def configurator_decorator(fn):
        assert callable(fn)
        fn.is_configurator = True
        fn.config_path = path
        return fn

    return configurator_decorator
