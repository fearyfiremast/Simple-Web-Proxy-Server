"""A module to manage threading for the HTTP server."""

import socket
import threading
from cache_utils import Cache

# Project imports
from message_utils import handle_request

MAX_THREAD_COUNT = 1
SOCKET_THREADS = []
SOCKET_THREADS_LOCK = threading.Lock()

# TODO: Consider creating a custom thread class


def initialize_socket_thread(conn: socket.socket, addr, cache : Cache):
    """
    Function is repsonsible for dispatching threads. If the number of active threads is less than
    MAX_THREAD_COUNT then the thread is added to an array started.
    Otherwise the socket is closed and no thread is created.\n

    Args:
        conn (socket.socket): A newly accepted socket object
        addr: tuple that contains the clients ip and port number
    """
    print("server")
    # Lock THREADS_LOCK list before checking capacity and appending thread
    with SOCKET_THREADS_LOCK:
        if len(SOCKET_THREADS) >= MAX_THREAD_COUNT:
            with conn:
                # threads at capacity
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()
                print("Thread limit reached")
                return

        # Thread creation.
        t = threading.Thread(target=thread_socket_main, args=(conn, addr, cache))
        SOCKET_THREADS.append(t)

    # Start the thread outside of the lock
    t.start()
    print(f"number of active threads: {len(SOCKET_THREADS)}", flush=True)
    return


def thread_socket_main(conn: socket.socket, addr, cache : Cache):
    """Function is spun up for each active thread. Handles HTTP server send and receive.\n

    Args:
        conn (socket.socket): A newly accepted socket object
        addr: tuple that contains the clients ip and port number
    """
    print(f"thread_socket_main: Connected by {addr}", flush=True)
    with conn:
        request = b""
        while True:
            # Read request data until the end of headers
            while b"\r\n\r\n" not in request:
                data = conn.recv(1024)
                if not data:
                    break
                request += data
            if not request:
                break
            response = handle_request(request, cache)
            conn.sendall(response)
            request = b""

        # thread termination process occurs after break
        # Lock SOCKET_THREADS list, remove thread from list
        with SOCKET_THREADS_LOCK:
            try:
                SOCKET_THREADS.remove(threading.current_thread())
            except ValueError:
                print("Thread not found in active thread list", flush=True)
        # with conn: context manager closes the socket
    print(
        f"thread_socket_main: Connection closed. Number of active threads: {len(SOCKET_THREADS)}",
        flush=True,
    )
    print("thread_socket_main: Done", flush=True)
    return
