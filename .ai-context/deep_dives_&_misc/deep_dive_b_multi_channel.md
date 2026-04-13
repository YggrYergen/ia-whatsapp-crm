# Deep Dive B v3: Multi-Channel Messaging — RESEARCH-BACKED + CITED

> **Status:** FINAL — All docs verified with exact URLs (April 2026)  
> **Last Updated:** 2026-04-11 15:40 CLT  
> **Research:** 22+ dedicated web searches completed  
> **Criticality:** 🔴 CRITICAL — Compliance + Revenue  

---

## 📚 Official Documentation Index (BOOKMARKS FOR IMPLEMENTATION)

### WhatsApp Business Platform
| Doc | URL | Use For |
|:---|:---|:---|
| **Cloud API Hub** | https://developers.facebook.com/docs/whatsapp/cloud-api | Overview, setup, concepts |
| **Get Started** | https://developers.facebook.com/docs/whatsapp/cloud-api/get-started | App creation, tokens, first webhook |
| **Send Messages** | https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages | Text, media, interactive messages |
| **Messages API Reference** | https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages | Exact API payload format |
| **Webhooks Overview** | https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks | Webhook setup, payload structure |
| **Error Codes** | https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes/ | All error codes, meanings, fixes |
| **Pricing** | https://developers.facebook.com/docs/whatsapp/pricing | Per-message costs, rate cards by country |
| **Phone Number Management** | https://developers.facebook.com/docs/whatsapp/business-management-api/manage-phone-numbers | Registration, verification |
| **Message Templates** | https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates | Template CRUD, categories |
| **Embedded Signup** | https://developers.facebook.com/docs/whatsapp/embedded-signup | Self-serve onboarding for Tech Providers |

### Instagram Messaging API
| Doc | URL | Use For |
|:---|:---|:---|
| **Overview** | https://developers.facebook.com/docs/messenger-platform/instagram | Getting started, concepts |
| **Send Messages** | https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message | Send API format |
| **Webhooks** | https://developers.facebook.com/docs/messenger-platform/instagram/features/webhook | Webhook events |
| **Quick Replies** | https://developers.facebook.com/docs/messenger-platform/instagram/features/quick-replies | Quick reply buttons |
| **App Review** | https://developers.facebook.com/docs/messenger-platform/instagram/app-review | Permission requests |

### Meta Platform Security & Versioning
| Doc | URL | Use For |
|:---|:---|:---|
| **Webhook Security (Signature Verification)** | https://developers.facebook.com/docs/graph-api/webhooks/getting-started#event-notifications | HMAC-SHA256 verification |
| **Graph API Changelog** | https://developers.facebook.com/docs/graph-api/changelog | Version deprecation schedule |
| **App Review Process** | https://developers.facebook.com/docs/app-review | General Meta app review guide |

---

## 1. 🔴 BSUID Migration (ARCHITECTURE-BREAKING)

