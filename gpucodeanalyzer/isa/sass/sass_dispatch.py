from ..dispatch import Dispatcher
from . import SASSFile, SASSClassifier, SASS2C

class SASSDispatcher(Dispatcher):
    def can_handle_by_ext(self, filename):
        return filename.endswith('.sass')

    def loader(self):
        return SASSFile

    def classifier(self):
        return SASSClassifier

    def converter(self):
        return SASS2C
