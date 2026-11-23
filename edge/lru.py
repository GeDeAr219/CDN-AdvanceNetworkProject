
from collections import OrderedDict


class LRUCache:

    def __init__(self, capacity=3):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key):

        if key not in self.cache:
            return None

        # Move recently used item to the end
        self.cache.move_to_end(key)

        return self.cache[key]

    def put(self, key, value):

        if key in self.cache:
            self.cache.move_to_end(key)

        self.cache[key] = value

        # Remove least recently used item
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
