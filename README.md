# Simple HTTP Server

This server responds to HTTP `GET` requests, and includes an internal cache as well as multi-threading capabilities to handle requests in parallel.

## Instructions to run

1. Start the HTTP server by navigating to the project directory and running the following Python command into the terminal, optionally specifying a port to use (default is `8080`):

```bash
> cd /path/to/project/directory
> python3 http_server.py <port, optional>
"[2025-10-29 16:45:14,186] [INFO] [MainThread] Server is listening for request on 127.0.0.1:8080"
```
You should see that the server is now listening for requests at the correct address and port.

2. Request test page using one of the following methods:
- `curl -v http://127.0.0.1:8080/test.html`
- Open http://127.0.0.1:8080/test.html in your browser
- Telnet

3. Run automated unit tests with the following command:

```bash
> python3 http_server_test.py
```

This will generate `results.md` - the contents of which are included in our report (`report.pdf`).
