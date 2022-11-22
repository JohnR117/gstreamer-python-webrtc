import typing

T = typing.TypeVar("T")


class RingBuffer(typing.Generic[T]):
    def __init__(self, size: int) -> None:
        self.size = size
        self.start = 0
        self.end = 0
        self.count = 0
        self.list: "list[T]" = [None] * self.size

    def push(self, item: "T"):
        self.list[self.end] = item
        self.end = (self.end + 1) % self.size
        if self.end == self.start:
            self.start = (self.start + 1) % self.size
        else:
            self.count += 1

    def __iter__(self):
        end = self.end
        # def gen():
        index = self.start
        end = self.end
        while True:
            if index == end:
                break
            yield self.list[index]
            index = (index + 1) % self.size
        # return gen()

    def __del__(self):
        self.clear()

    def clear(self):
        self.start = 0
        self.end = 0
        self.count = 0
        self.list: "list[T]" = [None] * self.size


T = typing.TypeVar("T")
KEY = typing.TypeVar("KEY")


class RingBufferWithKey(typing.Generic[T]):
    def __init__(self, size: int, get_key: "typing.Callable[[T],KEY]") -> None:
        self.size = size
        self.start = 0
        self.end = 0
        self.count = 0
        self.get_key = get_key
        self._list: "list[T]" = [None] * self.size
        self._dict: "dict[KEY, T]" = {}

    def push(self, item: "T"):
        self._list[self.end] = item
        self.end = (self.end + 1) % self.size
        if self.end == self.start:
            self._dict.pop(self.get_key(self._list[self.start]), None)
            self.start = (self.start + 1) % self.size
        else:
            self.count += 1
        self._dict[self.get_key(item)] = item

    def __iter__(self):
        end = self.end
        index = self.start
        end = self.end
        while True:
            if index == end:
                break
            yield self._list[index]
            index = (index + 1) % self.size
        # return gen()

    def clear(self):
        self.start = 0
        self.end = 0
        self.count = 0
        self._list: "list[T]" = [None] * self.size
        self._dict: "dict[KEY, T]" = {}

    def __getitem__(self, key: KEY) -> T:
        return self._dict[key]

    def get(self, key: "KEY", default=None) -> T:
        return self._dict.get(key, default)
