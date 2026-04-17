# BACKLOG.md — Recall Memory (Active Pending Work)
> **Tier 2 | Updated:** 2026-04-16 19:36 CLT
> Single source of truth for ALL pending work. No history — completed items go to execution_tracker.md.

---

## §1 — Open Bugs

| ID | Severity | Description | Status |
|:---|:---|:---|:---|
| BUG-8 | P2 | Desktop cursor tracking on deployed site (CF Workers) — mouse not tracked by Vortex after deploy | Investigate CSP/pointer-events |
| BUG-9 | P2 | Sandbox chat "Enviar Prueba" — `test_feedback` may need `tenant_id` column check on DEV | Verify schema |
| ~~BUG-10~~ | ~~P1~~ | ~~Sandbox "Reiniciar" button not working — `confirm()` blocked by Edge runtime~~ | ~~✅ FIXED `3915990`~~ |

---

## §2 — Active Sprint (Block X — Stabilization Close-Out)

| ID | Priority | Task | Status |
|:---|:---|:---|:---|
| X-1 | 🔴 | Verify Reiniciar button works after deploy (React inline confirmation) | ✅ User verified |
| X-2 | 🔴 | Configure `SENTRY_AUTH_TOKEN` as **Build Secret** in CF Workers Builds dashboard | ✅ User configured |
| X-3 | 🟡 | 3-way isolation re-test (Superadmin vs Jose Mancilla vs CasaVitaCure) | ✅ Passed |
| X-4 | 🟡 | PROD migration gate — present schema diff, await approval | ✅ Applied 6 groups |
| X-5 | 🟡 | `NEXT_PUBLIC_*` vars as **Build Secrets** in CF dashboard (for build-time inlining) | ✅ User configured (dev+prod) |
| X-6 | 🟢 | Append session results to execution_tracker.md | ✅ Done |

---

## §3 — Next Sprint (Sprint 2 — Product Expansion)

| ID | Priority | Feature | Notes |
|:---|:---|:---|:---|
| S2-1 | 🔴 | WhatsApp pipeline → Responses API migration | Proven via onboarding agent |
| S2-2 | 🔴 | Instagram DM integration | Major selling point |
| S2-3 | 🔴 | Multi-squad booking engine | Major selling point |
| S2-4 | 🔴 | Dashboard MVP (real charts, KPIs) | Replace mock data |
| S2-5 | 🟡 | Gemini adapter real (google-genai SDK) | Replace mock |
| S2-6 | 🟡 | Credits/billing system | Revenue gate |
| S2-7 | 🟡 | SuperAdmin panel | Ops tooling |

---

## §4 — Technical Debt

| ID | Item | Priority |
|:---|:---|:---|
| TD-1 | `google-generativeai` → `google-genai` (FutureWarning on startup) | Low |
| TD-2 | `reportes/` and `finops/` pages are mock data | Medium |
| TD-3 | `admin-feedback/` QA pipeline improvements | Low |
| TD-4 | `gpt-5.4-mini` model name validation against latest OpenAI API | Medium |
| TD-5 | Tektur font loads per-component — consider global via layout.tsx | Low |
| TD-6 | `_provision_services_and_resources` full path (from onboarding data) not yet tested end-to-end — fallback always fires for reset users | High |
| TD-7 | **Migrate tenant resolution to JWT `app_metadata` claims** — see details below | High |
| TD-8 | **Env Var Architecture audit** — Ensure `NEXT_PUBLIC_*` vars are in CF Build Secrets (build-time inlining) AND wrangler.toml `[vars]` (runtime). Currently only in `[vars]`. | Medium |

### TD-7: Tenant Resolution via JWT `app_metadata` (Performance + Security)

**Current state:** Config page (and future standalone pages) resolve tenant via 3 sequential queries:
`auth.getUser()` → `tenant_users` table → `tenants` table. Pages inside `(panel)` use `TenantContext`
which also queries `tenant_users` on mount.

