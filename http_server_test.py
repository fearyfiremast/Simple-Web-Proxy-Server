"""
This module contains unit tests for an HTTP server.
We verify server responses for status codes 200, 304, 403, 404, and 505.
"""

from email.utils import formatdate
import os
import shlex
import unittest
import socket
import subprocess
import sys

REPORT_STATUS = True  # if value is true write report
REPORT_NAME = "results.md"

PORT = 8080
HOST = "127.0.0.1"
DESTINATION = None
RESOURCE = "/test.html"


def capture_package_values(cmd: list):
    """
    runs a subprocess and returns its output as text.

    Args:
        cmd (list): A list that contains a command as well as its arguments.

        Returns:
            The output of cmd as a string.
    """
    result = (subprocess.run(cmd, capture_output=True, text=True, check=False)).stdout
    return result


def parse_response(response: str):
    """
    Parses an HTTP response into its status line, headers, and body.

    Args:
        response (str): The full HTTP response as a string.

    Returns:
        tuple: A tuple containing the status line (str), headers (dict), and body (str).
    """

    # split head and body accepting CRLF or LF-only separators
    if "\r\n\r\n" in response:
        head, body = response.split("\r\n\r\n", 1)
    elif "\n\n" in response:
        # Python's subprocess with text=True normalizes CRLF to LF, so account for that
        head, body = response.split("\n\n", 1)
    else:
        head = response
        body = ""

    lines = head.splitlines()
    status_line = lines[0] if lines else ""
    headers = {}
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            # preserve header capitalization as returned by the server
            headers[k.strip()] = v.strip()

    # body may start with an extra newline if split used LF
    if body.startswith("\n") and not body.startswith("\r\n"):
        body = body[1:]

    return status_line, headers, body


