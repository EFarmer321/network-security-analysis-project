from mysql.connector import pooling, errors

pool = None

def get_connection():
    if pool == None:
        raise("You need to call `init_database` before calling `get_connection`")
    
    return pool.get_connection()

def init_database(username, password):
    global pool

    try:
        pool = pooling.MySQLConnectionPool(
            pool_name="anti-ddos",
            pool_size=10,
            host="localhost",
            user=username,
            password=password,
            port=3306
        )

        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS `anti-ddos`")
        cursor.close()
        connection.close()
    except errors.ProgrammingError:
        print("Invalid password.")
        exit(1)

    pool = pooling.MySQLConnectionPool(
        pool_name="anti-ddos",
        pool_size=10,
        host="localhost",
        user=username,
        password=password,
        database="anti-ddos", 
        port=3306
    )


    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Users (
                IpAddress VARCHAR(50) NOT NULL PRIMARY KEY,
                Reputation INT,
                LastOffense DATETIME DEFAULT NOW()
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Endpoints (
                Endpoint VARCHAR(255) NOT NULL,
                IpAddress VARCHAR(50) NOT NULL,
                LastRequestTime DATETIME,
                CurrentLimit INT DEFAULT 0,
                PRIMARY KEY (IpAddress, Endpoint),
                FOREIGN KEY (IpAddress) REFERENCES Users(IpAddress)
                ON DELETE CASCADE
            );
            """
        )
        cursor.close()
        connection.close()
    except errors.ProgrammingError as e:
        print(f"Failed to create table: {e}")
        exit(1)
    