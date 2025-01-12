#!/usr/bin/env python3
import os
import socket
import threading
import sys
import base64
import subprocess
import socket


def thread_listen(host: str, port: int, _stopit: threading.Event, _notify):
    serverSocket = socket.socket()
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind((host, port))
    serverSocket.listen()
    serverSocket.settimeout(10.0)
    while not _stopit.is_set():
        try:
            clientConnection, _ = serverSocket.accept()
        except socket.timeout:
            continue
        fd = clientConnection.detach()
        data = os.read(fd, 1024).decode()
        if data.startswith("CONNECT ") and data.endswith("\r\n\r\n"):
            verb, hostport, _ = data.split(" ", 2)
            hostport = hostport.removeprefix("http://")
            hostport = hostport.removeprefix("https://")
            hostport = hostport.removesuffix("/")
            clienthost, clientport = hostport.split(":", 1)
            _notify(
                "wantproxy",
                [clienthost, int(clientport), fd, host, port],
            )
        elif data.startswith("GET ") and data.endswith("\r\n\r\n"):
            _notify(
                "wanthttp",
                [base64.b64encode(data.encode()).decode(), fd, host, port],
            )
        elif data.startswith("HEAD ") and data.endswith("\r\n\r\n"):
            _notify(
                "wanthttp",
                [base64.b64encode(data.encode()).decode(), fd, host, port],
            )
        elif data.startswith("POST ") and "\r\n\r\n" in data:
            _notify(
                "wanthttp",
                [base64.b64encode(data.encode()).decode(), fd, host, port],
            )
        else:
            _tryclose(fd)


def _tryclose(fd: int, pid=None):
    # if pid:
    #     os.waitpid(pid, 0)
    try:
        os.close(fd)
    except Exception as err:
        pass
    # try:
    #     socket.socket(fileno=fd).close()
    # except Exception as err:
    #     pass


def accept(fd: int, args: list[str]):
    os.write(fd, b"HTTP/1.0 200 OK\r\n\r\n")
    p = subprocess.Popen(
        args,
        stdin=fd,
        stdout=fd,
        stderr=subprocess.DEVNULL,
    )
    # to catch zombie processes
    threading.Thread(target=lambda: os.waitpid(p.pid, 0)).start()
    threading.Thread(target=lambda: _tryclose(fd)).start()
    return p.pid


def deny(fd: int):
    os.write(fd, b"HTTP/1.0 403 Denied\r\n\r\n")
    _tryclose(fd)


def accept_http(fd: int, args: list[str], init_data: str):
    init_data2 = base64.b64decode(init_data.encode())
    p = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=fd,
        stderr=subprocess.DEVNULL,
    )
    assert p.stdin
    p.stdin.write(init_data2)
    p.stdin.flush()
    p.stdin.close()
    print("waitpid", p.pid, file=sys.stderr)
    # to catch zombie processes
    threading.Thread(target=lambda: os.waitpid(p.pid, 0)).start()
    threading.Thread(target=lambda: _tryclose(fd)).start()
    return p.pid