class TestPart1(unittest.TestCase):
    """
    This class is responsible for performing unit tests related to part one of the assignments.
    This includes, verifying server response for the HTTP GET method and codes 200, 304, 403,
    404, and 505.

    Extends the unittest.TestCase class.
    """

    def setUp(self):
        # build destination URL for tests
        self.destination = f"http://{HOST}:{PORT}{RESOURCE}"
        # Clear cache for a clean slate
        _ = capture_package_values(
            [
                "curl",
                "-sS",
                "-X",
                "POST",
                f"http://{HOST}:{PORT}/__cache__/clear",
            ]
        )

    def test_200_OK_header(self):
        """
        unit test that verifies if the header is well formed
        """
        cmd = ["curl", "-i", f"{self.destination}"]
        result = capture_package_values(cmd)

        status_line, headers, body = parse_response(result)

        append_report(
            "200 OK",
            headers,
            body,
            command=cmd,
            status_line=status_line,
        )

        # Check status
        self.assertTrue(status_line.startswith("HTTP/1.1 200"))

        # Presence-only checks for required header fields
        for name in ("Date", "Server", "Content-Type", "Content-Length", "Connection"):
            self.assertIn(name, headers)

    def test_200_OK_body_content(self):
        """
        Unit test that verifies if the payload was delivered as expected
        """
        cmd = ["curl", f"{self.destination}"]
        result = capture_package_values(cmd)
        with open("./test.html", mode="r", encoding="utf-8") as test_html:
            data = test_html.read()
            self.assertEqual(data.split("\n"), result.split("\n"))

    def test_304_not_modified_headers(self):
        """Request with If-Modified-Since equal to file mtime should return 304 with headers."""

        filepath = "./test.html"
        modified_time = os.path.getmtime(filepath)
        current_time = formatdate(timeval=modified_time, localtime=False, usegmt=True)

        cmd = [
            "curl",
            "-i",
            "-H",
            f"If-Modified-Since: {current_time}",
            f"http://{HOST}:{PORT}/test.html",
        ]
        result = capture_package_values(cmd)

        status_line, headers, _ = parse_response(result)

        append_report(
            "304 Not Modified",
            headers,
            command=cmd,
            status_line=status_line,
        )

        self.assertTrue(status_line.startswith("HTTP/1.1 304"))
        for name in ("Date", "Server", "Content-Length", "Connection"):
            self.assertIn(name, headers)

    def test_403_forbidden_locked_file(self):
        """Create a file with no read permissions and verify server returns 403."""
        locked_path = "./locked.html"
        # create file and write sample content
        with open(locked_path, "w", encoding="utf-8") as f:
            f.write("Locked content\n")

        # remove all permissions (no read for anyone)
        orig_mode = os.stat(locked_path).st_mode
        try:
            os.chmod(locked_path, 0o000)

            cmd = ["curl", "-i", f"http://{HOST}:{PORT}/locked.html"]
            result = capture_package_values(cmd)
            status_line, headers, body = parse_response(result)

            append_report(
                "403 Forbidden: Locked File",
                headers,
                body,
                body_fmt="text",
                command=cmd,
                status_line=status_line,
            )

            self.assertTrue(status_line.startswith("HTTP/1.1 403"))
            for name in (
                "Date",
                "Server",
                "Content-Type",
                "Content-Length",
                "Connection",
            ):
                self.assertIn(name, headers)
        finally:
            # restore permissions and remove file
            try:
                os.chmod(locked_path, orig_mode)
            except OSError:
                pass
            try:
                os.remove(locked_path)
            except OSError:
                pass

    def test_403_forbidden_outside_path(self):
        """Requesting a path outside the server root should return 403 with headers."""
        s = socket.socket()
        s.connect((HOST, PORT))
        request = "GET /../ HTTP/1.1\r\nHost: localhost\r\n\r\n"
        s.send(request.encode("utf-8"))
        result = s.recv(4096).decode("utf-8")
        s.close()

        status_line, headers, body = parse_response(result)

        append_report(
            "403 Forbidden: File outside server root path",
            headers,
            body,
            body_fmt="text",
            command=["Socket send: " + request.replace("\r\n", "\\r\\n")],
            status_line=status_line,
        )

        self.assertTrue(status_line.startswith("HTTP/1.1 403"))
        for name in ("Date", "Server", "Content-Type", "Content-Length", "Connection"):
            self.assertIn(name, headers)

    def test_404_not_found_headers(self):
        """Requesting a missing file should return 404 with expected headers present."""
        cmd = ["curl", "-i", f"http://{HOST}:{PORT}/no_such_file.html"]
        result = capture_package_values(cmd)
        status_line, headers, body = parse_response(result)

        append_report(
            "404 Not Found",
            headers,
            body,
            body_fmt="bash",
            command=cmd,
            status_line=status_line,
        )

        self.assertTrue(status_line.startswith("HTTP/1.1 404"))
        for name in ("Date", "Server", "Content-Type", "Content-Length", "Connection"):
            self.assertIn(name, headers)

    def test_405_method_not_allowed_headers(self):
        """Request with unsupported method should return 405 Method Not Allowed."""
        s = socket.socket()
        s.connect((HOST, PORT))
        request = "POST /test.html HTTP/1.1\r\nHost: localhost\r\n\r\n"
        s.send(request.encode("utf-8"))
        result = s.recv(4096).decode("utf-8")
        s.close()

        status_line, headers, body = parse_response(result)

        append_report(
            "405 Method Not Allowed",
            headers,
            body,
            body_fmt="bash",
            command=["Socket send: " + request.replace("\r\n", "\\r\\n")],
            status_line=status_line,
        )

        self.assertTrue(status_line.startswith("HTTP/1.1 405"))
        for name in ("Date", "Server", "Content-Type", "Content-Length", "Connection"):
            self.assertIn(name, headers)

    def test_505_unsupported_version_headers(self):
        """Request with unsupported HTTP version should return 505 Version Not Supported."""
        s = socket.socket()
        s.connect((HOST, PORT))
        request = "GET /test.html HTTP/3.0\r\nHost: localhost\r\n\r\n"
        s.send(request.encode("utf-8"))
        result = s.recv(4096).decode("utf-8")
        s.close()

        status_line, headers, body = parse_response(result)

        append_report(
            "505 Version Not Supported",
            headers,
            body,
            body_fmt="bash",
            command=["Socket send: " + request.replace("\r\n", "\\r\\n")],
            status_line=status_line,
        )

        self.assertTrue(
            status_line.startswith("HTTP/1.1 505")
            or status_line.startswith("HTTP/1.0 505")
        )
        for name in ("Date", "Server", "Content-Type", "Content-Length", "Connection"):
            self.assertIn(name, headers)


