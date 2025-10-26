"""
The main server program that starts the HTTP server and listens for incoming connections.
Runs up to the maximum number of threads defined in thread_utils.py.
"""

import socket
import sys

# Project imports
from thread_utils import initialize_socket_thread


HOST = "127.0.0.1"
MAX_LISTEN_QUEUE_SIZE = 0
PORT = 8080


# SERVER BEHAVIOUR
def start_server():
    """The main server loop that listens for incoming connections and handles requests."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_LISTEN_QUEUE_SIZE)  # Listen for incoming connections
        print(f"Server is listening for request on {HOST}:{PORT}")

        while True:  # Loop forever
            print("Waiting for connection")
            conn, addr = server_socket.accept()  # Accept a new connection
            initialize_socket_thread(conn, addr)


# Entry point
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit() and 0 < int(sys.argv[1]) < 65536:
            PORT = int(sys.argv[1])

    start_server()
