class Dispatcher:
    def can_handle_by_ext(self, filename):
        raise NotImplementedError

    def loader(self):
        raise NotImplementedError

    def classifier(self):
        raise NotImplementedError