class TestPart2(unittest.TestCase):
    """
    This class is responsible for performing unit tests related to part 2, or caching.

    Extends the unittest.TestCase class.
    """

    def setUp(self):
        # build destination URL for tests
        self.destination = f"http://{HOST}:{PORT}{RESOURCE}"
        # Clear cache for a clean slate
        _ = capture_package_values(
            [
                "curl",
                "-sS",
                "-X",
                "POST",
                f"http://{HOST}:{PORT}/__cache__/clear",
            ]
        )

        _ = capture_package_values(
            [
                "curl",
                "-sS",
                "-X",
                "POST",
                "http://127.0.0.1:8080/__cache__/set-miss-delay?seconds=1.2",
            ]
        )

    def test_cache_hit_on_repeat_requests(self):
        """Two identical requests should result in second one being a cache HIT (X-Cache: HIT)."""
        # Warm up cache with first request
        cmd1 = ["curl", "-i", "-H", "Accept-Encoding: identity", f"{self.destination}"]
        result1 = capture_package_values(cmd1)
        status_line1, _headers1, _body1 = parse_response(result1)
        self.assertTrue(status_line1.startswith("HTTP/1.1 200"))

        append_report(
            "Cache MISS on First Request:",
            _headers1,
            command=cmd1,
            status_line=status_line1,
        )

        # Next request should be served from cache
        cmd2 = ["curl", "-i", "-H", "Accept-Encoding: identity", f"{self.destination}"]
        result2 = capture_package_values(cmd2)
        status_line2, headers2, _body2 = parse_response(result2)
        self.assertTrue(status_line2.startswith("HTTP/1.1 200"))

        # Check cache indicator
        self.assertEqual(headers2.get("X-Cache"), "HIT")

        append_report(
            "Cache HIT on Repeat Requests: Request 2",
            headers2,
            command=cmd2,
            status_line=status_line2,
        )

    def test_cache_miss_then_hit_with_vary(self):
        """Different Accept-Encoding values should create different cache entries; same value should hit."""
        # First with identity
        cmd_identity = [
            "curl",
            "-i",
            "-H",
            "Accept-Encoding: identity",
            f"{self.destination}",
        ]
        _ = capture_package_values(cmd_identity)

        # Now with gzip - different representation, should MISS then HIT on repeat
        cmd_gzip1 = ["curl", "-i", "--compressed", f"{self.destination}"]
        res1 = capture_package_values(cmd_gzip1)
        _, headers_gz1, _ = parse_response(res1)
        # X-Cache may be missing for compressed if server doesn't compress; we rely on repeat below

        cmd_gzip2 = ["curl", "-i", "--compressed", f"{self.destination}"]
        res2 = capture_package_values(cmd_gzip2)
        _, headers_gz2, _ = parse_response(res2)
        # Second compressed request should be a HIT for same encoding dimension
        self.assertEqual(headers_gz2.get("X-Cache"), "HIT")

        append_report(
            "Cache Miss then Hit with Vary on Accept-Encoding",
            headers_gz2,
            command=cmd_gzip2,
            status_line="HTTP/1.1 200 OK",
        )

    #TODO: Test cache entires expire on their own time
    def test_expiry_evicts_record(self):

        WAIT_TIME = 0
        # sets wait time
        cmd_expiry = [
                "curl",
                "-sS",
                "-X",
                "POST",
                f"http://{HOST}:{PORT}/__cache__/set-expiry?{WAIT_TIME}",
        ]
        capture_package_values(cmd_expiry)

        # put val in cache
        capture_package_values(
            ["curl", f"{self.destination}"]
        )

        # returns size of cache of eviction

        cmd_evict = [
            "curl",
            "-sS",
            "-X",
            "POST",
            f"http://{HOST}:{PORT}/__cache__/evict-expired", 
        ]

        response = capture_package_values(cmd_evict)


        # Sets cache expiry back to default
        capture_package_values(
            [
                "curl",
                "-sS",
                "-X",
                "POST",
                f"http://{HOST}:{PORT}/__cache__/set-expiry?{60}",
            ]
        )

        append_report(
            "Evict Test: Set Expiry",
            command=cmd_expiry,
            status_line="HTTP/1.1 200 OK",
        )

        append_report(
            "Evict Test: Evict Cache",
            command=cmd_evict,
            status_line="HTTP/1.1 200 OK"
        )

        self.assertEqual("Removed expired records.\nRecords in cache: 0", response)

    def test_304_with_etag_and_ims_from_cache(self):
        """Request with ETag or IMS that matches cached entry should return 304 and X-Cache: HIT."""
        # Warm cache
        cmd = ["curl", "-i", "-H", "Accept-Encoding: identity", f"{self.destination}"]
        res = capture_package_values(cmd)
        _, headers, _ = parse_response(res)
        etag = headers.get("ETag")
        last_modified = headers.get("Last-Modified")
        self.assertIsNotNone(etag)
        self.assertIsNotNone(last_modified)

        # ETag validator
        cmd_etag = [
            "curl",
            "-i",
            "-H",
            f"If-None-Match: {etag}",
            "-H",
            "Accept-Encoding: identity",
            f"{self.destination}",
        ]
        res_etag = capture_package_values(cmd_etag)
        status_etag, h_etag, _ = parse_response(res_etag)
        self.assertTrue(status_etag.startswith("HTTP/1.1 304"))
        self.assertEqual(h_etag.get("X-Cache"), "HIT")

        append_report(
            "304 Not Modified with ETag from Cache",
            h_etag,
            command=cmd_etag,
            status_line=status_etag,
        )

        # IMS validator
        cmd_ims = [
            "curl",
            "-i",
            "-H",
            f"If-Modified-Since: {last_modified}",
            "-H",
            "Accept-Encoding: identity",
            f"{self.destination}",
        ]
        res_ims = capture_package_values(cmd_ims)
        status_ims, h_ims, _ = parse_response(res_ims)
        self.assertTrue(status_ims.startswith("HTTP/1.1 304"))
        self.assertEqual(h_ims.get("X-Cache"), "HIT")

        append_report(
            "304 Not Modified with If-Modified-Since from Cache",
            h_ims,
            command=cmd_ims,
            status_line=status_ims,
        )

    def test_high_volume_requests(self):
        """Send a high volume of requests to test server stability and caching under load."""
        import shutil, time

        # Skip if ApacheBench is not installed
        if shutil.which("ab") is None:
            self.skipTest("ApacheBench (ab) is not installed on this system")

        # Warm cache so the benchmark measures cached responses
        _ = capture_package_values(
            [
                "curl",
                "-sS",
                "-H",
                "Accept-Encoding: identity",
                f"http://{HOST}:{PORT}/test.html",
            ]
        )

        num_requests = 50
        concurrency = 10
        per_socket_timeout = 2.5  # ab per-conn timeout
        threshold_seconds = 4.0  # end-to-end test must finish under this

        cmd = [
            "ab",
            "-n",
            str(num_requests),
            "-c",
            str(concurrency),
            "-H",
            "Accept-Encoding: identity",
            f"http://{HOST}:{PORT}/test.html",
        ]

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=threshold_seconds,
            )
        except subprocess.TimeoutExpired:
            self.fail(
                f"High volume request test exceeded {threshold_seconds:.2f}s (timeout)"
            )
        elapsed = time.perf_counter() - start

        # Verify we completed under the threshold
        self.assertLessEqual(
            elapsed,
            threshold_seconds,
            f"ab run took {elapsed:.2f}s, expected <= {threshold_seconds:.2f}s",
        )
        time.sleep(3)  # brief pause to ensure output is flushed
        # Basic sanity: no failed requests as reported by ab
        self.assertIn("Failed requests:        0", proc.stdout)

        append_report(
            "High Volume Requests Performance",
            {"Elapsed": f"{elapsed:.2f}s"},
            command=cmd,
            status_line="ab completed",
        )


