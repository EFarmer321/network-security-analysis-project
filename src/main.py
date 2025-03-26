import uvicorn
from fastapi import FastAPI, Request
from rate_limiter import createEndPoint
from app import app
from fastapi.responses import JSONResponse


async def testFunction():
    return JSONResponse(content={"response": "i see you"}, status_code=200)

createEndPoint("/test", ["GET"], 10, testFunction)
createEndPoint("/foo", ["GET", "SET"], 30, testFunction)
createEndPoint("/bar", ["GET", "SET"], 90, testFunction)
createEndPoint("/baz", ["GET", "SET"], 90, testFunction)

uvicorn.run(app, host="127.0.0.1", port=10000)
