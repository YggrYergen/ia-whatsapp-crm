#!/usr/bin/env python3
# ================================================================================
# Phase 5A: Simulation Cleanup
# ================================================================================
# Removes all contacts and messages created by the simulation suite from the
# dev Supabase database. Uses phone number prefix "5691000000" to identify 
# simulation data.
#
# Usage:
#   python -m scripts.simulation.cleanup
#   python -m scripts.simulation.cleanup --dry-run
# ================================================================================

import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from supabase import create_async_client
from dotenv import load_dotenv

# ── Simulation phone prefixes to clean ─────────────────────────────────
SIM_PHONE_PREFIX = "5691000000"


async def main():
    parser = argparse.ArgumentParser(description="Phase 5A: Simulation Data Cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be deleted without actually deleting")
    args = parser.parse_args()
    
    # Load env
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)
    
    # Safety check: refuse to run against production
    if "nemrjlimrnrusodivtoa" in supabase_url:
        print("🛑 ABORT: This script detected a PRODUCTION Supabase URL. Refusing to run.")
        print("   Only run this against the development database.")
        sys.exit(1)
    
    client = await create_async_client(supabase_url, supabase_key)
    
    print("🔍 Scanning for simulation data...")
    
    # Find simulation contacts
    contacts_res = await client.table("contacts").select("id, phone_number, name").like("phone_number", f"{SIM_PHONE_PREFIX}%").execute()
    sim_contacts = contacts_res.data or []
    
    print(f"   Found {len(sim_contacts)} simulation contacts:")
    for c in sim_contacts:
        print(f"   - {c['phone_number']} ({c['name']}) → {c['id']}")
    
    if not sim_contacts:
        print("✅ No simulation data found. Nothing to clean.")
        return
    
    contact_ids = [c["id"] for c in sim_contacts]
    
    # Find messages for simulation contacts
    messages_count = 0
    for cid in contact_ids:
        msg_res = await client.table("messages").select("id", count="exact").eq("contact_id", cid).execute()
        messages_count += msg_res.count or 0
    
    print(f"   Found {messages_count} messages from simulation contacts")
    
    if args.dry_run:
        print(f"\n🔶 DRY RUN: Would delete {messages_count} messages and {len(sim_contacts)} contacts.")
        print("   Run without --dry-run to actually delete.")
        return
    
    # Delete messages first (FK constraint)
    print(f"\n🗑️  Deleting {messages_count} messages...")
    for cid in contact_ids:
        await client.table("messages").delete().eq("contact_id", cid).execute()
    
    # Delete contacts
    print(f"🗑️  Deleting {len(sim_contacts)} contacts...")
    for cid in contact_ids:
        await client.table("contacts").delete().eq("id", cid).execute()
    
    print(f"✅ Cleanup complete: {messages_count} messages + {len(sim_contacts)} contacts removed.")


if __name__ == "__main__":
    asyncio.run(main())
