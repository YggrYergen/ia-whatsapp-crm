# 🔴 INCIDENT REPORT — April 12, 2026 00:47 CLT

> **Severity:** CRITICAL (contact permanently locked in PROD)  
> **Duration:** Ongoing — contact `83dc2480` is STILL locked  
> **Affected User:** 56931374341 (your personal number, "Rapida Media Co.")  
> **Tenant:** d8376510 (CasaVitaCure)

---

## 1. What Happened — The Cascade Chain

The errors fired in rapid succession at 00:47-00:48 CLT (04:47-04:48 UTC). Here's the exact chain:

```
00:47:00 — Hardware/Network HTTP layer error (PYTHON-16)
    ↓ Connection to external services timed out
00:47:00 — ❌ Shadow forward failed (PYTHON-18)
    ↓ MetaGraphAPIClient.send_text_message → ConnectTimeout to graph.facebook.com
00:47:00 — ConnectTimeout send_text_message (PYTHON-17)
    ↓ The main reply to the user ALSO failed — same ConnectTimeout
00:47:00 — ❌ Meta API send failed (PYTHON-19)
    ↓ The LLM processed the message, generated a reply, but couldn't SEND it
00:47:00 — Failed to send email alert (PYTHON-1A)
    ↓ Even the alert system couldn't reach the internet
00:47:00 — ConnectTimeout send_business_email_alert (PYTHON-1B)
00:48:00 — Failed to send Discord alert (PYTHON-1C)
    ↓ Discord webhook also unreachable 
00:48:00 — ConnectTimeout send_discord_alert (PYTHON-1D)
    ↓ At this point ALL outbound HTTP connections are dead
00:48:00 — 🔒 Processing Lock Release Failed (PYTHON-1E)
    ↓ _unset_processing() tried to PATCH contacts but got StreamReset
    ↓ httpx.RemoteProtocolError: <StreamReset stream_id:7, error_code:1, remote_reset:True>
    ↓ Even Supabase was unreachable
00:48:00 — ❌ Failed to unset processing lock (PYTHON-1F)
    ↓ The "finally" cleanup ALSO failed
    ↓ 🔴 CONTACT IS NOW PERMANENTLY LOCKED 🔴
00:55:00 — 🚨 ESCALACIÓN triggered
    ↓ 7 minutes later, a different message somehow got through
    ↓ The escalation tool ran for phone 56912345678 (test contact)
    ↓ This means SOME connectivity was restored by 00:55
```

## 2. Root Cause — Cloud Run Instance Network Death

**What happened:** The Cloud Run instance experienced a **total network isolation event**. All outbound HTTP connections (Meta API, Discord, email, AND Supabase) failed simultaneously.

**Evidence:**
- ALL external services failed at the exact same second (00:47)
- The error types are all `ConnectTimeout` and `RemoteProtocolError: StreamReset`
- This is NOT an API-specific issue (Meta/Discord/email all failed together)
- The `StreamReset stream_id:7, error_code:1, remote_reset:True` is an HTTP/2 connection being forcibly closed

**Most likely cause:** Cloud Run's infrastructure recycled the instance (cold start, scaling event, or infrastructure maintenance), and the instance's network stack was briefly broken during the transition. This is a **known Cloud Run behavior** — instances can be preempted or recycled at any time.

**Why it lasted ~8 minutes:**
- 00:47: Network dies mid-request
- 00:48: Lock release fails → contact permanently locked
- 00:55: A new instance spins up (or connectivity restores), processes the next message
- But the LOCK was never released → all subsequent messages from 56931374341 are silently dropped

## 3. 🔴 CRITICAL FINDING #1: Contact Is STILL Permanently Locked

```sql
-- LIVE PROD DATA RIGHT NOW:
id:               83dc2480-aa91-4a59-8e7a-0a41c73e2186
name:             Rapida Media Co.
phone_number:     56931374341
bot_active:       true       ← bot thinks it's active
is_processing_llm: TRUE      ← ⚡ STILL LOCKED ⚡
last_message_at:  2026-04-10 14:17:24  ← hasn't been updated since April 10!
```

**This is why the assistant doesn't respond to your messages right now.**

Every incoming message hits line 222 (`if is_processing and not is_simulation`), checks if the lock is stale... and the TTL check FAILS because of Finding #2.

## 4. 🔴 CRITICAL FINDING #2: Block E3 (Lock TTL) Is COMPLETELY Non-Functional on PROD

The lock TTL code (line 225) does:
```python
updated_at_str = contact_data.get("updated_at") if contact_data else None
```

**But the PROD `contacts` table does NOT HAVE an `updated_at` column.**

