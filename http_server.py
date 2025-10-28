"""
The main server program that starts the HTTP server and listens for incoming connections.
Runs up to the maximum number of threads defined in thread_utils.py.
"""

import logging
import socket
import sys

# Project imports
from thread_utils import (
    initialize_socket_thread,
    logger,
    start_worker_pool,
    stop_worker_pool,
)
from cache_utils import Cache


HOST = "127.0.0.1"
MAX_LISTEN_QUEUE_SIZE = 256
PORT = 8080

# ANSI color codes
RESET = "\033[0m"
COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
}


class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, RESET)
        message = super().format(record)
        return f"{color}{message}{RESET}"


formatter = ColorFormatter("[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s")

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[handler])


# SERVER BEHAVIOUR
def start_server():
    """The main server loop that listens for incoming connections and handles requests."""

    cache = Cache()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_LISTEN_QUEUE_SIZE)  # Listen for incoming connections
        start_worker_pool()
        logger.info("Server is listening for request on %s:%s", HOST, PORT)

        try:
            while True:  # Loop forever
                logger.debug("Waiting for connection")
                conn, addr = server_socket.accept()  # Accept a new connection
                initialize_socket_thread(conn, addr, cache)
        except KeyboardInterrupt:
            logger.info("Server is shutting down due to keyboard interrupt")
        finally:
            stop_worker_pool()
            logger.info("Server has shut down")


# Entry point
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit() and 0 < int(sys.argv[1]) < 65536:
            PORT = int(sys.argv[1])

    start_server()
