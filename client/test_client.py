
import requests
import time

EDGE_URL = "http://127.0.0.1:5001/content/a.txt"

latencies = []

for i in range(20):

    # Start timer
    start = time.perf_counter()

    # Send HTTP request
    response = requests.get(EDGE_URL, timeout=10)

    # Stop timer
    end = time.perf_counter()

    # Convert seconds to milliseconds
    latency = (end - start) * 1000
    latencies.append(latency)

    cache_status = response.headers.get("X-Cache")

    print(f"Request {i + 1}")
    print(f"Status: {response.status_code}")
    print(f"Cache: {cache_status}")
    print(f"Latency: {latency:.3f} ms")
    print("--------------------")

average_latency = sum(latencies) / len(latencies)

print("\n===== TEST SUMMARY =====")
print(f"Total Requests: {len(latencies)}")
print(f"Average Latency: {average_latency:.3f} ms")
print(f"Minimum Latency: {min(latencies):.3f} ms")
print(f"Maximum Latency: {max(latencies):.3f} ms")