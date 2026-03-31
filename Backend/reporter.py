import os

def generate_report():
    # El script se encuentra en Backend, pero usaremos la ruta absoluta para seguridad
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(backend_dir, "report.md")
    script_name = "reporter.py"
    output_name = "report.md"
    
    # Configuraciones de ignorado
    ignore_names = {".env", "__pycache__", script_name, output_name, ".git", ".venv", "venv"}
    ignore_extensions = {".pyc", ".pyo", ".pyd", ".db", ".sqlite", ".json", ".lock"}

    structure_lines = ["# Arquitectura de Backend", ""]
    files_to_process = []

    def walk_and_build(path, prefix=""):
        try:
            # Filtrar entradas irrelevantes
            entries = []
            for entry in sorted(os.listdir(path)):
                full_path = os.path.join(path, entry)
                if entry in ignore_names:
                    continue
                if any(entry.endswith(ext) for ext in ignore_extensions):
                    continue
                entries.append(entry)

            for i, entry in enumerate(entries):
                full_path = os.path.join(path, entry)
                is_dir = os.path.isdir(full_path)
                
                connector = "├── " if i < len(entries) - 1 else "└── "
                structure_lines.append(f"{prefix}{connector}{entry}")
                
                if is_dir:
                    new_prefix = prefix + ("│   " if i < len(entries) - 1 else "    ")
                    walk_and_build(full_path, new_prefix)
                else:
                    files_to_process.append(full_path)
        except Exception as e:
            structure_lines.append(f"{prefix} [Error al leer {path}: {str(e)}]")

    # Iniciar escaneo desde Backend/
    structure_lines.append("Backend/")
    walk_and_build(backend_dir)

    # Preparar el contenido final
    final_output = "\n".join(structure_lines) + "\n\n---\n\n# Contenido de Archivos\n\n"

    for file_path in files_to_process:
        rel_path = os.path.relpath(file_path, backend_dir)
        filename = os.path.basename(file_path)
        
        final_output += f"--- INICIO DE ARCHIVO: {filename} (Ruta: Backend/{rel_path.replace(os.sep, '/')}) ---\n\n"
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                # Envolver en bloques de código markdown si no lo está ya, 
                # pero el usuario pidió los archivos completos.
                # Usaremos bloques de código para evitar que el markdown del archivo rompa el reporte.
                ext = os.path.splitext(filename)[1].lstrip('.')
                final_output += f"```{ext}\n{content}\n```\n\n"
        except Exception as e:
            final_output += f"[Error al leer el archivo: {str(e)}]\n\n"
            
        final_output += f"--- FIN DE ARCHIVO: {filename} ---\n\n"

    # Escribir el reporte final
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_output)

    print(f"Reporte generado exitosamente en: {report_path}")

if __name__ == "__main__":
    generate_report()
