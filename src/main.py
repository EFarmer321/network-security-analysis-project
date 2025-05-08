import uvicorn
from fastapi.responses import JSONResponse
from app import app
from utils import *
from database import init_database
from rate_limiter import create_end_point
import getpass


async def test_function():
    return JSONResponse(content={"response": "HELLO YES HELLO!!!!!@!@#!!@#!!!"}, status_code=200)


def anti_ddos_init():
    port = 0

    create_end_point("/test", ["GET"], 5, 10, test_function, 15)

    while True:
        port = input(
            f"Enter your port number ({PORT_RANGE_MIN} - {PORT_RANGE_MAX}): ")

        try:
            port = int(port)
        except:
            print("You must enter an integer")
            continue

        if not is_port_in_valid_range(port):
            print("Invalid port number")
        else:
            break

    print("Input your MySQL password and username. If the database has not been created yet, one will be made for you.")
    username = input("Enter your database username: ")
    password = getpass.getpass("Enter database password: ")
    init_database(username, password)

    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    anti_ddos_init()
