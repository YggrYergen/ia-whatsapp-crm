import os

files = ['curl_stderr.txt', 'error_clean.txt', 'output_debug.json', 'logs.json']

for file in files:
    if os.path.exists(file):
        print(f"\n--- Reading {file} ---")
        try:
            with open(file, 'r', encoding='utf-16le', errors='ignore') as f:
                content = f.read()
                print(content[:1500])
        except Exception as e:
            print(f"Failed to read {file}: {e}")
