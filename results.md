# Test Results

## 200 OK Response

### Command:

`curl -i http://127.0.0.1:8080/test.html`


### Headers:

```http
Date: Mon, 27 Oct 2025 01:08:06 GMT
Server: Smith-Peters-Web-Server/1.0
Content-Type: text/html
Content-Length: 308
Last-Modified: Mon, 20 Oct 2025 19:08:33 GMT
Connection: close
```

### Body:

```html
<!DOCTYPE html>
<html>

<head>
  <meta charset="utf-8">
  <title></title>
  <meta name="author" content="">
  <meta name="description" content="">
  <meta name="viewport" content="width=device-width, initial-scale=1">

</head>

<body>

  <p>Congratulations! Your Web Server is Working!</p>

</body>

</html>
```

## 304 Not Modified Response

### Command:

`curl -i -H 'If-Modified-Since: Mon, 20 Oct 2025 19:08:33 GMT' http://127.0.0.1:8080/test.html`


### Headers:

```http
Date: Mon, 27 Oct 2025 01:08:06 GMT
Server: Smith-Peters-Web-Server/1.0
Content-Length: 0
Connection: close
```

## 403 Forbidden Response: Locked File

### Command:

`curl -i http://127.0.0.1:8080/locked.html`


### Headers:

```http
Date: Mon, 27 Oct 2025 01:08:06 GMT
Server: Smith-Peters-Web-Server/1.0
Content-Type: text/plain; charset=utf-8
Content-Length: 29
Connection: close
```

### Body:

```text
403 Forbidden: Access Denied
```

## 404 Not Found Response

### Command:

`curl -i http://127.0.0.1:8080/no_such_file.html`


### Headers:

```http
Date: Mon, 27 Oct 2025 01:08:06 GMT
Server: Smith-Peters-Web-Server/1.0
Content-Type: text/plain; charset=utf-8
Content-Length: 15
Connection: close
```

### Body:

```bash
File Not Found
```

## 505 Version Not Supported Response

### Command:

`curl -i --http1.0 http://127.0.0.1:8080/test.html`


### Headers:

```http
Date: Mon, 27 Oct 2025 01:08:06 GMT
Server: Smith-Peters-Web-Server/1.0
Content-Type: text/plain; charset=utf-8
Content-Length: 27
Connection: close
```

### Body:

```bash
HTTP Version Not Supported
```

