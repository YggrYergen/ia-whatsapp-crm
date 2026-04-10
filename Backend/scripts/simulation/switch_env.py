#!/usr/bin/env python3
# ================================================================================
# Phase 5A: Switch Backend to Dev Environment
# ================================================================================
# Swaps the .env file to point at the DEV Supabase instance for safe simulation.
# Run this BEFORE starting the backend for simulation.
#
# Usage:
#   python -m scripts.simulation.switch_env dev    # Switch to dev
#   python -m scripts.simulation.switch_env prod   # Switch back to prod
#   python -m scripts.simulation.switch_env status  # Show current state
# ================================================================================

import sys
import os
import re

ENV_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".env")

# Known identifiers
DEV_SUPABASE_REF = "nzsksjczswndjjbctasu"
PROD_SUPABASE_REF = "nemrjlimrnrusodivtoa"


def read_env():
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        return f.read()


def write_env(content: str):
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def detect_active(content: str) -> str:
    """Detect which Supabase is currently active."""
    # Find uncommented SUPABASE_URL line
    for line in content.splitlines():
        if line.startswith("SUPABASE_URL=") and not line.startswith("#"):
            if DEV_SUPABASE_REF in line:
                return "dev"
            elif PROD_SUPABASE_REF in line:
                return "prod"
    return "unknown"


def switch_to(target: str, content: str) -> str:
    """Switch active Supabase by commenting/uncommenting lines."""
    lines = content.splitlines()
    result = []
    
    for line in lines:
        stripped = line.lstrip("# ").strip()
        
        # Handle SUPABASE_URL lines
        if "SUPABASE_URL=" in stripped and "SUPABASE_DB_URL" not in stripped:
            if target == "dev":
                if DEV_SUPABASE_REF in stripped:
                    result.append(stripped)  # Uncomment dev
                elif PROD_SUPABASE_REF in stripped:
                    result.append(f"# {stripped}")  # Comment prod
                else:
                    result.append(line)
            elif target == "prod":
                if PROD_SUPABASE_REF in stripped:
                    result.append(stripped)  # Uncomment prod
                elif DEV_SUPABASE_REF in stripped:
                    result.append(f"# {stripped}")  # Comment dev
                else:
                    result.append(line)
        
        # Handle SUPABASE_SERVICE_ROLE_KEY lines
        elif "SUPABASE_SERVICE_ROLE_KEY=" in stripped:
            if target == "dev":
                if DEV_SUPABASE_REF in stripped:
                    result.append(stripped)  # Uncomment dev key
                elif PROD_SUPABASE_REF in stripped:
                    result.append(f"# {stripped}")  # Comment prod key
                else:
                    result.append(line)
            elif target == "prod":
                if PROD_SUPABASE_REF in stripped:
                    result.append(stripped)  # Uncomment prod key
                elif DEV_SUPABASE_REF in stripped:
                    result.append(f"# {stripped}")  # Comment dev key
                else:
                    result.append(line)
        
        # Handle SUPABASE_DB_URL lines
        elif "SUPABASE_DB_URL=" in stripped:
            if target == "dev":
                if DEV_SUPABASE_REF in stripped:
                    result.append(stripped)
                elif PROD_SUPABASE_REF in stripped:
                    result.append(f"# {stripped}")
                else:
                    result.append(line)
            elif target == "prod":
                if PROD_SUPABASE_REF in stripped:
                    result.append(stripped)
                elif DEV_SUPABASE_REF in stripped:
                    result.append(f"# {stripped}")
                else:
                    result.append(line)
        
        # Handle ENVIRONMENT line
        elif stripped.startswith("ENVIRONMENT="):
            if target == "dev":
                result.append("ENVIRONMENT=development")
            elif target == "prod":
                result.append("ENVIRONMENT=production")
        else:
            result.append(line)
    
    return "\n".join(result)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.simulation.switch_env [dev|prod|status]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    content = read_env()
    current = detect_active(content)
    
    if command == "status":
        emoji = "🔧" if current == "dev" else "🚀" if current == "prod" else "❓"
        print(f"{emoji} Current environment: {current.upper()}")
        return
    
    if command not in ("dev", "prod"):
        print(f"❌ Unknown command: {command}. Use 'dev', 'prod', or 'status'.")
        sys.exit(1)
    
    if current == command:
        print(f"Already on {command.upper()}. No changes needed.")
        return
    
    new_content = switch_to(command, content)
    write_env(new_content)
    
    new_active = detect_active(new_content)
    if command == "dev":
        print(f"🔧 Switched to DEVELOPMENT environment (Supabase: {DEV_SUPABASE_REF})")
        print(f"   ⚠️  Restart the backend server to apply changes.")
    else:
        print(f"🚀 Switched to PRODUCTION environment (Supabase: {PROD_SUPABASE_REF})")
        print(f"   ⚠️  Restart the backend server to apply changes.")


if __name__ == "__main__":
    main()
