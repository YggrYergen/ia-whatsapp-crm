import json
import traceback

with open('extracted_logs.txt', 'w', encoding='utf-8') as out:
    for filename in ['curl_stderr.txt', 'error_clean.txt', 'output_debug.json', 'logs.json', 'error.log', 'error_all.txt', 'error_bg.txt']:
        try:
            with open(filename, 'r', encoding='utf-16le', errors='ignore') as f:
                content = f.read()
                if not content.strip() or len(content) < 10:
                    raise ValueError("Probably wrong encoding")
                out.write(f"\n--- {filename} (utf-16le) ---\n")
                if "logs.json" in filename:
                    for line in content.splitlines():
                        if 'timeout' in line.lower() or 'exception' in line.lower() or 'traceback' in line.lower() or 'error' in line.lower():
                            out.write(line + "\n")
                else:
                    out.write(content[:2000] + "\n")
        except:
            try:
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    out.write(f"\n--- {filename} (utf-8) ---\n")
                    if "logs.json" in filename:
                        for line in content.splitlines():
                            if 'timeout' in line.lower() or 'exception' in line.lower() or 'traceback' in line.lower() or 'error' in line.lower():
                                out.write(line + "\n")
                    else:
                        out.write(content[:2000] + "\n")
            except Exception as e:
                out.write(f"Failed {filename}: {e}\n")