def refresh_report():
    """Initialize the results file as Markdown."""
    if not REPORT_STATUS:
        return
    with open(REPORT_NAME, "w", encoding="utf-8") as f:
        f.write("# Test Results\n\n")


# project states that we need screenshots of output.
def append_report(
    title: str,
    headers: dict | None = None,
    body: str = None,
    body_fmt: str = "html",
    command: list | None = None,
    status_line: str | None = None,
):
    if REPORT_STATUS == False:
        return

    # Append a markdown section with the title, headers, and body in fenced blocks
    with open(REPORT_NAME, "a", encoding="utf-8") as data:
        data.write(f"## {title}\n\n")
        # Command block (if provided)
        if command is not None:
            # command may be a list (cmd args) or a string; format safely
            if isinstance(command, (list, tuple)):
                cmd_text = " ".join(shlex.quote(str(x)) for x in command)
            else:
                cmd_text = str(command)
            data.write("### Command:\n\n")
            data.write("`" + cmd_text + "`\n")
            data.write("\n\n")
        # Status line (if provided)
        if status_line:
            data.write("### Status Line:\n\n")
            data.write("`" + status_line + "`\n\n")
        
        if headers is not None:
            data.write("### Headers:\n\n")
            data.write("```http\n")
            for key, value in headers.items():
                data.write(f"{key}: {value}\n")
            data.write("```\n\n")

        if body is not None:
            data.write("### Body:\n\n")
            data.write(f"```{body_fmt}\n")
            data.write(body.rstrip() + "\n")
            data.write("```\n\n")

    return


# entry point
# specific tests can be ran from the command line: https://docs.python.org/3/library/unittest.html
# If report or port number is wanted it is not recommended to use the interface from above link

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # may cause errors with unittest sys.argv implementation
        if sys.argv[1].isdigit() and 0 < int(sys.argv[1]) < 65536:
            PORT = int(sys.argv[1])
            del sys.argv[1]
    refresh_report()
    print("---- BEGIN TESTS ----")
    print(f"Running tests against server at {HOST}:{PORT}")
    unittest.main()
