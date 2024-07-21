from djamago import *
from . import expressions
from .topics.main import Main


class Shellsy(Djamago):
    def __init__(self):
        super().__init__("Shellsy")


Shellsy.topic(Main)
