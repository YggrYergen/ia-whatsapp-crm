import psycopg2
import os

DB_URL = "postgresql://postgres:Synapse!Synapse!@db.nemrjlimrnrusodivtoa.supabase.co:5432/postgres"
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "..", "schema.sql")

def init_db():
    print("Conectando a la base de datos...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    with open(SCHEMA_FILE, "r", encoding="utf-8") as file:
        schema_sql = file.read()

    print("Ejecutando schema.sql...")
    try:
        cur.execute(schema_sql)
        print("Base de datos inicializada correctamente.")
    except Exception as e:
        print(f"Error al inicializar la base de datos (puede que ya exista): {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    init_db()
