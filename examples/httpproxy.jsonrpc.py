#!/usr/bin/env python3
import os
import socket
import threading
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
        data = os.read(fd, 1024)
        _notify("want", [base64.b64encode(data).decode(), fd])


def _tryclose(fd: int):
    try:
        os.close(fd)
    except OSError:
        pass


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
    # to catch zombie processes
    threading.Thread(target=lambda: os.waitpid(p.pid, 0)).start()
    threading.Thread(target=lambda: _tryclose(fd)).start()
    return p.pid
