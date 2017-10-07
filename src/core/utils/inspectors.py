class ClassInspectorMixin(object):
    @staticmethod
    def _find_commands(obj, prefix='_'):
        prefix_len = len(prefix)
        _commands = {}
        for command in dir(obj):
            if not command.startswith(prefix):
                continue
            _commands[command[prefix_len:]] = getattr(obj, command)
        return _commands
