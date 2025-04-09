import psycopg2

def get_db_connection():
    conn = psycopg2.connect(
        dbname="thesta_db",
        user="skypirate",
        host="localhost",
        port="5432"
    )
    return conn