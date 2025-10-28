"""A module to manage threading and connection dispatch for the HTTP server.

Implements a bounded queue of accepted connections and a fixed-size pool of
worker threads to process them. This allows the server to absorb short bursts
without spawning unbounded threads and to return a graceful 503 when the
queue is full.
"""

import logging
import socket
import threading
from queue import Queue, Full, Empty

# Project imports
from message_utils import handle_request, create_503_response

# Configuration
MAX_THREAD_COUNT = 1  # Number of worker threads
BACKLOG_QUEUE_SIZE = 256  # Max queued accepted connections

# Connection queue and worker management
CONNECTION_QUEUE = Queue(maxsize=BACKLOG_QUEUE_SIZE)
WORKER_THREADS = []
WORKER_STOP_EVENT = threading.Event()

CONNECTION_TIMEOUT = None  # seconds


logger = logging.getLogger(__name__)


def start_worker_pool():
    """Start the fixed-size worker thread pool."""
    if WORKER_THREADS:
        return  # already started
    for i in range(MAX_THREAD_COUNT):
        t = threading.Thread(target=_worker_main, name=f"worker-{i+1}", daemon=True)
        WORKER_THREADS.append(t)
        t.start()
    logger.info("Started %d worker threads", len(WORKER_THREADS))


def stop_worker_pool():
    """Signal workers to stop and wait for them to exit."""
    WORKER_STOP_EVENT.set()
    # Unblock all workers by pushing sentinels
    for _ in WORKER_THREADS:
        try:
            CONNECTION_QUEUE.put_nowait(None)  # type: ignore[arg-type]
        except Full:
            # If full, workers will drain and exit; best-effort wakeup below
            break
    for t in WORKER_THREADS:
        t.join(timeout=1.0)
    WORKER_THREADS.clear()
    logger.info("Worker pool stopped")


def initialize_socket_thread(conn: socket.socket, addr):
    """Enqueue a newly accepted connection for processing by the worker pool.

    If the queue is full, reply with a 503 Service Unavailable gracefully and
    close the connection to avoid resets on the client side.
    """
    try:
        CONNECTION_QUEUE.put_nowait((conn, addr))
        logger.debug(
            "Enqueued connection from %s (queue size=%d)",
            addr,
            CONNECTION_QUEUE.qsize(),
        )
    except Full:
        # Queue is full, send a graceful 503
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
            # Drain briefly then close
            try:
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
            logger.warning("Connection queue full, responded 503 Service Unavailable")


def thread_socket_main(conn: socket.socket, addr, cache: Cache):
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

                response = handle_request(request, cache)
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

                # could eventually support pipelined/multiple requests on same connection
                request = b""
    finally:
        logger.debug("Connection handler for %s completed", addr)


def _worker_main():
    """Worker thread that pulls connections from the queue and handles them."""
    while not WORKER_STOP_EVENT.is_set():
        try:
            item = CONNECTION_QUEUE.get(timeout=0.5)
        except Empty:
            continue
        if item is None:
            CONNECTION_QUEUE.task_done()
            break
        conn, addr = item
        try:
            thread_socket_main(conn, addr)
        finally:
            CONNECTION_QUEUE.task_done()
