import os
from db_connector import get_db_connection

def get_species_for_location(lat, lon):
    sql_path = os.path.join(os.path.dirname(__file__), "DataCollection.sql")

    with open(sql_path, "r") as f:
        query = f.read()

    conn, tunnel = get_db_connection()
    print("Back to handler")
    try:
        with conn.cursor() as cursor:
            print(lon, lat)
            cursor.execute(query, (lon, lat))
            results = cursor.fetchall()
            print("Results******",results)
            species = [row[0] for row in results]
            return species
    finally:
        conn.close()
        tunnel.close()
