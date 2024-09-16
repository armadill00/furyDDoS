A Python script designed for sending high volumes of Layer 7 (HTTP) requests to a server using concurrent threads. Ideal for stress testing or benchmarking web applications, with support for detailed verbose output.

## Features
* High-Concurrency Requests: Uses a thread pool for sending multiple HTTP requests simultaneously.
* Flexible HTTP Methods: Supports GET and POST requests.
* Verbose Output: Provides detailed information including timestamps, HTTP method, response packet size, and ping response time.
* Command-Line Interface: Configurable via command-line arguments for target URL, HTTP method, number of threads, and verbosity.

## Usage:
Run the script from the command line with the desired options:

python attack.py <target-url> [-m METHOD] [-t THREADS] [-v]
* <target-url>: URL to send requests to (e.g., http://example.com).
* -m METHOD: HTTP method to use (GET or POST). Default is GET.
* -t THREADS: Number of concurrent threads. Default is 100.
* -v: Enable verbose output for detailed logging.

### Example Commands
Send GET requests to http://example.com with 200 threads and verbose output:

python attack.py http://example.com -m GET -t 200 -v

![Exemple on very limited internet](https://ibb.co/1L1YTL7)


## Methods:
* GET
* POST

## Disclaimer
This tool is intended for educational purposes and stress testing only. Do not use it to attack or disrupt services without proper authorization. Unauthorized use of this tool may be illegal and unethical.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

# Contributions
Feel free to open issues or submit pull requests. Contributions are welcome!

