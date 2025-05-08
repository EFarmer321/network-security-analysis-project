from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app import app
from database import get_connection
from collections.abc import Callable, Awaitable
from mysql.connector import errors
from datetime import datetime
from constants import *
from math import floor
from utils import lerp, clamp

stored_paths = {}
created_functions = {}

rejected_response = JSONResponse(
    content={"response": "rejected"}, status_code=429)

def get_rate_limit_from_reputation(reputation: int, min_rate_limit: int, max_rate_limit: int):
   return floor(lerp(min_rate_limit, max_rate_limit, reputation / MAX_REPUTATION))
    
def try_add_ip(ip: str):
    connection = get_connection()
    cursor = connection.cursor()
    success = True

    try:
        cursor.execute(
            """
            INSERT INTO Users
                (
                    IpAddress,
                    Reputation
                ) 
            VALUES 
                (
                    %s, 
                    5
                ) 
            ON DUPLICATE KEY UPDATE IpAddress = IpAddress;
            """,
            (ip,)
        )
        connection.commit()
    except errors.ProgrammingError as e:
        print(f"Caught exception: {e}")
        connection.rollback()
        success = False
    finally:
        cursor.close()
        connection.close()
        
    return success

def get_reputation(ip: str):
    connection = get_connection()
    cursor = connection.cursor()
    reputation = 0

    try:
        cursor.execute(
            """
            SELECT Reputation
            FROM Users
            WHERE IpAddress = %s;
            """,
            (ip,)
        )
        reputation = cursor.fetchone()[0]
    except errors.ProgrammingError as e:
        print(f"Caught exception: {e}")
        reputation = 0
        connection.rollback()
    finally:
        connection.close()
        cursor.close()

    if reputation == None:
        return 0
    else:
        return reputation

