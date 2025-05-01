import os
import mysql.connector
from mysql.connector import pooling

pool = pooling.MySQLConnectionPool(
    pool_name="AntiDdos",
    pool_size=10,
    host="localhost",
    user="user",
    password="pass?",
    database="anti_ddos",
)


def get_connection():
    return pool.get_connection()
