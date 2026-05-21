from ..dispatch import Dispatcher
from .ptx import PTXFile

class PTXDispatcher(Dispatcher):
    name = 'sass'

    def can_handle_by_ext(self, filename):
        return filename.endswith('.ptx')

    def loader(self):
        return PTXFile

    def classifier(self):
        return PTXClassifier

    def converter(self):
        return PTX2C

    def counter(self):
        return PTXCounter
