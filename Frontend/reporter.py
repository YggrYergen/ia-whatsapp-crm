import os

def generate_report():
    # Obtener el directorio base de la carpeta Frontend
    frontend_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(frontend_dir, "report.md")
    script_name = "reporter.py"
    output_name = "report.md"
    
    # Configuraciones de ignorado para Frontend (Next.js / React / Credentials)
    ignore_names = {
        ".env", ".env.local", ".env.development", ".env.production", 
        "node_modules", ".next", "out", "build", "dist", ".vercel", 
        ".turbo", ".vercel_build_output", ".git",
        script_name, output_name, "package-lock.json"
    }
    
    # Ignorar archivos compilados, bases de datos o multimedia para no contaminar el markdown
    ignore_extensions = {
        ".pyc", ".db", ".sqlite", ".lock", 
        ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".gif",
        ".mp4", ".mp3", ".wav", ".ttf", ".woff", ".woff2", ".eot"
    }

    structure_lines = ["# Arquitectura de Frontend", ""]
    files_to_process = []

    def walk_and_build(path, prefix=""):
        try:
            # Filtrar entradas irrelevantes
            entries = []
            for entry in sorted(os.listdir(path)):
                # Ignorar carpetas/archivos explícitamente prohibidos
                if entry in ignore_names:
                    continue
                # Ignorar extensiones binarias/bloatware
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
            structure_lines.append(f"{prefix} [Error al leer directorio {path}: {str(e)}]")

    # Iniciar escaneo desde la raíz del Frontend
    structure_lines.append("Frontend/")
    walk_and_build(frontend_dir)

    # Preparar el contenido final
    final_output = "\n".join(structure_lines) + "\n\n---\n\n# Contenido de Archivos\n\n"

    for file_path in files_to_process:
        rel_path = os.path.relpath(file_path, frontend_dir)
        filename = os.path.basename(file_path)
        
        final_output += f"--- INICIO DE ARCHIVO: {filename} (Ruta: Frontend/{rel_path.replace(os.sep, '/')}) ---\n\n"
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                
                # Resaltado de sintaxis predictivo para markdown
                ext = os.path.splitext(filename)[1].lstrip('.')
                if ext in ["tsx", "ts", "jsx", "js"]:
                    lang = "typescript" if "ts" in ext else "javascript"
                elif ext in ["css", "scss"]:
                    lang = "css"
                elif ext == "json":
                    lang = "json"
                elif ext == "md":
                    lang = "markdown"
                else:
                    lang = ext

                final_output += f"```{lang}\n{content}\n```\n\n"
        except Exception as e:
            final_output += f"[Error al leer el archivo: {str(e)}]\n\n"
            
        final_output += f"--- FIN DE ARCHIVO: {filename} ---\n\n"

    # Escribir el reporte final
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_output)

    print(f"Reporte Frontend generado de forma segura en: {report_path}")

if __name__ == "__main__":
    generate_report()
