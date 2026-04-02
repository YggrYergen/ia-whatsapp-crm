import os
import subprocess
import psycopg2

def main():
    print("Iniciando Wipe & Replace de la base de datos de PRODUCCIÓN...")
    
    # Scripts en orden
    scripts = [
        "scripts/setup/db_setup.py",
        "scripts/migration_ddl.py",
        "scripts/run_migration.py",
        "scripts/setup/enable_rt.py",
        "scripts/setup/fix_rls.py"
    ]
    
    for script in scripts:
        print(f"\n--- Ejecutando {script} ---")
        try:
            result = subprocess.run(["python", script], check=True, text=True, capture_output=True)
            print(result.stdout)
            if result.stderr:
                print("Warnings/Errors:", result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Error crítico al ejecutar {script}.")
            print(e.output)
            print(e.stderr)
            print("\nABORTANDO. Por favor corre los comandos manualmente en Supabase SQL Editor.")
            return

    print("\n✅ ¡Todos los scripts se ejecutaron correctamente en Producción!")

if __name__ == '__main__':
    main()
