from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app import app
from database import get_connection
import math

stored_paths = {}
created_functions = {}

rejected_response = JSONResponse(
    content={"response": "rejected"}, status_code=429)

stored_paths = {}
created_functions = {}


def try_add_ip(ip):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO User
                (
                    IpAddress,
                    Reputation
                ) 
            VALUES 
                (
                    %s, 
                    0
                ) 
            ON DUPLICATE KEY UPDATE IpAddress = IpAddress;
            """,
            (ip,)
        )
        connection.commit()
    except:
        connection.rollback()
    finally:
        cursor.close()
        connection.close()


def try_update_limit_threshold(ip):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO RecordedLimitThresholds 
                (
                    IpAddress, 
                    RecordedAt
                ) 
            VALUES 
                (
                    %s, 
                    NOW()
                );
            """,
            (ip,)
        )
        connection.commit()
    except:
        connection.rollback()
    finally:
        cursor.close()
        connection.close()


@app.middleware("http")
async def try_rate_limit(request, call_next):
    path = request.url.path

    if path not in created_functions:
        return rejected_response

    ip = request.client.host or "None"

    reputation = 0
    try_add_ip(ip)

    can_lower_reputation = True
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM RecordedLimitThresholds
            WHERE IpAddress = %s AND RecordedAt > (NOW() - %s);
            """,
            (ip, created_functions[path]["duration"]),
        )
        count = cur.fetchone()[0]
    except Exception as e:
        print(e)
        conn.rollback()
        can_lower_reputation = False
        count = float("inf")
    finally:
        cur.close()
        conn.close()

    if count > created_functions[path]["rate_limit"]:

        if can_lower_reputation:
            conn = get_connection()
            cur = conn.cursor()

        return rejected_response

    return await call_next(request)


def createEndPoint(path, methods, rate_limit, accept_function, duration=60):
    if path in stored_paths or path in created_functions:
        # TODO: Add error.
        print("path already exists")
        return

    stored_paths[path] = {"addresses": {}}

    created_functions[path] = {
        "rate_limit": rate_limit, "accept_function": accept_function, "duration": duration}

    app.add_api_route(path, accept_function, methods=methods)
