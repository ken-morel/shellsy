import sys
from types import ModuleType
from typing import Callable
from functools import wraps
from importlib import import_module
from threading import Thread


class ComberloadModule(ModuleType):
    worker_running = False
    should_work = True
    backlog = []
    done = []
    comberloaders = []

    class ComberLoader:
        _fallback = None

        def __init__(self, modules, func, default):
            self.__func__ = func
            self.modules = modules
            self.default = default
            ComberloadModule.comberloaders.append(self)
            self.comberloaded = (
                len(set(ComberloadModule.backlog) & set(modules)) == 0
            )
            # wraps(func)(self.__call__)

        def call(self, *args, **kw):
            if self._fallback:
                return self._fallback(*args, **kw)
            else:
                return self.default

        def fallback(self, func: Callable):
            self._fallback = func
            return func

        def __call__(self, *args, **kw):
            if hasattr(self, "__self__"):
                return self.call(self.__self__, *args, **kw)
            else:
                return self.call(*args, **kw)

        def __get__(self, instance, *__, **_):
            self.__self__ = instance
            return self

    def __init__(self):
        super().__init__(__name__)
        self.start_worker()

    def __str__(self):
        return "<Comberload module>"

    def __call__(self, modules: list[str], default=None):
        """
        THis registers modules for comberloading
        :param modules: The list of modules to load

        :returns: A registerer to conditionally call a function
        """
        if isinstance(modules, str):
            modules = [modules]
        self.backlog.extend(modules)
        self.start_worker()

        def register_func(func: Callable):
            return ComberloadModule.ComberLoader(modules, func, default)

        return register_func

    def install(self):
        sys.modules[__name__] = self

    def start_worker(self):
        if not self.worker_running:
            self._worker_thread = Thread(target=self._worker)
            self._worker_thread.start()
            return True
        else:
            return False

    def should_exit(self):
        self.should_work = False

    def _worker(self):
        self.worker_running = True
        for modules in self.backlog:
            self.importing = True
            modules = modules.split(".")
            for depth in range(len(modules)):
                module = ".".join(modules[: depth + 1])
                if module in self.done:
                    continue
                import_module(module)
                if module in self.backlog:
                    self.backlog.remove(module)
                self.done.append(module)
                for loader in ComberloadModule.comberloaders:
                    if loader.comberloaded:
                        continue
                    if (
                        len(
                            set(ComberloadModule.backlog) & set(loader.modules)
                        )
                        == 0
                    ):
                        loader.comberloaded = True
                        loader.call = loader.__func__
            self.importing = False
        self.worker_running = False


ComberloadModule().install()
