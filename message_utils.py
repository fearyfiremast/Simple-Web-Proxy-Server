"""A module for handling HTTP message creation and parsing."""

from time import sleep
import os
import logging

# Project imports
from cache_utils import Cache, Record
from header_utils import (
    get_date_header,
    is_not_modified_since,
    convert_reqheader_into_dict,
)

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


# response package (content, content_type, last_modified)
def create_200_response(response: Record):
    """Create an HTTP response message.

    Args:
        filepath (str): The path to the file to be served.

    Returns:
        bytes: A UTF-8 encoded HTTP response message.
    """
    # Create response
    status = Status(200, "OK")
    body = (
        response.get_content()
    )  # pre encoded to UTF-8 by acquire_resources in header_util
    response_line = f"HTTP/1.1 {status.code} {status.text}\r\n"
    headers = (
        f"Date: {get_date_header()}\r\n"
        "Server: Smith-Peters-Web-Server/1.0\r\n"
        f"Content-Type: {response.get_content_type()}\r\n"  # Content-Length is the number of bytes
        f"Content-Length: {len(body)}\r\n"
        "Cache-Control: 'max-age=3600'\r\n"
        f"ETag: '{response.get_etag()}'\r\n"
        f"Last-Modified: {response.get_last_modified()}\r\n"
        f"Vary: {response.get_vary()}\r\n"
        "Connection: close\r\n"
    )
    # print(f"################### ETag\n {response.get_etag()}", flush=True)
    # Build headers as bytes and concatenate with body bytes
    header_bytes = (response_line + headers + "\r\n").encode("utf-8")
    return header_bytes + body


def create_304_response(response: Record):
    """Create a 304 Not Modified HTTP response message.

    Returns:
        bytes: A UTF-8 encoded HTTP response message.

    """
    response_line = "HTTP/1.1 304 Not Modified\r\n"
    headers = (
        f"Date: {get_date_header()}\r\n"
        "Server: Smith-Peters-Web-Server/1.0\r\n"
        f"Content-Length: 0\r\n"
        "Cache-Control: 'max-age=3600'\r\n"
        f"ETag: '{response.get_etag()}'\r\n"
        f"Last-Modified: {response.get_last_modified()}\r\n"
        f"Vary: {response.get_vary()}\r\n"
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


# TODO: Allow the passing in of header arguments as an iteratable object
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


def request_well_formed(method, version):
    """
    Checks the request header for the correct version and if it calling a supported method by
    the proxy server.

    Args:
        method (str): The method contained within the request
        version (str): The version of the http request (formated as "HTTP/x.x")

    Returns:
        If either the requests method is unsupported returns a code 400 response.
        If the request method has a supported method but an unsupported version of HTTP
        returns a 505 response

        otherwise, returns None.
    """
    supported_methods = ["GET"]  # Methods supported by the proxy server
    supported_versions = ["HTTP/1.0", "HTTP/1.1"]

    if method not in supported_methods:
        body = "Method Not Allowed\n"
        status = Status(405, "Method Not Allowed")
        return create_response(body, status)

    if version not in supported_versions:
        body = "HTTP Version Not Supported\n"
        status = Status(505, "HTTP Version Not Supported")
        return create_response(body, status)

    return None


def valid_webserver_response(url):
    """ """

    # print(f"Requested Path: {path}", flush=True)

    # 404: File does not exist
    if not os.path.exists(url):
        body = "File Not Found\n"
        status = Status(404, "Not Found")
        return create_response(body, status)

    # 403: File is not accessible (e.g., permission denied, outside root directory)
    if not is_accessable_file(url):
        body = "403 Forbidden: Access Denied\n"
        status = Status(403, "Forbidden")
        return create_response(body, status)

    return None


def handle_request(request, cache: Cache):
    """Parse the HTTP request and generate the appropriate response.

    Args:
        request (bytes): The UTF-8 encoded HTTP request message.

    Returns:
        bytes: The UTF-8 encoded HTTP response message.
    """

    # simulate processing delay

    request = request.decode("utf-8")  # Decode bytes to string

    # print(f"Full Request:\n{request}", flush=True)

    lines = request.split("\r\n")  # Split request into lines
    request_line = lines[0]  # First line is the request line
    method, path, version = request_line.split()

    # Store header in a dictionary
    headers = convert_reqheader_into_dict(lines[1:])

    # Returns a response if request is NOT well formed
    if (to_return := request_well_formed(method, version)) is not None:
        return to_return

    # Resolve absolute path within DOCUMENT_ROOT
    abs_path = os.path.join(DOCUMENT_ROOT, path.lstrip("/"))

    # Build cache lookup key: request identity + headers (for Vary semantics)
    cache_key = {
        "method": method,
        "url": abs_path,
        "version": version,
        "headers": headers,
    }

    # print(f"Cache Key: {cache_key}", flush=True)
    # print("Cache Contents Before Lookup:", flush=True)
    # cache.print_cache()

    # Check if cache has a fresh matching representation
    if (found_request := cache.find_record(cache_key)) is not None:
        # Validators: If-None-Match and If-Modified-Since
        inm = headers.get("If-None-Match")
        ims = headers.get("If-Modified-Since")

        # Strong/weak ETag handling not implemented; do a simple string compare after stripping quotes
        if inm is not None:
            etag_clean = inm.strip().strip("'\"")
            if etag_clean == str(found_request.get_etag()):
                return create_304_response(found_request)

        if ims is not None and is_not_modified_since(abs_path, ims):
            return create_304_response(found_request)

        # No validators or validators indicate resource changed -> serve 200 from cache
        return create_200_response(found_request)

    # Not in cache
    # Validate path and accessibility at server
    if (error_at_srv := valid_webserver_response(abs_path)) is not None:
        return error_at_srv

    # TODO: extract into helper function
    if len(lines) > 0:
        parts = request_line.split()
        if len(parts) >= 2:
            if method == "GET":  # Currently only handling GET requests
                if os.path.isfile(abs_path):

                    logger.warning("Cache miss for %s", path)

                    sleep(2.0)  # Simulate processing delay

                    # create record for the representation
                    to_insert = Record(
                        abs_path, method=method, version=version, req_headers=headers
                    )

                    # Send 304 only if client provided If-Modified-Since and
                    # the file has not been modified since that time
                    ims = headers.get("If-Modified-Since")
                    if ims is not None and is_not_modified_since(abs_path, ims):
                        return create_304_response(to_insert)

                    # 200 OK
                    # must create the response before inserting it into cache as after insertion
                    # it may be touched by other threads during response creation (if shallow copy)
                    to_send = create_200_response(to_insert)
                    cache.insert_response(to_insert)
                    return to_send

                else:
                    body = "File Not Found\n"
                    status = Status(404, "Not Found")
                    return create_response(body, status)

    body = "Bad Request\n"
    status = Status(400, "Bad Request")
    return create_response(body, status)