**Sources:** [Meta Graph API Changelog](https://developers.facebook.com/docs/graph-api/changelog) | [Twilio BSUID Guide](https://www.twilio.com/docs/whatsapp/bsuid) | [WhatsApp Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)

### What's Happening
WhatsApp is introducing **usernames** — users can message businesses without sharing phone numbers. Each user gets a **Business-Scoped User ID (BSUID)** per business portfolio.

### Timeline (confirmed April 2026)
| Date | Milestone |
|:---|:---|
| **Early April 2026** | BSUIDs appearing in webhooks NOW. Contact Book feature launched. |
| **May 2026** | APIs support sending messages via BSUID |
| **June 2026** | Business username claims begin |
| **H2 2026** | User-facing username feature global rollout |

### BSUID Webhook Payload (Real Example)
```json
{
  "contacts": [
    {
      "profile": {"name": "Jane Doe"},
      "user_id": "US.13491208655302741918",
      "wa_id": "US.13491208655302741918"
    }
  ],
  "messages": [
    {
      "from": "US.13491208655302741918",
      "id": "wamid.HBgLMTY1MDM4...",
      "type": "text",
      "text": {"body": "Hello"}
    }
  ]
}
```

**Key:** `user_id` field = BSUID. When user enables username, `wa_id` becomes the BSUID (not phone number).

### Required DB Changes (Sprint 1 — 2 minutes)
```sql
-- Add BSUID support to contacts (future-proofing)
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS bsuid text;
CREATE INDEX IF NOT EXISTS idx_contacts_bsuid ON contacts(bsuid) WHERE bsuid IS NOT NULL;
```

### Required Code Changes
```python
# In webhook handler — support both identifiers
def resolve_contact(webhook_data):
    contact_info = webhook_data.get("contacts", [{}])[0]
    bsuid = contact_info.get("user_id")  # BSUID if available
    phone = contact_info.get("wa_id")    # Phone or BSUID
    
    # Detect BSUID format (country_code.numeric_id)
    is_bsuid = phone and "." in phone and not phone.startswith("+")
    
    if bsuid:
        contact = await db.table("contacts").select("*").eq("bsuid", bsuid).single()
        if contact:
            return contact
    
    if phone and not is_bsuid:
        contact = await db.table("contacts").select("*").eq("phone", phone).single()
        if contact and bsuid:
            await db.table("contacts").update({"bsuid": bsuid}).eq("id", contact.id)
            return contact
    
    return await create_contact(phone=phone if not is_bsuid else None, bsuid=bsuid)
```

### Dormant Mode Implementation — Phase 1 (April 2026)

> **Forensic analysis completed 2026-04-11.**
> See [Full BSUID Forensic Report](file:///C:/Users/tomas/.gemini/antigravity/brain/2ae8123c-0df3-4743-86ba-b85da6306f81/bsuid_full_forensic.md) for the complete 40+ touch-point trace.

**Decision:** Implement as "dormant capture" — store BSUID data from webhooks NOW, but change ZERO contact resolution behavior. All lookups remain phone-first.

**What Phase 1 changes (4 code touches + 1 migration):**

| Change | File | Risk |
|:---|:---|:---|
| Add `bsuid TEXT NULL` column + `UNIQUE(tenant_id, bsuid)` partial index | DB migration (both DEV + PROD) | Near zero — metadata-only ALTER TABLE |
| Extract `bsuid = message.get("user_id")` with format validation | `use_cases.py:~L90` | Zero — additive `.get()`, no existing logic touched |
| Add `"bsuid": bsuid` to new contact insert | `use_cases.py:~L131` | Near zero — nullable column, NULL if absent |
| Backfill BSUID on existing contacts found by phone | `use_cases.py:~L115` | Near zero — non-blocking, idempotent, wrapped in try/except |

**What Phase 1 does NOT change:**
- ❌ Contact lookup order (remains phone-only)
- ❌ Reply routing (`to=patient_phone`)
- ❌ Tool queries (all still `.eq("phone_number", ...)`) 
- ❌ Rate limiter key (still phone-based)
- ❌ Frontend code (zero changes)
- ❌ RLS policies (row-level, not column-level)
- ❌ Realtime subscriptions (table-level listeners)
- ❌ Simulation suite (absence of `user_id` doesn't break anything)

### Database Constraints to Know (verified via MCP 2026-04-11)

| Constraint | Type | Dormant Impact | Phase 2 Impact |
|:---|:---|:---|:---|
| `phone_number NOT NULL` | Column constraint | 🟢 Unaffected — all current users have phones | 🔴 Must relax to NULLABLE when users can hide phone |
| `UNIQUE(tenant_id, phone_number)` | Unique index | 🟢 Unaffected | 🟡 Must become partial: `WHERE phone_number IS NOT NULL` |
| `contacts_pkey (id uuid)` | Primary key | 🟢 UUID-based, not phone-based | 🟢 No change needed |
| `contacts_tenant_id_fkey` | Foreign key | 🟢 References tenants(id) | 🟢 No change needed |

### 7 Breaking Points (Current Codebase — Will Fail in June 2026 WITHOUT Phase 2)

1. **`use_cases.py:L90`** — `patient_phone = message.get("from")` — assumes `from` is always a phone
2. **`use_cases.py:L102`** — `.eq("phone_number", patient_phone)` — phone-only lookup, misses BSUID users
3. **`use_cases.py:L131`** — `"phone_number": patient_phone` — stores BSUID in phone column
4. **`tools.py:L265`** — `.eq("phone_number", patient_phone)` — escalation silently fails
5. **`tools.py:L335`** — `.eq("phone_number", phone)` — scoring silently fails
6. **`main.py:L63`** — `.eq("phone_number", patient_phone)` — frontend send fails
7. **`meta_graph_api.py:L32`** — `to=patient_phone` — actually works (API accepts BSUIDs), but semantics are wrong

### Activation — Phase 2 (SEPARATE TASK — Must Deploy Before June 2026)

When Meta enables username hiding (~June 2026), `message["from"]` may contain a BSUID instead of a phone number. Phase 2 must be deployed BEFORE that happens.

**Phase 2 changes:**
1. Swap contact lookup: BSUID-first → phone-fallback (using the data Phase 1 pre-stored)
2. Relax `phone_number NOT NULL` → `NULLABLE`
3. Update `UNIQUE(tenant_id, phone_number)` to partial index (`WHERE phone_number IS NOT NULL`)
4. Add `UNIQUE(tenant_id, bsuid)` if not already present
5. Update all tool queries from `.eq("phone_number", ...)` → `.eq("id", contact_id)` 
6. Update frontend display: `contact.name || contact.phone_number || contact.bsuid`
7. Update simulation suite with BSUID-only test scenarios
8. BSUID format detection utility: `re.match(r'^[A-Z]{2}\..+$', identifier)`

> **Phase 2 is dramatically easier if Phase 1 is done:** every existing contact will already have their BSUID stored from ongoing webhook traffic.


## 2. WhatsApp Pricing (CORRECTED — Service = FREE)

**Source:** [WhatsApp Pricing](https://developers.facebook.com/docs/whatsapp/pricing)

### Current Model (Since July 1, 2025)

| Message Type | Cost | Notes |
|:---|:---|:---|
| **Service conversations (user-initiated)** | **FREE** ✅ | All replies within 24h window |
| **Non-template messages** | **FREE** ✅ | Text, images, video within 24h |
| **Utility templates (within 24h)** | **FREE** ✅ | Order confirmations, appointment reminders |
| **Utility templates (outside 24h)** | Paid per delivery | Country + volume tiered |
| **Marketing templates** | Paid per delivery | Always charged |
| **Authentication templates** | Paid per delivery | OTPs, login codes |

**Chile CLP billing:** Supported since April 1, 2026.

**Impact:** Our use case is 95%+ service conversations → **WhatsApp cost per tenant: ~0 CLP/month** for normal operations.

---

## 3. Portfolio Messaging Limits (No Warmup Needed!)

**Source:** Meta WABA docs (October 2025 change)

| Old System | New System (Oct 2025+) |
|:---|:---|
| Per-phone-number limits | **Portfolio-based** — all numbers share highest limit |
| New numbers start at 250/day | New numbers **inherit portfolio limit immediately** |
| Warm-up over days/weeks | **No warm-up needed** |
| Tier upgrades every 24-48h | Upgrades every ~6 hours |

**Tiers:**
| Tier | Unique Customers/24h |
|:---|:---|
| Unverified | 250 |
| Tier 1 | 1,000 |
| Tier 2 | 10,000 |
| Tier 3 | 100,000 |
| Tier 4 | Unlimited |

**Throughput:** Default 80 messages/second. Can upgrade to 1,000 MPS at Tier 4.

**Impact:** When adding fumigation client's number to our portfolio, it immediately gets our existing tier. Zero warmup.

---

## 4. Webhook Signature Verification (Security Audit Needed)

**Source:** [Webhook Security](https://developers.facebook.com/docs/graph-api/webhooks/getting-started#event-notifications)

```python
import hmac
import hashlib

def verify_webhook_signature(request_body: bytes, signature_header: str, app_secret: str) -> bool:
    """Verify X-Hub-Signature-256 from Meta webhooks."""
    if not signature_header:
        return False
    
    expected = "sha256=" + hmac.new(
        app_secret.encode('utf-8'),
        request_body,  # MUST be raw bytes, NOT parsed JSON
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature_header)  # Timing-safe!
```

**Critical checks:**
1. ✅ Verify on **raw request bytes** (not parsed JSON)
2. ✅ Use `hmac.compare_digest()` (timing-safe comparison)
3. ✅ Return 403 BEFORE any business logic on invalid signature
4. ✅ Return 200 immediately on valid webhook, process async
5. ⚠️ **New mTLS cert since March 31, 2026** — verify Cloud Run handles it

**Action:** Audit our `main.py` webhook handler against this pattern.

---

## 5. WhatsApp Error Codes (Must Handle)

**Source:** [Error Codes Reference](https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes/)

| Code | Meaning | Our Action |
|:---|:---|:---|
| **130429** | Throughput (MPS) limit | Exponential backoff + queue |
| **131048** | Spam/quality limit | CRITICAL ALERT — stop messaging, check quality |
| **131056** | Pair rate limit | Queue with 6s min gap per user |
| **131047** | 24h window closed | Switch to template message |
| **400** | Bad request (payload) | Log full payload, fix in code |
| **470** | Policy violation | CRITICAL ALERT — immediate review |

---

## 6. Graph API Version Management

**Source:** [Graph API Changelog](https://developers.facebook.com/docs/graph-api/changelog)

| Version | Status |
|:---|:---|
| **v25.0** | ✅ Current (Feb 18, 2026) |
| v24.0 | Active |
| v23.0 | Active |
| **v19.0** | ⚠️ **DEPRECATED May 21, 2026** |
| **v20.0** | ⚠️ Deprecated Sep 24, 2026 |

**Action:** Search codebase for hardcoded API version strings. Ensure all use `v25.0`.

**Other v25.0 changes:**
- `metadata=1` query param deprecated (ignored after May 19, 2026)
- **New mTLS Certificate Authority** since March 31, 2026

---

## 7. Instagram Messaging API (Sprint 2 — Complete Spec)

**Source:** [Instagram Messaging Overview](https://developers.facebook.com/docs/messenger-platform/instagram)

### Send Message
```
POST https://graph.facebook.com/v25.0/me/messages?access_token=<TOKEN>
```

**Text:**
```json
{"recipient": {"id": "<IGSID>"}, "message": {"text": "Hello!"}}
```

**Quick Replies (max 13, max 20 char each):**
```json
{
  "recipient": {"id": "<IGSID>"},
  "message": {
    "text": "¿Cómo puedo ayudarte?",
    "quick_replies": [
      {"content_type": "text", "title": "Agendar cita", "payload": "BOOK"},
      {"content_type": "text", "title": "Ver precios", "payload": "PRICING"},
      {"content_type": "text", "title": "Hablar con humano", "payload": "ESCALATE"}
    ]
  }
}
```

### Instagram vs WhatsApp Differences

| Feature | Instagram | WhatsApp |
|:---|:---|:---|
| 24h messaging window | ✅ Yes | ✅ Yes |
| Templates after window | ❌ **NO** — blocked entirely | ✅ Via templates |
| Human Agent extension | ✅ 7 days | ❌ N/A |
| Business-initiated outreach | ❌ Cannot | ✅ Templates |
| Rate limit | **200 API calls/hour** | 80 MPS (upgradeable to 1,000) |
| Permission needed | `instagram_manage_messages` | `whatsapp_business_messaging` |

> [!WARNING]
> Instagram has NO template equivalent. Once 24h window closes, we CANNOT reach the customer. Business must understand this limitation.

---

## 8. Meta App Review Process (Sprint 3)

**Source:** [App Review](https://developers.facebook.com/docs/app-review) | [WA Permissions](https://developers.facebook.com/docs/whatsapp/embedded-signup)

### When Needed
- **Direct developers:** NO App Review needed (accessing own data)
- **Tech Providers (us at tenant #7):** MUST pass App Review

### Requirements per Permission

**`whatsapp_business_messaging`:**
- Written explanation of messaging functionality
- Video: Demo showing message sent from our dashboard → received in WhatsApp
- Show: our app → send → WA mobile/web receives

**`whatsapp_business_management`:**
- Written: How we manage client WABA assets
- Video: Demo of template creation/management
- Show: our dashboard → create template

### Best Practices
- Submit **separate videos per permission**
- Functioning prototype required (not mockups)
- Professional domain, public privacy policy
- Turnaround: 24h to 7 business days

---

## 9. Implementation Priority (With Doc References)

### Sprint 1 (Now — Tuesday deadline)
| Task | Effort | Docs |
|:---|:---|:---|
| Add `bsuid` column to contacts | 2 min | [Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks) |
| Extract + store BSUIDs from webhooks (dormant capture) | 15 min | [Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks) |
| Backfill existing contacts' BSUIDs | 3 min | [Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks) |
| Verify webhook signature implementation | 15 min | [Webhook Security](https://developers.facebook.com/docs/graph-api/webhooks/getting-started) |
| Audit API version strings (→ v25.0) | 10 min | [Changelog](https://developers.facebook.com/docs/graph-api/changelog) |
| Add WhatsApp error code handler | 30 min | [Error Codes](https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes/) |

### Sprint 2 (Instagram integration)
| Task | Docs |
|:---|:---|
| Multi-channel DB schema | [Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks) + [IG Webhooks](https://developers.facebook.com/docs/messenger-platform/instagram/features/webhook) |
| NormalizedMessage dataclass | — |
| Instagram webhook handler | [IG Overview](https://developers.facebook.com/docs/messenger-platform/instagram) |
| Instagram Send API | [IG Send Message](https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message) |
| Quick Replies | [IG Quick Replies](https://developers.facebook.com/docs/messenger-platform/instagram/features/quick-replies) |

### Sprint 3 (Tech Provider)
| Task | Docs |
|:---|:---|
| Embedded Signup implementation | [Embedded Signup](https://developers.facebook.com/docs/whatsapp/embedded-signup) |
| Meta App Review submission | [App Review](https://developers.facebook.com/docs/app-review) |
| Facebook Messenger adapter | [Messenger Platform](https://developers.facebook.com/docs/messenger-platform) |

---

## 10. Risk Register with Doc References

| Risk | Mitigation | Verify Against |
|:---|:---|:---|
| BSUID breaks contact lookup (June 2026) | Phase 1: dormant capture NOW. Phase 2: lookup swap before June. | [Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks) |
| IG window closes, can't follow up | Collect phone/email as backup | [IG Messaging](https://developers.facebook.com/docs/messenger-platform/instagram) |
| Graph API v19 deprecated May 21 | Use v25.0 everywhere | [Changelog](https://developers.facebook.com/docs/graph-api/changelog) |
| mTLS cert broke webhooks | Verify Cloud Run TLS handling | [Changelog](https://developers.facebook.com/docs/graph-api/changelog) |
| App Review rejected | Follow video requirements exactly | [App Review](https://developers.facebook.com/docs/app-review) |
| Quality rating drops | Monitor quality dashboard | [WA Pricing](https://developers.facebook.com/docs/whatsapp/pricing) |
