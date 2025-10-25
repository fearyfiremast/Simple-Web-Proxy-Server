# Simple HTTP Server
import mimetypes
import os
import socket
import threading

HOST = "127.0.0.1"
PORT = 3000
SOCKET_THREADS = []
MAX_THREAD_COUNT = 1
MAX_LISTEN_QUEUE_SIZE = 0

# REQUEST HANDLING
class Status:
    """Class representing an HTTP status code and its associated text."""

    def __init__(self, code, text):
        self.code = code
        self.text = text

#TODO: Consider creating a custom thread class
#TODO: properly lock shared resources (SOCKET_THREADS)
def initialize_socket_thread(conn : socket.socket, addr):
    """
    Function is repsonsible for dispatching threads. If the number of active threads is less than 
    MAX_THREAD_COUNT then the thread is added to an array started.
    Otherwise the socket is closed and no thread is created.\n

    Args:
        conn (socket.socket): A newly accepted socket object
        addr: tuple that contains the clients ip and port number
    """
    print("server")
    if len(SOCKET_THREADS) >= MAX_THREAD_COUNT:
        with conn:
            # threads at capacity
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
            print("Thread limit reached")
            return
        
    # Thread creation.
    t=threading.Thread(target=thread_socket_main, args=(conn,addr))
    SOCKET_THREADS.append(t)
    t.start()
    print(f"number of active threads: {len(SOCKET_THREADS)}", flush=True)
    return

#TODO: properly lock shared materials
def thread_socket_main(conn : socket.socket, addr):
    """Function is spun up for each active thread. Handles HTTP server send and receive.\n

    Args:
        conn (socket.socket): A newly accepted socket object
        addr: tuple that contains the clients ip and port number
    """
    print(f"Connected by {addr}", flush=True)
    with conn:
        while True:
            #TODO: Issue may arise if 0 packets arrive but data is still in transit. Length header?
            data = conn.recv(1024)
            if not data:
                break
            response = handle_request(data)
            conn.sendall(response)

        # thread termination process. Occurs after break
        SOCKET_THREADS.remove(threading.current_thread())
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()

    print(f"number of active threads: {len(SOCKET_THREADS)}", flush=True)
    return


def create_response(body, status, content_type="text/plain; charset=utf-8"):
    """Create an HTTP response message.

    Args:
        body (str or bytes): The body of the HTTP response.
        status (Status): The Status object containing the HTTP status code and text.
        content_type (str, optional): The mimetype of the body content.
                                      Defaults to 'text/plain; charset=utf-8'.

    Returns:
        bytes: A UTF-8 encoded HTTP response message.
    """
    # Content-Length is the number of bytes
    if isinstance(body, str):
        body = body.encode("utf-8")
    content_length = len(body)
    response_line = f"HTTP/1.1 {status.code} {status.text}\r\n"
    headers = (
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {content_length}\r\n"
        "Connection: close\r\n"
    )
    # Build headers as bytes and concatenate with body bytes
    header_bytes = (response_line + headers + "\r\n").encode("utf-8")
    return header_bytes + body


def handle_request(request):
    """Parse the HTTP request and generate the appropriate response.

    Args:
        request (bytes): The UTF-8 encoded HTTP request message.

    Returns:
        bytes: The UTF-8 encoded HTTP response message.
    """
    request = request.decode("utf-8")  # Decode bytes to string
    lines = request.split("\r\n")  # Split request into lines
    if len(lines) > 0:
        request_line = lines[0]
        print(f"Request Line: {request_line}")
        parts = request_line.split()
        if len(parts) >= 2:
            method = parts[0]
            path = parts[1]
            if method == "GET":  # Currently only handling GET requests
                filepath = path.lstrip("/")
                if os.path.isfile(filepath):
                    with open(filepath, "rb") as file:
                        body = file.read()
                        mimetype = (
                            mimetypes.guess_type(filepath)[0]
                            or "application/octet-stream"
                        )
                        status = Status(200, "OK")
                        return create_response(body, status, mimetype)
                else:
                    body = "File Not Found"
                    status = Status(404, "Not Found")
                    return create_response(body, status)

    body = "Bad Request"
    status = Status(400, "Bad Request")
    return create_response(body, status)

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
            print(type(conn)) 
            initialize_socket_thread(conn, addr)

# Entry point
if __name__ == "__main__":
    start_server()