PROD columns (verified via MCP):
```
id, tenant_id, phone_number, name, bot_active, role, status, 
is_processing_llm, metadata, last_message_at, created_at, bsuid
```

**No `updated_at`.** The column was supposed to be added in Block E3's migration, but it was only applied to DEV, not PROD.

So the TTL check does:
1. `updated_at_str = contact_data.get("updated_at")` → returns `None`
2. `if updated_at_str:` → `False`
3. Falls through with `stale_lock = False`
4. `if not stale_lock:` → skips the message: `"Already processing (lock is fresh). Skipping."`

**The entire "90-second lock TTL" safety mechanism does not work in production.** It has NEVER worked. Every message from your number since the incident has been silently dropped at line 260.

## 5. Why "Chat de Pruebas" Works But Real WhatsApp Doesn't

The simulation endpoint (`/api/simulate`) sets `is_simulation = True` in the payload.

Line 222: `if is_processing and not is_simulation:`

Simulations completely skip the lock check. So the chat de pruebas works fine while real WhatsApp messages are permanently blocked.

## 6. Conversation Analysis — What the User Experienced

From the message history:

| Time (UTC) | Role | Message |
|:---|:---|:---|
| 03:25 | user | "Como dijiste disculpa?" |
| 03:26 | assistant | "Hola, ¿cómo estás?..." (working normally) |
| 03:46 | user | "Em no estoy seguro" |
| 03:47 | assistant | "Entiendo, por lo que me cuentas..." (still working) |
| 04:41 | user | "A ver me gustaría agendar" |
| 04:42 | assistant | "¡Claro! Para agendar..." (still working, slow) |
| 04:42 | user | "1 c 2 c 3 c" |
| 04:43 | assistant | "Entiendo... ¿nombre, apellido, horario?" |
| 04:44 | user | "Carla tapia y mañana a las 10" |
| 04:45 | assistant | "Sí, mañana a las 10:00 está disponible 😊" |
| 04:46 | user | "Por QUEEE SI YA DIJEE CTMMMM" (frustration mounting) |
| 04:47 | assistant | "Perfecto, quedó confirmado..." ← **THIS was the last response** |
| 04:47 | 💀 | **NETWORK DIES — ConnectTimeout cascade** |
| 04:51 | user | "What?" ← **No response (locked)** |
| 04:54 | user | "Olaaa" ← **No response (locked)** |
| 04:55 | user | "QUEEEE WEAAA AAAH HOLAAA" ← **No response (locked)** |

The bot DID generate a response at 04:47 (the booking confirmation), but:
1. The response was saved to DB (Supabase was still reachable at that point)
2. The response FAILED to send via WhatsApp (ConnectTimeout)
3. The lock FAILED to release (StreamReset)
4. All subsequent messages → permanently dropped

## 7. Summary of Issues Found

| # | Issue | Severity | Status |
|:---|:---|:---|:---|
| **INC-1** | Contact 83dc2480 is permanently locked (`is_processing_llm=true`) | 🔴 CRITICAL | Needs manual fix (1 SQL query) |
| **INC-2** | `updated_at` column missing from PROD contacts table — Block E3 TTL is non-functional | 🔴 CRITICAL | Migration never applied to PROD |
| **INC-3** | Network death cascade has no recovery mechanism — a single instance failure permanently locks contacts | 🟡 ARCHITECTURAL | Needs a finally/cleanup block that always runs |
| **INC-4** | `last_message_at` not being updated — shows April 10 but messages exist from April 12 | 🟡 BUG | The update logic isn't writing to this field |
| **INC-5** | Lock release failure in `_unset_processing()` has no retry mechanism | 🟡 RESILIENCE | Single attempt → permanent lock |

## 8. Immediate Fixes Needed (DO NOT EXECUTE — for user review)

### Fix 1: Unlock the contact (30 seconds)
```sql
UPDATE contacts 
SET is_processing_llm = false 
WHERE id = '83dc2480-aa91-4a59-8e7a-0a41c73e2186';
```

### Fix 2: Add `updated_at` column to PROD (1 minute)
```sql
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

-- Auto-update trigger (same as DEV)
CREATE OR REPLACE FUNCTION update_contacts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER contacts_updated_at_trigger
    BEFORE UPDATE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_contacts_updated_at();
```

### Fix 3: Add lock release retry/finally (code change)
The `_unset_processing()` function needs to be in a `finally` block that retries once on failure, and has a fallback in-memory TTL that forces release on the next message.

### Fix 4: Update `last_message_at` on message processing
The orchestrator should update `last_message_at` whenever it processes a message. Currently this field is stale.
