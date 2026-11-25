
from collections import OrderedDict


class PopularityCache:

    def __init__(self, capacity=3):
        self.capacity = capacity
        # Ordered from least to most recently used
        self.cache = OrderedDict()
        self.frequency = {}

    def get(self, key):

        if key not in self.cache:
            return None

        # Increase access frequency
        self.frequency[key] += 1
        self.cache.move_to_end(key)

        return self.cache[key]

    def put(self, key, value):

        if self.capacity <= 0:
            return

        if key in self.cache:
            self.cache[key] = value
            self.cache.move_to_end(key)
            return

        # Check if cache is full
        if len(self.cache) >= self.capacity:

            # Find the least frequently used file;
            # min() picks the least recently used one on ties
            least_popular = min(
                self.cache,
                key=lambda k: self.frequency[k]
            )

            # Remove the least popular file
            del self.cache[least_popular]
            del self.frequency[least_popular]

            print(f"LFU EVICTED: {least_popular}")

        # Add new file
        self.cache[key] = value
        self.frequency[key] = 1
