"""A module for handling HTTP message creation and parsing."""

from email.utils import formatdate, parsedate_to_datetime
import mimetypes
import os
from os.path import getmtime
from time import time
import logging


# Serve files relative to the repository/module directory (document root)
DOCUMENT_ROOT = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger(__name__)


class Status:
    """Class representing an HTTP status code and its associated text."""

    def __init__(self, code, text):
        self.code = code
        self.text = text


def is_accessable_file(filepath):
    """Check if a file exists and is accessible.

    Args:
        filepath (str): The path to the file.

    Returns:
        bool: True if the file exists and is accessible, False otherwise.
    """
    # Only allow files inside the document root
    try:
        abs_path = os.path.abspath(filepath)
    except Exception:
        return False

    if not abs_path.startswith(DOCUMENT_ROOT):
        return False

    return os.path.isfile(abs_path) and os.access(abs_path, os.R_OK)


def get_date_header():
    """Generate a Date header for HTTP response.

    Returns:
        str: The Date header string.
    """
    return formatdate(timeval=time(), localtime=False, usegmt=True)


def is_not_modified_since(filepath, ims_header):
    """Check if the file has been modified since the time specified in the If-Modified-Since header.

    Args:
        filepath (str): The path to the file.
        ims_header (str): The value of the If-Modified-Since header.

    Returns:
        bool: True if the file has been modified since the specified time, False otherwise.
    """
    try:
        ims_time = parsedate_to_datetime(ims_header).timestamp()
        file_mtime = getmtime(filepath)
        return file_mtime <= ims_time
    except (TypeError, ValueError):
        return True  # If parsing fails, assume modified


def get_last_modified_header(filepath):
    """Generate a Last-Modified header for a given file.

    Args:
        filepath (str): The path to the file.

    Returns:
        str: The Last-Modified header string.
    """
    last_modified_time = getmtime(filepath)
    return formatdate(timeval=last_modified_time, localtime=False, usegmt=True)


def create_200_response(filepath):
    """Create an HTTP response message.

    Args:
        filepath (str): The path to the file to be served.

    Returns:
        bytes: A UTF-8 encoded HTTP response message.
    """
    # Read file content (filepath should be absolute)
    with open(filepath, "rb") as file:
        body = file.read()
    if isinstance(body, str):
        body = body.encode("utf-8")

    # Create response
    status = Status(200, "OK")
    content_type = mimetypes.guess_type(filepath)[0] or "text/plain; charset=utf-8"

    response_line = f"HTTP/1.1 {status.code} {status.text}\r\n"
    headers = (
        f"Date: {get_date_header()}\r\n"
        "Server: Smith-Peters-Web-Server/1.0\r\n"
        f"Content-Type: {content_type}\r\n"  # Content-Length is the number of bytes
        f"Content-Length: {len(body)}\r\n"
        f"Last-Modified: {get_last_modified_header(filepath)}\r\n"
        "Connection: close\r\n"
    )
    # Build headers as bytes and concatenate with body bytes
    header_bytes = (response_line + headers + "\r\n").encode("utf-8")
    return header_bytes + body


def create_304_response():
    """Create a 304 Not Modified HTTP response message.

    Returns:
        bytes: A UTF-8 encoded HTTP response message.
    """
    response_line = "HTTP/1.1 304 Not Modified\r\n"
    headers = (
        f"Date: {get_date_header()}\r\n"
        "Server: Smith-Peters-Web-Server/1.0\r\n"
        f"Content-Length: 0\r\n"
        "Connection: close\r\n"
    )
    header_bytes = (response_line + headers + "\r\n").encode("utf-8")
    return header_bytes


def create_503_response():
    """Create a 503 Service Unavailable HTTP response message.

    Returns:
        bytes: A UTF-8 encoded HTTP response message.
    """
    body = "Service Unavailable\n".encode("utf-8")
    response_line = "HTTP/1.1 503 Service Unavailable\r\n"
    headers = (
        f"Date: {get_date_header()}\r\n"
        "Server: Smith-Peters-Web-Server/1.0\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
    )
    header_bytes = (response_line + headers + "\r\n").encode("utf-8")
    return header_bytes + body


def create_404_response():
    """Create a 404 Not Found HTTP response message.

    Returns:
        bytes: A UTF-8 encoded HTTP response message.
    """
    body = "File Not Found\n"

    if isinstance(body, str):
        body = body.encode("utf-8")
    response_line = "HTTP/1.1 404 Not Found\r\n"
    headers = (
        f"Date: {get_date_header()}\r\n"
        "Server: Smith-Peters-Web-Server/1.0\r\n"
        f"Content-Type: text/plain; charset=UTF-8\r\n"  # Content-Length is the number of bytes
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
    )
    header_bytes = (response_line + headers + "\r\n").encode("utf-8")
    return header_bytes + body


def create_response(body, status):
    """Create a generic HTTP response message.

    Args:
        body (str or bytes): The body of the HTTP response.
        status (Status): The Status object containing the HTTP status code and text.

    Returns:
        bytes: A UTF-8 encoded HTTP response message.
    """
    if isinstance(body, str):
        body = body.encode("utf-8")
    content_length = len(body)
    response_line = f"HTTP/1.1 {status.code} {status.text}\r\n"
    headers = (
        f"Date: {get_date_header()}\r\n"
        "Server: Smith-Peters-Web-Server/1.0\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {content_length}\r\n"
        "Connection: close\r\n"
    )
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

    # print(f"Full Request:\n{request}", flush=True)

    lines = request.split("\r\n")  # Split request into lines
    request = lines[0]  # First line is the request line
    method, path, version = request.split()

    headers = {}
    for line in lines[1:]:
        if line == "":
            break
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()  # Store header in a dictionary

    if version not in ["HTTP/1.0", "HTTP/1.1"]:
        body = "HTTP Version Not Supported\n"
        status = Status(505, "HTTP Version Not Supported")
        return create_response(body, status)

    # Resolve path within DOCUMENT_ROOT to prevent directory traversal
    path = os.path.join(DOCUMENT_ROOT, path.lstrip("/"))
    # print(f"Requested Path: {path}", flush=True)

    # 404: File does not exist
    if not os.path.exists(path):
        body = "File Not Found\n"
        status = Status(404, "Not Found")
        return create_response(body, status)

    # 403: File is not accessible (e.g., permission denied, outside root directory)
    if not is_accessable_file(path):
        body = "403 Forbidden: Access Denied\n"
        status = Status(403, "Forbidden")
        return create_response(body, status)

    # 304: Not Modified
    if "If-Modified-Since" in headers:
        # last_modified = parsedate_to_datetime(headers["If-Modified-Since"]).timestamp()

        # Send 304 if file has not been modified since the time specified
        # i.e. file last modified time is less than or equal to the time in the header
        if is_not_modified_since(path, headers["If-Modified-Since"]) is False:
            return create_304_response()

    if len(lines) > 0:
        parts = request.split()
        if len(parts) >= 2:
            if method == "GET":  # Currently only handling GET requests
                if os.path.isfile(path):
                    # 200 OK
                    return create_200_response(path)
                else:
                    body = "File Not Found\n"
                    status = Status(404, "Not Found")
                    return create_response(body, status)

    body = "Bad Request\n"
    status = Status(400, "Bad Request")
    return create_response(body, status)
