"""A module to manage threading for the HTTP server."""

import logging
import socket
import threading

# Project imports
from message_utils import handle_request, create_503_response

MAX_THREAD_COUNT = 16
SOCKET_THREADS = []
SOCKET_THREADS_LOCK = threading.Lock()

CONNECTION_TIMEOUT = None  # seconds


logger = logging.getLogger(__name__)


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
            # Threads at capacity, send a 503 response
            try:
                response = create_503_response()
                try:
                    conn.sendall(response)
                except (BrokenPipeError, ConnectionResetError, OSError, socket.timeout):
                    pass
                try:
                    conn.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                try:
                    # Drain any remaining client data, then close
                    conn.settimeout(0.2)
                    while True:
                        try:
                            if not conn.recv(1024):
                                break
                        except socket.timeout:
                            break
                        except OSError:
                            break
                finally:
                    try:
                        conn.close()
                    except OSError:
                        pass
            finally:
                logger.warning(
                    "Thread limit reached, responded 503 Service Unavailable"
                )
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
                conn.settimeout(CONNECTION_TIMEOUT)
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
                    should_close = b"connection: close" in response.lower()
                except TypeError:
                    should_close = True

                if should_close:
                    logger.debug("Response asked to close connection for %s", addr)
                    # Perform a graceful half-close to avoid RST on clients like ab
                    try:
                        conn.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass

                    # Drain any remaining client data, then close
                    conn.settimeout(0.2)
                    while True:
                        try:
                            if not conn.recv(1024):
                                break
                        except socket.timeout:
                            break
                        except OSError:
                            break
                    break

                # could eventually support possible pipelined/multiple requests on same connection
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

    # print the id of the terminated thread
    logger.info(
        "Terminated thread (id: %s). Number of active threads: %s",
        threading.current_thread().ident,
        len(SOCKET_THREADS),
    )
    return
