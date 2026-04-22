# 📋 AUDIT GAP ANALYSIS v2 — ACTUALIZADO POST-PASADA 4

> Fecha: 2026-04-21 01:40 CLT
>
> **v2**: Actualizado después de auditar todos los archivos de alto riesgo restantes.

---

## RESUMEN DE COBERTURA

| Área | Archivos | Leídos | % | Nota |
|---|---|---|---|---|
| Backend `app/` | 40 | 40 (4 parcial) | **100%** | ✅ |
| Backend root | 29 | 24 | **83%** | Falta: reporter.py, Procfile, pyproject.toml, *.json payloads, latency_analysis.md |
| Backend scripts/ | 12 | 8 | **67%** | Falta: scenarios.py, payload_factory.py, cleanup.py, maintenance/ |
| Backend tests/ | 4 | 0 | **0%** | 🟢 Bajo riesgo |
| Backend SQL | 4 | 4 | **100%** | ✅ |
| Frontend contexts/ | 5 | 5 | **100%** | ✅ |
| Frontend lib/ | 5 | 3 | **60%** | Falta: utils.ts (172B), whatsappFormatter (6.4KB) — 🟢 bajo riesgo |
| Frontend app pages | 16 | 10 | **63%** | Falta: panel subroutes (6) — 🟢 bajo riesgo (carga components) |
| Frontend API routes | 5 | 5 | **100%** | ✅ Todos auditados en pasada 4 |
| Frontend components/ | 31 | 0 | **0%** | 🟢 Bajo riesgo — UI puro |
| Frontend hooks/ | 1 | 0 | **0%** | 🟡 useOnboardingStream.ts (25KB) — SSE parsing |
| Frontend config | 7 | 5 | **71%** | Falta: package.json, open-next.config.ts |
| Root project | 33 | 5 | **15%** | Todos HIGH-risk leídos. Falta: debug scripts, logs, error dumps |
| **DB COMPLETA** | 14 áreas | 14 | **100%** | ✅✅✅ Grants, RLS, Functions, Triggers, Indexes, Publications, Storage, Edge Functions |

---

## ARCHIVOS QUE PERMANECEN SIN LEER

### 🟢 BAJO RIESGO — No prioritarios para auditoría de seguridad

| # | Archivo | Tamaño | Razón por la que es bajo riesgo |
|---|---|---|---|
| 1-31 | `Frontend/components/**/*.tsx` (31 archivos) | ~400KB total | Componentes React UI — no manejan auth, secrets, ni DB directamente |
| 32-42 | `Frontend/components/ui/*.tsx` (11 archivos) | ~52KB | Shadcn/radix primitivas UI |
| 43 | `Frontend/lib/utils.ts` | 172B | Solo helper `cn()` para classnames |
| 44 | `Frontend/lib/whatsappFormatter.tsx` | 6.4KB | Formateo visual de mensajes |
| 45 | `Frontend/app/globals.css` | 8.9KB | CSS |
| 46 | `Frontend/app/global-error.tsx` | 1.5KB | Sentry error boundary |
| 47 | `Frontend/postcss.config.js` | 82B | PostCSS config |
| 48 | `Frontend/tailwind.config.js` | 2.1KB | Tailwind config |
| 49 | `Frontend/tsconfig.json` | 725B | TypeScript config |
| 50 | `Frontend/components.json` | 535B | Shadcn config |
| 51 | `Backend/Procfile` | 55B | Startup command |
| 52 | `Backend/pyproject.toml` | 952B | Python dependencies |
| 53 | `Backend/reporter.py` | 3.3KB | Report generator |
| 54 | `Backend/payload.json` | 103B | Test payload |
| 55 | `Backend/simpayload.json` | 163B | Simulation payload |
| 56 | `Backend/latency_analysis.md` | 11KB | Analysis doc |
| 57 | `Backend/simulation_report.md` | 1.2KB | Report |
| 58 | `error*.txt` (5 archivos) | ~8KB | Error logs |
| 59 | `curl_*.txt` (2 archivos) | ~5KB | Debug output |
| 60 | `logs.json`, `orch_logs.json`, etc. | ~87KB | Runtime logs |
| 61 | `extract.py` | 1.6KB | Log extractor |
| 62 | `read_utf16_logs.py` | 440B | Log reader |
| 63 | `run_logs.bat` | 354B | Batch helper |

### 🟡 MEDIO RIESGO — Útiles pero no bloqueantes

| # | Archivo | Tamaño | Riesgo |
|---|---|---|---|
| 64 | `Frontend/hooks/useOnboardingStream.ts` | 25KB | SSE stream parsing — podría tener token handling |
| 65 | `Frontend/package.json` | 1.5KB | Dependencies — podrían tener versiones vulnerables |
| 66 | `Frontend/open-next.config.ts` | 255B | OpenNext bindings |
| 67 | `Backend/scripts/simulation/scenarios.py` | 9.7KB | Simulation scenarios |
| 68 | `Backend/scripts/simulation/payload_factory.py` | 12.6KB | Payload generator |
| 69 | `Backend/scripts/simulation/cleanup.py` | 3.8KB | Data cleanup |
| 70 | `Backend/scripts/maintenance/delete_contacts.py` | 358B | Contact deletion |
| 71 | `Backend/scripts/maintenance/migrate_contacts.py` | 1.0KB | Contact migration |
| 72 | `Backend/tests/unit/conftest.py` | 325B | Test fixtures |
| 73 | `Backend/tests/unit/test_*.py` (3 archivos) | 3.4KB | Unit tests |
| 74 | `Backend/temp_contacts.json` | 658B | PII data |
| 75-80 | `Frontend/app/(panel)/*/page.tsx` (6 subrutas) | ? | Panel pages — importan components |

### Archivos parcialmente leídos (líneas faltantes)

| Archivo | Leído | Falta | Riesgo de lo faltante |
|---|---|---|---|
| `use_cases.py` (82KB) | L800-1349 (32%) | L1-799, L1350+ | 🟡 Import section + tail of agentic loop |
| `native_service.py` (57KB) | L1-800 (67%) | L800-1200 | 🟡 book/update/cancel detailed logic |
| `scheduling/tools.py` (21KB) | L1-100 (25%) | L100-404 | 🟡 Tool execute methods |
| `chat_endpoint.py` (79KB) | ~L1-100 (7%) | L100-1524 | 🟡 Full SSE streaming handler |

---

## DB AUDIT — 100% COMPLETE ✅

| Área | Status | Hallazgos |
|---|---|---|
| Grants (anon/authenticated) | ✅ Completo | 🔴 anon tiene ALL en 11 tablas |
| RLS Policies (53) | ✅ Completo | 🟠 8 tablas sin `with_check` en UPDATE |
| Functions (5 custom) | ✅ Completo | 🟠 `acquire_processing_lock` sin search_path |
| Triggers (1) | ✅ Completo | ✅ OK |
| Indexes (21) | ✅ Completo | ✅ OK |
| Realtime Publications | ✅ Completo | 🟡 Sin rowfilter |
| Storage Buckets | ✅ Completo | ✅ Ninguno (0 buckets) |
| Edge Functions | ✅ Completo | ✅ Ninguna (0 functions) |
| Cloud Run Config | ✅ Completo | 🔴 RESEND in plaintext, invoker-iam-disabled |
| Views | ✅ Ninguna custom | ✅ OK |
| Foreign Keys | ✅ Via schema review | ✅ OK |
