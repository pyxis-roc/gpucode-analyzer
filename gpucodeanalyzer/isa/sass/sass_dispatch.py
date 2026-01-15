from ..dispatch import Dispatcher
from . import SASSFile, SASSClassifier

class SASSDispatcher(Dispatcher):
    def can_handle_by_ext(self, filename):
        return filename.endswith('.sass')

    def loader(self):
        return SASSFile

    def classifier(self):
        return SASSClassifier
