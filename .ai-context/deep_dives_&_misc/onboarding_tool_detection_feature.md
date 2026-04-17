# Onboarding: Tool Detection & Superadmin Notification System

> **Status:** 🔴 NOT STARTED — Tracked for implementation before scaling  
> **Priority:** HIGH — Required before onboarding more than pilot clients  
> **Created:** 2026-04-14  
> **Context:** Discovered during first real onboarding session (FumigaMax fictional client)

## Problem

The onboarding config agent collects business requirements (type, services, hours, tools needed, etc.), but currently has **no mechanism to**:

1. **Detect tool gaps** — Compare the client's stated needs against available platform tools (booking engine, payment processing, inventory, etc.) and flag missing capabilities.
2. **Notify superadmins** — Alert superadmins of every completed (or failed) onboarding, including whether the client's requirements are fully satisfiable with existing tools.
3. **Provision sandbox chat** — Automatically configure the newcomer's "Chat de Pruebas" (sandbox) with the generated system prompt and all available tools, so the client can immediately test the AI behavior.
4. **Expose onboarding history** — Make the full config-agent conversation history available to superadmins for review, QA, and prompt iteration.

## Requirements

### R1: Tool Gap Detection
- The config agent's `mark_configuration_complete` tool (or a new post-completion step) should compare the client's `services_offered` and `special_instructions` against a registry of available tools.
- Output: `{ tools_available: [...], tools_missing: [...], coverage_percentage: N% }`
- If `tools_missing` is non-empty, the agent should tell the client: "Algunas funciones que necesitas están en desarrollo. Tu ejecutivo de cuenta te contactará."

### R2: Superadmin Notifications (Discord + DB)
- On every completed onboarding: Discord alert to `#onboarding-alerts` channel with:
  - Tenant name, ID, owner email
  - Tool coverage percentage
  - Missing tools list
  - Link to full conversation history
- On every **failed** onboarding (timeout, error, user abandoned): separate alert with error context
- Store notification records in `onboarding_events` table for audit trail

### R3: Sandbox Chat Auto-Configuration
- After `mark_configuration_complete`, automatically:
  1. Write the `generated_system_prompt` to `tenants.system_prompt`
  2. Enable available tools for the tenant in `tenant_tools` table
  3. Set up a sandbox conversation so the client can test immediately from `/chats`
- The sandbox should show a welcome message like: "Este es tu chat de pruebas. Envía un mensaje como si fueras un cliente para ver cómo responde tu asistente."

### R4: Onboarding Conversation History (Complex — Phase 2)
- Store the full config-agent conversation (all user + assistant messages) in a `onboarding_conversations` table
- Superadmin UI: `/admin/onboarding/:tenantId` page to review the conversation
- Useful for: prompt iteration, QA, understanding client expectations vs actual behavior
- **Note:** This requires frontend changes to persist conversation state server-side. Currently, conversation history only lives in React state (`historyRef`) and is lost on page reload.

## Architecture Notes

### Tool Registry (Proposed)
```python
AVAILABLE_TOOLS = {
    "appointment_booking": True,
    "payment_processing": False,  # Not yet implemented
    "inventory_management": False,
    "lead_qualification": True,
    "human_escalation": True,
    "faq_responses": True,
    "order_tracking": False,
    "quote_generation": False,
}
```

### Onboarding Events Table (Proposed Schema)
```sql
CREATE TABLE onboarding_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    event_type TEXT NOT NULL,  -- 'completed', 'failed', 'abandoned'
    tool_coverage NUMERIC,
    tools_available TEXT[],
    tools_missing TEXT[],
    conversation_summary TEXT,
    error_details JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## Dependencies
- Requires: Complete list of platform tools with availability status
- Requires: Discord webhook for `#onboarding-alerts` (separate from `#crm-observability`)
- Blocked by: Nothing — can start implementation anytime
