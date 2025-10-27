"""A module to manage threading for the HTTP server."""

import logging
import socket
import threading

# Project imports
from message_utils import handle_request

MAX_THREAD_COUNT = 10
SOCKET_THREADS = []
SOCKET_THREADS_LOCK = threading.Lock()

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

logging.basicConfig(level=logging.DEBUG, handlers=[handler])

logger = logging.getLogger(__name__)

# TODO: Consider creating a custom thread class


def initialize_socket_thread(conn: socket.socket, addr):
    """
    Function is repsonsible for dispatching threads. If the number of active threads is less than
    MAX_THREAD_COUNT then the thread is added to an array started.
    Otherwise the socket is closed and no thread is created.\n

    Args:
        conn (socket.socket): A newly accepted socket object
        addr: tuple that contains the clients ip and port number
    """
    # Lock THREADS_LOCK list before checking capacity and appending thread
    with SOCKET_THREADS_LOCK:
        if len(SOCKET_THREADS) >= MAX_THREAD_COUNT:
            # threads at capacity, so refuse connection
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                # if socket is closed or not connected, ignore
                pass
            try:
                conn.close()
            except OSError:
                pass
            logger.warning("Thread limit reached, connection refused")
            return

        # Thread creation.
        t = threading.Thread(target=thread_socket_main, args=(conn, addr))
        SOCKET_THREADS.append(t)

    # Start the thread outside of the lock
    logger.debug("Starting new thread for connection from %s", addr)
    t.start()
    # print the id of the started thread
    logger.debug(
        "Thread (id: %s) started. Active threads: %s", t.ident, len(SOCKET_THREADS)
    )
    return


def thread_socket_main(conn: socket.socket, addr):
    """Function is spun up for each active thread. Handles HTTP server send and receive.\n

    Args:
        conn (socket.socket): A newly accepted socket object
        addr: tuple that contains the clients ip and port number
    """
    logger.info(
        "Started thread (id: %s) handling connection from %s",
        threading.current_thread().ident,
        addr,
    )
    # Using try, finally block to ensure the thread is always removed
    # from SOCKET_THREADS exactly once on exit.
    try:
        with conn:
            # protect recv/send from blocking forever under load
            try:
                conn.settimeout(5.0)
            except OSError:
                # ignore if setting timeout fails for any reason
                pass

            request = b""
            while True:
                # Read request data until the end of headers
                while b"\r\n\r\n" not in request:
                    try:
                        data = conn.recv(1024)
                    except socket.timeout:
                        logger.debug(
                            "Receive timeout from %s, closing connection", addr
                        )
                        data = b""
                    except OSError as e:
                        logger.debug("Recv failed for %s: %s", addr, e)
                        data = b""

                    if not data:
                        break
                    request += data
                if not request:
                    break

                response = handle_request(request)
                try:
                    conn.sendall(response)
                except (
                    BrokenPipeError,
                    ConnectionResetError,
                    OSError,
                    socket.timeout,
                ) as e:
                    logger.debug("Send failed for %s: %s", addr, e)
                    break

                # If the application promised to close the connection, do so immediately
                # to avoid leaving the client or server waiting for the other side to close.
                try:
                    if b"connection: close" in response.lower():
                        logger.debug("Response asked to close connection for %s", addr)
                        break
                except TypeError:
                    # If response isn't bytes for some reason, ignore and continue
                    pass

                # prepare for possible pipelined/multiple requests on same connection
                request = b""
    finally:
        logger.debug("Thread for %s cleaning up and terminating", addr)
        with SOCKET_THREADS_LOCK:
            try:
                SOCKET_THREADS.remove(threading.current_thread())
            except ValueError:
                logger.warning(
                    "Error attempting to remove socket thread: thread not found in active thread list"
                )
        # with conn: context manager has closed the socket
        # with conn: context manager closes the socket

    # print the id of the terminated thread
    logger.info(
        "Terminated thread (id: %s). Number of active threads: %s",
        threading.current_thread().ident,
        len(SOCKET_THREADS),
    )
    return
