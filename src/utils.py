import inspect
from typing import Generator


def get_all_subclasses(cls) -> Generator[type, None, None]:
    for subclass in cls.__subclasses__():
        if not inspect.isabstract(subclass):
            yield subclass
        yield from get_all_subclasses(subclass)
