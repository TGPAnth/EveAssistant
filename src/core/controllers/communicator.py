from src.core.controllers import BaseController


class Communicator(BaseController):
    def __init__(self, config, modules_folder='communicators'):
        super(Communicator, self).__init__(modules_folder)
        self._communicators = self._get_init_classes(self.modules_folder, config=config)

    def start(self):
        for comm_name, comm in self._communicators.iteritems():
            comm.start()

    def stop(self):
        for comm_name, comm in self._communicators.iteritems():
            comm.stop()

    def set_handler(self, handler):
        for comm_name, comm in self._communicators.iteritems():
            comm.set_handler(handler=handler)
