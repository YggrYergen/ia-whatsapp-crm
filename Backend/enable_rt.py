import psycopg2
import sys

conn_string = "postgresql://postgres:Synapse!Synapse!@db.nemrjlimrnrusodivtoa.supabase.co:5432/postgres"

def enable_realtime():
    print("Conectando a la Base de Datos para habilitar Real-time de Supabase...")
    try:
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cursor = conn.cursor()

        # Configurar realtime para las tablas "messages" y "contacts"
        sql = """
        BEGIN;
            -- Recrear la publicacion de realtime si existiera o estaria de por defecto (no es necesaria en Supabase nuevo a veces, pero ayuda)
            DROP PUBLICATION IF EXISTS supabase_realtime;
            CREATE PUBLICATION supabase_realtime;
        COMMIT;
        
        -- Agregar explícitamente las tablas a emitir websockets
        ALTER PUBLICATION supabase_realtime ADD TABLE contacts;
        ALTER PUBLICATION supabase_realtime ADD TABLE messages;
        """
        cursor.execute(sql)
        print("¡Eventos en Tiempo Real ACTIVADOS a nivel de base de datos exitosamente para 'messages' y 'contacts'!")

    except Exception as e:
        print("Hubo un error configurando Real-Time.")
        print(str(e))
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()

if __name__ == "__main__":
    enable_realtime()
