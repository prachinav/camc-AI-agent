import os
from db_connector import get_db_connection

def get_species_for_location(lat, lon):
    sql_path = os.path.join(os.path.dirname(__file__), "DataCollection.sql")

    with open(sql_path, "r") as f:
        query = f.read()

    conn, tunnel = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (lon, lat))  # Note: lon, lat order for PostGIS
            results = cursor.fetchall()
            # Assuming species name is in column 0
            species = [row[0] for row in results]
            return species
    finally:
        conn.close()
        tunnel.close()
