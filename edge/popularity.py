
class PopularityCache:

    def __init__(self, capacity=3):
        self.capacity = capacity
        self.cache = {}
        self.frequency = {}

    def get(self, key):

        if key not in self.cache:
            return None

        # Increase access frequency
        self.frequency[key] += 1

        return self.cache[key]

    def put(self, key, value):

        if key in self.cache:
            self.cache[key] = value
            return

        # Check if cache is full
        if len(self.cache) >= self.capacity:

            # Find the least frequently used file
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
