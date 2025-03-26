from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app import app
from queue import Queue

import time

stored_paths = {}
created_functions = {}


@app.middleware("https")
async def try_rate_limit(request, call_next):
    path = request.url.path
    rejected_response = JSONResponse(
        content={"response": "rejected"}, status_code=429)

    if path not in stored_paths or not path in created_functions:
        return rejected_response

    ip = request.client.host if request.client else "Nonexisting"
    address_info = stored_paths[path]["addresses"]

    if ip not in address_info:
        stored_paths[path]["addresses"][ip] = Queue()

    if address_info[ip].qsize() >= created_functions[path]["rate_limit"] and time.time() - address_info[ip].queue[0] < 10:
        return rejected_response

    if address_info[ip].qsize() == created_functions[path]["rate_limit"]:
        address_info[ip].get()

    address_info[ip].put(time.time())

    return await call_next(request)


def createEndPoint(path, methods, rate_limit, accept_function):
    if path in stored_paths or path in created_functions:
        # TODO: Add error.
        print("path already exists")
        return

    stored_paths[path] = {"addresses": {}}

    created_functions[path] = {
        "rate_limit": rate_limit, "accept_function": accept_function}

    app.add_api_route(path, accept_function, methods=methods)
