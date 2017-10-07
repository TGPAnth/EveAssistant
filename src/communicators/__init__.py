class Message(object):
    def __init__(self, msg='', source=None):
        self.msg = msg.lower()
        self.source = source

    def __str__(self):
        s = u'<Message msg:[%s]|src:[%s]>' % (self.msg, self.source)
        return s


class BaseCommunicator(object):
    def start(self):
        pass

    def stop(self):
        pass

    def set_handler(self, handler):
        pass
