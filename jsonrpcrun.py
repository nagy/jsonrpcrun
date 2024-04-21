#!/usr/bin/env python3
import sys
import os
import importlib
import importlib.util
import json
import threading

funcs = {}

stop_events = {}


def handle_request(*, jsonrpc: str, method: str, params, id: int):
    assert jsonrpc == "2.0"
    assert int(id)
    if method.startswith("_"):
        raise RuntimeError("private method")
    if not method in funcs and method != "stop_thread":
        raise RuntimeError("not method in globals")
    if method != "stop_thread" and not callable(funcs[method]):
        raise RuntimeError("not callable")
    if method == "stop_thread":
        stopid = params["stopid"]
        if stopid in stop_events:
            stop_events[stopid].set()
            del stop_events[stopid]
            return True
        else:
            return
    if method.startswith("thread_"):
        evt = threading.Event()
        thread = threading.Thread(
            target=funcs[method],
            kwargs=(params or {})
            | {
                "_stopit": evt,
                "_notify": lambda method, params: writejson(
                    {"method": method, "params": params}
                ),
            },
            daemon=True,
        )
        thread.start()
        stop_events[thread.native_id] = evt
        return thread.native_id
    else:
        return funcs[method](**(params or {}))


def writejson(obj: dict):
    byt = json.dumps({"jsonrpc": "2.0"} | obj)
    out = f"Content-Length: {len(byt)}\r\n\r\n{byt}".encode()
    sys.stdout.buffer.write(out)
    sys.stdout.buffer.flush()


def readjsons(stream):
    bfr = b""
    while data := stream.read(1):
        bfr += data
        if b"\r\n\r\n" not in bfr:
            continue
        ln = int(bfr.removeprefix(b"Content-Length:").strip())
        bfr = b""
        thedata = stream.read(ln).decode()
        jso = json.loads(thedata)
        assert jso["jsonrpc"] == "2.0"
        yield jso


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        raise ValueError("no module provided")
    for arg in sys.argv[1:]:
        spec = importlib.util.spec_from_file_location("module", arg)
        assert spec
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        for attr in dir(mod):
            if callable(getattr(mod, attr)):
                funcs[attr] = getattr(mod, attr)

    if os.getenv("VERBOSE") == "json":
        print(json.dumps([key for key in funcs], indent=2))
        sys.exit(1)
    else:
        for jso in readjsons(sys.stdin.buffer):
            try:
                ret = {"id": jso["id"], "result": handle_request(**jso)}
            except Exception as err:
                ret = {"id": jso["id"], "error": {"code": 123, "message": str(err)}}
            writejson(ret)
