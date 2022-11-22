import typing
T = typing.TypeVar("T")


class Event(typing.Generic[T]):

    class _Target(typing.Generic[T]):
        def __init__(self, f: T, is_new=True) -> None:
            self.f = f
            self.is_new = is_new

        def __eq__(self, f: object) -> bool:
            return self.f.__eq__(f)

        def __call__(self, *a, **kw):
            self.is_new = False
            return self.f(*a, **kw)

    def __init__(self, name):
        self.targets: "list[self._Target(T)]" = []
        self.__name__ = name

    def __del__(self):
        self.clear()

    def __repr__(self):
        # return f"event '{self.__name__}', listeners: {len(self)}"
        return f"Event(\"{self.__name__}\")"

    def __call__(self, *a, **kw):
        ret = None
        for target in tuple(self.targets):
            ret = target(*a, **kw)
        # for i in range(len(self.targets)):
        #     ret = self.targets[i](*a, **kw)
        return ret

    def get_new(self):
        return tuple(target for target in self.targets if target.is_new)

    def __iadd__(self, f: "T"):
        self.append(f)
        return self

    def __isub__(self, f: "T"):
        try:
            self.remove(f)
        except BaseException as e:
            pass
        return self

    def __len__(self):
        return len(self.targets)

    def __iter__(self):
        # def gen():
        for target in self.targets:
            yield target
        # return gen()

    def __getitem__(self, key):
        return self.targets[key]

    def __bool__(self):
        return True

    def append(self, f: "T", is_new=True):
        return self.targets.append(self._Target(f, is_new))

    def insert(self, index: int, f: "T", is_new=True):
        return self.targets.insert(index, self._Target(f, is_new))

    def remove(self, f: "T"):
        return self.targets.remove(f)

    def clear(self):
        return self.targets.clear()
