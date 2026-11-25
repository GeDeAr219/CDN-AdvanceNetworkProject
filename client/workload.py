
import random

FILES = ["a.txt", "b.txt", "c.txt", "d.txt"]


# Scenario 1: Popular Content
def popular_content():
    rng = random.Random(42)

    return rng.choices(
        FILES,
        weights=[7, 1, 1, 1],
        k=60
    )


# Scenario 2: Recent Content
def recent_content():
    requests = []

    groups = [
        ["a.txt", "b.txt", "c.txt"],
        ["b.txt", "c.txt", "d.txt"],
        ["a.txt", "c.txt", "d.txt"]
    ]

    for group in groups:
        for i in range(20):
            requests.append(group[i % 3])

    return requests


# Scenario 3: Random Requests
def random_content():
    rng = random.Random(42)

    return [
        rng.choice(FILES)
        for _ in range(60)
    ]


if __name__ == "__main__":

    scenarios = {
        "Popular": popular_content(),
        "Recent": recent_content(),
        "Random": random_content()
    }

    for name, requests in scenarios.items():
        print(f"\n{name} Scenario")
        print(f"Total Requests: {len(requests)}")
        print(f"First 10 Requests: {requests[:10]}")