def set_reputation(ip: str, new_reputation: int):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE Users
            SET Reputation = %s
            WHERE IpAddress = %s
            """,
            (clamp(new_reputation, 0, MAX_REPUTATION), ip)
        )
        connection.commit()
    except errors.ProgrammingError as e:
        print(f"Caught exception: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

def try_add_endpoint(ip: str, path: str):
    connection = get_connection()
    cursor = connection.cursor()
    success = True

    try:
        cursor.execute(
            """
            INSERT INTO Endpoints (
                Endpoint,
                IpAddress,
                LastRequestTime
            )
            VALUES (
                %s,
                %s,
                NOW()
            )
            ON DUPLICATE KEY UPDATE Endpoint = Endpoint;
            """,
            (path, ip)
        )
        connection.commit()
    except errors.ProgrammingError as e:
        print(f"Caught exception: {e}")
        success = False
        connection.rollback()
    finally:
        cursor.close()
        connection.close()
    
    return success

def handle_rate_limit_request(ip: str, path: str):
    connection = get_connection()
    cursor = connection.cursor()
    success = True
    row = None

    try:
        cursor.execute(
            """
            SELECT LastRequestTime, CurrentLimit, ReputationDebounce
            FROM Endpoints
            WHERE IpAddress = %s AND Endpoint = %s;
            """, 
            (ip, path)
        )
        row = cursor.fetchone()
    except errors.ProgrammingError as e:
        print(f"Caught exception: {e}")
        success = False
        connection.rollback()
    finally:
        cursor.close()
        connection.close()
    
    if row == None or not success:
        return False
    
    last_request_time = row[0]
    current_limit = row[1]
    reputation_debounce = row[2]
    reputation = get_reputation(ip)
    max_limit = get_rate_limit_from_reputation(reputation, created_functions[path]["min_rate_limit"], created_functions[path]["min_rate_limit"])

    if (datetime.now() - last_request_time).total_seconds() >= created_functions[path]["duration"]:
        connection = get_connection()
        cursor = connection.cursor()
        current_limit = 0
        try:
            cursor.execute(
                """
                UPDATE Endpoints
                SET LastRequestTime = NOW(), CurrentLimit = %s, ReputationDebounce = FALSE
                WHERE IpAddress = %s AND Endpoint = %s;
                """,
                (current_limit, ip, path)
            )
            connection.commit()
        except errors.ProgrammingError as e:
            print(f"Caught exception: {e}")
            success = False
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
    else:        
        connection = get_connection()
        cursor = connection.cursor()
        current_limit = min(current_limit + 1, max_limit)
    
        try:
            cursor.execute(
                """
                UPDATE Endpoints
                SET CurrentLimit = %s
                WHERE IpAddress = %s AND Endpoint = %s;
                """,
                (current_limit, ip, path)
            )
            connection.commit()
        except errors.ProgrammingError as e:
            print(f"Caught exception: {e}")
            success = False
            connection.rollback()
        finally:
            cursor.close()
            connection.close()

    # TODO: I feel like this should be returning a status code instead of `False` so we can differentiate between
    # Whether a request failed due to a sql error or if the user is being rate limited.
    hit_rate_limit = current_limit >= max_limit

    if hit_rate_limit and not reputation_debounce: 
        connection = get_connection()
        cursor = connection.cursor()
        set_reputation(ip, reputation - 1)
        
        try:
            cursor.execute(
                """
                UPDATE Users
                SET LastOffense = NOW()
                WHERE IpAddress = %s;
                """,
                (ip,)
            )
            connection.commit()
        except errors.ProgrammingError as e:
            print(f"Caught exception: {e}")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()

        connection = get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute(
                """
                UPDATE Endpoints
                SET ReputationDebounce = TRUE
                WHERE IpAddress = %s AND Endpoint = %s;
                """,
                (ip, path)
            )
            connection.commit()
        except errors.ProgrammingError as e:
            print(f"Caught exception: {e}")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
    elif not hit_rate_limit:
        last_offense = datetime.now()      
        connection = get_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                SELECT LastOffense
                FROM Users
                WHERE IpAddress = %s;
                """,
                (ip,)
            )
            last_offense = cursor.fetchone()[0]
        except errors.ProgrammingError as e:
            print(f"Caught exception: {e}")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()

        if (datetime.now() - last_offense).total_seconds() >= REPUTATION_INCREASE_INTERVAL:
            set_reputation(ip, reputation + 1)
            connection = get_connection()
            cursor = connection.cursor()

            try:
                cursor.execute(
                    """
                    UPDATE Users
                    SET LastOffense = NOW()
                    WHERE IpAddress = %s;
                    """,
                    (ip,)
                )
                connection.commit()
            except errors.ProgrammingError as e:
                print(f"Caught exception: {e}")
                connection.rollback()
            finally:
                cursor.close()
                connection.close()  

    return success and not hit_rate_limit

@app.middleware("http")
async def try_rate_limit(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    
    path = request.url.path

    if path not in created_functions:
        return JSONResponse(content={"response": "Invalid endpoint"}, status_code=404)

    ip = request.client.host or "None"

    if not try_add_ip(ip):
        print("try_add_ip failed")
        return JSONResponse(content={"response": "Unknown error registering IP"}, status_code=520)
    
    if not try_add_endpoint(ip, request.url.path):
        print("try_add_endpoint failed")
        return JSONResponse(content={"response": "Unknown error registering IP"}, status_code=520)

    if not handle_rate_limit_request(ip, path):
        return JSONResponse(content={"response": "Woah, slow down buddy!"}, status_code=429)

    return await call_next(request)


def create_end_point(path: str, methods, min_rate_limit: int, max_rate_limit: int, accept_function: Callable[[Request], Awaitable[Response]], duration=60):
    if path in stored_paths or path in created_functions:
        # TODO: Add better error.
        raise("path already exists")

    stored_paths[path] = {"addresses": {}}

    created_functions[path] = {
        "min_rate_limit": min_rate_limit, "accept_function": accept_function, "duration": duration, "max_rate_limit": max_rate_limit}

    app.add_api_route(path, accept_function, methods=methods)