**Target state (Supabase-recommended):** Inject `tenant_id` into user's `app_metadata` during onboarding
via `supabase.auth.admin.updateUserById()`. This makes `tenant_id` available directly in the JWT,
eliminating the `tenant_users` lookup on every page load and enabling faster RLS policies.

**Implementation steps:**
1. During onboarding (`_provision_services_and_resources`), call:
   ```js
   await supabase.auth.admin.updateUserById(userId, {
     app_metadata: { tenant_id: newTenantId }
   })
   ```
2. Update `TenantContext.tsx` to read `user.app_metadata.tenant_id` as primary source.
3. Update RLS policies from `get_my_tenant_id()` subquery to direct JWT claim:
   ```sql
   USING (tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid)
   ```
4. Keep `tenant_users` table as source of truth for multi-tenant membership (superadmin).
5. For superadmin tenant switching, use Custom Access Token Hook to override the claim.

**Why:**
- Eliminates 1 query per page load per user (the `tenant_users` lookup)
- RLS policies run faster (JWT claim read vs. subquery on every row check)
- Aligns with Supabase's official recommended multi-tenant pattern
- `app_metadata` is server-side only — users CANNOT tamper with it (unlike `user_metadata`)

**Official Supabase references:**
- [User Management (app_metadata vs user_metadata)](https://supabase.com/docs/guides/auth/managing-user-data)
- [Custom Claims & RBAC](https://supabase.com/docs/guides/api/custom-claims-and-role-based-access-control-rbac)
- [JWT Claims Reference](https://supabase.com/docs/guides/auth/jwt-fields)
- [Custom Access Token Hook](https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook)
- [SSR Auth with Next.js](https://supabase.com/docs/guides/auth/server-side/nextjs)

### TD-8: Env Var Architecture (Build-Time vs Runtime)

**Current state:** `NEXT_PUBLIC_*` vars are in `wrangler.toml [vars]` (runtime only).
Per OpenNext docs, they ALSO need to be in CF Workers Builds "Build variables and secrets"
for Next.js to inline them into the client bundle at build time.

**Target state:** Same vars in BOTH places — wrangler.toml for runtime, CF Build Secrets for build-time.

**Official references:**
- [OpenNext Env Vars](https://opennext.js.org/cloudflare/howtos/env-vars)
- [CF Workers Build Config](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)
- [CF Environment Variables](https://developers.cloudflare.com/workers/configuration/environment-variables/)

---

## §5 — PROD Migration Gate (✅ ALL APPLIED — 2026-04-16 20:00 CLT)

| Migration | Tables Affected | DEV | PROD |
|:---|:---|:---|:---|
| Onboarding schema | tenant_onboarding, onboarding_messages | ✅ | ✅ |
| Native calendar schema | resources, appointments, scheduling_config, tenant_services | ✅ | ✅ |
| Profiles table | profiles | ✅ | ✅ |
| tenants ALTER | ws_phone_id, ws_token, system_prompt → nullable | ✅ | ✅ |
| tenant_users ALTER | role, created_at columns added | ✅ | ✅ |
| Functions | is_superadmin, get_my_tenant_id, handle_new_user | ✅ | ✅ |
| Superadmin RLS | All 13 tables | ✅ | ✅ |
| Profile backfill | tomasgemes=superadmin, instagramelectrimax=admin | ✅ | ✅ |

> `is_setup_complete` on tenants: ✅ PROD already applied (emergency fix earlier today).

> **Data preservation verified:** 1 tenant, 7 contacts, 122 messages, 12 alerts, 41 test_feedback — all intact.

---

## §6 — Key References

| Doc | Purpose |
|:---|:---|
| [NOW.md](NOW.md) | Current session state (Tier 1) |
| [execution_tracker.md](execution_tracker.md) | Permanent history log (Tier 3) |
| [master_plan.md](master_plan.md) | Strategic north star (Tier 4) |
| [README.md](../README.md) | Technical documentation |
| [OpenNext Env Vars](https://opennext.js.org/cloudflare/howtos/env-vars) | Cloudflare env var architecture |
| [Sentry Next.js Setup](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/) | Sentry configuration |
