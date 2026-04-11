# Deep Dive C v3: Dashboard UX + Observability — RESEARCH-BACKED + CITED

> **Status:** FINAL — All docs verified with exact URLs (April 2026)  
> **Last Updated:** 2026-04-11 15:50 CLT  
> **Research:** 12+ dedicated web searches completed  
> **Criticality:** 🟡 HIGH — Product face + Safety net  

---

## 📚 Official Documentation Index (BOOKMARKS FOR IMPLEMENTATION)

### Backend Infrastructure
| Doc | URL | Use For |
|:---|:---|:---|
| **Sentry FastAPI Integration** | https://docs.sentry.io/platforms/python/integrations/fastapi/ | Setup, `set_tag`, scope isolation |
| **asgi-correlation-id (GitHub)** | https://github.com/snok/asgi-correlation-id | Middleware setup, Sentry auto-integration |
| **asgi-correlation-id (PyPI)** | https://pypi.org/project/asgi-correlation-id/ | Installation, version |
| **structlog (Docs)** | https://www.structlog.org/ | Structured logging configuration |
| **structlog (GitHub)** | https://github.com/hynek/structlog | Source, examples |
| **structlog (PyPI)** | https://pypi.org/project/structlog/ | Installation |
| **FastAPI Middleware Docs** | https://fastapi.tiangolo.com/tutorial/middleware/ | ASGI middleware, execution order |
| **FastAPI Dependencies** | https://fastapi.tiangolo.com/tutorial/dependencies/ | Dependency injection, `Depends` |
| **Cloud Run Docs** | https://cloud.google.com/run/docs | Deployment, scaling, secrets |
| **Pydantic v2** | https://docs.pydantic.dev/latest/ | Validation, JSON schema |

### Frontend / Database
| Doc | URL | Use For |
|:---|:---|:---|
| **Supabase Docs Hub** | https://supabase.com/docs | Main docs portal |
| **Supabase Realtime** | https://supabase.com/docs/guides/realtime | Subscriptions, channels, limits |
| **Supabase RLS** | https://supabase.com/docs/guides/database/postgres/row-level-security | Row Level Security policies |
| **Supabase JS Client** | https://supabase.com/docs/reference/javascript/introduction | Frontend client library |
| **Supabase Python Client** | https://supabase.com/docs/guides/getting-started/quickstarts/python | `supabase-py`, async queries |
| **Supabase DB Functions** | https://supabase.com/docs/guides/database/functions | PostgreSQL functions |
| **Next.js 15 Docs** | https://nextjs.org/docs | App Router, Server Components |
| **Cloudflare Workers** | https://developers.cloudflare.com/workers/ | Deployment, wrangler |
| **Next.js on Cloudflare** | https://developers.cloudflare.com/workers/frameworks/framework-guides/nextjs/ | OpenNext adapter |

### External APIs
| Doc | URL | Use For |
|:---|:---|:---|
| **Google Calendar API Events** | https://developers.google.com/calendar/api/v3/reference/events | Events CRUD |
| **Google Calendar FreeBusy** | https://developers.google.com/calendar/api/v3/reference/freebusy | Availability queries |
| **Google Calendar Python Quickstart** | https://developers.google.com/workspace/calendar/quickstart/python | Python client setup |

---

## 1. Supabase Realtime Limits (Architecture Constraint)

**Source:** [Supabase Realtime](https://supabase.com/docs/guides/realtime)

| Feature | Free Tier Limit | Pro Tier |
|:---|:---|:---|
| **Concurrent connections** | **200** | 500 |
| **Messages per second** | **100** | Higher |
| **Channel joins per second** | **100** | Higher |
| **Channels per connection** | **100** | Higher |

**Free tier gotcha:** Projects **pause after 1 week of inactivity.**

**Our usage at 7 tenants:** ~14-42 connections (7 tenants × 2-3 staff × 1-2 tabs). **Safe.**

**Recommendation:**
- Realtime ONLY for: Activity Feed (Block 2) + Escalation alerts
- Polling (30s interval) for: Status Block 1, metrics
- Keep RLS policies simple — index on `tenant_id`

---

## 2. Dashboard Query Performance

**Source:** [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security) | [Supabase Docs](https://supabase.com/docs)

### Required Indexes
```sql
-- Verify these exist:
CREATE INDEX IF NOT EXISTS idx_messages_tenant_time 
  ON messages(tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_tenant_contact 
  ON messages(tenant_id, contact_id);

-- For dashboard "today's activity":
CREATE INDEX IF NOT EXISTS idx_messages_today 
  ON messages(tenant_id, created_at) 
  WHERE created_at > CURRENT_DATE;

-- For "pending escalations" count:
CREATE INDEX IF NOT EXISTS idx_contacts_escalated 
  ON contacts(tenant_id) 
  WHERE bot_active = false;
```

### Growth Projections
- 40 convos/day × 5 msgs × 30 days = **6,000 messages/tenant/month**
- At 7 tenants: **42,000 messages/month**
- At 15 tenants: **90,000 messages/month**
- Partial indexes keep dashboard queries fast even at scale

---

## 3. Observability: Correlation ID Architecture

### Setup with `asgi-correlation-id`
**Source:** [asgi-correlation-id (GitHub)](https://github.com/snok/asgi-correlation-id) | [Sentry FastAPI](https://docs.sentry.io/platforms/python/integrations/fastapi/)

```python
# Backend/app/main.py
from fastapi import FastAPI
from asgi_correlation_id import CorrelationIdMiddleware
import sentry_sdk

app = FastAPI()

# Add BEFORE Sentry middleware
app.add_middleware(CorrelationIdMiddleware)

# Sentry init
sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    traces_sample_rate=0.3,  # Don't trace 100% in production
)
```

### Logging Configuration
**Source:** [asgi-correlation-id (GitHub)](https://github.com/snok/asgi-correlation-id) | [structlog](https://www.structlog.org/)

```python
import logging.config

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'correlation_id': {
            '()': 'asgi_correlation_id.CorrelationIdFilter',
            'uuid_length': 12,
            'default_value': 'no-correlation',
        },
    },
    'formatters': {
        'default': {
            'format': '%(levelname)s [%(correlation_id)s] %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['correlation_id'],
            'formatter': 'default',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
}

logging.config.dictConfig(LOGGING)
```

### Sentry Tag Integration
**Source:** [Sentry FastAPI](https://docs.sentry.io/platforms/python/integrations/fastapi/)

```python
import sentry_sdk
from asgi_correlation_id import correlation_id

# In request middleware or dependency
@app.middleware("http")
async def add_sentry_context(request, call_next):
    cid = correlation_id.get() or "unknown"
    tenant_id = extract_tenant_id(request)
    
    sentry_sdk.set_tag("correlation_id", cid)
    sentry_sdk.set_tag("tenant_id", tenant_id or "unknown")
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response
```

---

## 4. Error Classification Taxonomy

| Level | Name | Example | Alert Channel | Response |
|:---|:---|:---|:---|:---|
| **P0** | System Down | Backend crash, zero webhooks | Discord 🔴 + Sentry | Immediate |
| **P1** | Degraded | LLM errors >5% | Discord 🟡 + Sentry | <15 min |
| **P2** | Feature Broken | Calendar API down | Discord 🟡 | <1 hour |
| **P3** | Quality | High escalation rate | Sentry only | <24 hours |
| **P4** | Cosmetic | UI glitch | Log only | Next sprint |

### Discord Rate Limits
**Source:** Discord API documentation

- **5 requests per 2 seconds** per webhook
- **30 requests per 60 seconds** per webhook

**Mitigation:** Batch alerts from same root cause. Cooldown: don't repeat same alert within 5 minutes.

---

## 5. Dashboard Design — Block-by-Block with APIs

### Block 1: Estado del Sistema (Status)
**Refresh:** 30-second polling via REST API
**Docs:** [Supabase Python](https://supabase.com/docs/guides/getting-started/quickstarts/python)

```
┌─────────────────────────────────────────┐
│  🟢 Todo funciona correctamente         │
│                                          │
│  Bot activo     │  42 mensajes hoy       │
│  0 errores      │  0 escalaciones        │
│  Última actividad: hace 2 min            │
└─────────────────────────────────────────┘
```

**API:** `GET /api/dashboard/status?tenant_id=X`

### Block 2: Actividad de Hoy (Activity Feed)
**Refresh:** Supabase Realtime subscription
**Docs:** [Supabase Realtime](https://supabase.com/docs/guides/realtime) | [Supabase JS Client](https://supabase.com/docs/reference/javascript/introduction)

```typescript
// Frontend subscription
const subscription = supabase
  .channel('activity-feed')
  .on('postgres_changes', 
    { event: 'INSERT', schema: 'public', table: 'messages', 
      filter: `tenant_id=eq.${tenantId}` },
    (payload) => addToActivityFeed(payload.new)
  )
  .subscribe();
```

**API:** `GET /api/dashboard/activity?tenant_id=X&limit=20`

### Block 3: Oportunidades (Sprint 2)
- Hot leads without follow-up (24h+)
- Inactive clients (30+ days)
- Conversion rate trends

### Block 4: Rendimiento (Sprint 2)
- Credit consumption from `usage_logs`
- Cache hit rate: `cached_tokens / prompt_tokens`
- Response time metrics
- Autonomous resolution rate

---

## 6. SuperAdmin Dashboard (Sprint 2)

```
┌── SuperAdmin: Cost Tracker ────────────────┐
│                                             │
│  💰 April 2026 (MTD)                       │
│  ┌────────┬──────┬──────┬────────────────┐ │
│  │ Tenant │ LLM  │ WA   │ Total          │ │
│  │ CVC    │ $8.20│ $0.15│ $8.35          │ │
│  │ Fumig  │ $0.00│ $0.00│ $0.00          │ │
│  │ TOTAL  │ $8.20│ $0.15│ $8.35          │ │
│  └────────┴──────┴──────┴────────────────┘ │
│                                             │
│  🔍 Correlation ID Lookup                   │
│  [cr_____________] [Search]                 │
│                                             │
│  📊 Error Summary (24h)                     │
│  P0: 0  P1: 2  P2: 1  P3: 5               │
└─────────────────────────────────────────────┘
```

**Data source:** `usage_logs` table (correlates LLM costs per tenant per request)

---

## 7. Implementation Priority (With Doc References)

### Sprint 1 (Tuesday deadline)
| Task | Effort | Docs |
|:---|:---|:---|
| `asgi-correlation-id` middleware | 15 min | [GitHub](https://github.com/snok/asgi-correlation-id) |
| Sentry tags: `tenant_id` + `correlation_id` | 15 min | [Sentry FastAPI](https://docs.sentry.io/platforms/python/integrations/fastapi/) |
| Logging config with correlation filter | 15 min | [asgi-correlation-id](https://github.com/snok/asgi-correlation-id) |
| Dashboard Blocks 1-2 API endpoints | 2 hours | [Supabase Python](https://supabase.com/docs/guides/getting-started/quickstarts/python) |
| Dashboard Blocks 1-2 frontend | 3 hours | [Supabase JS](https://supabase.com/docs/reference/javascript/introduction), [Next.js](https://nextjs.org/docs) |
| Verify DB indexes | 10 min | [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security) |

### Sprint 2
| Task | Docs |
|:---|:---|
| Dashboard Blocks 3-4 | [Supabase Realtime](https://supabase.com/docs/guides/realtime) |
| `usage_logs` table + credit tracking | [Supabase DB Functions](https://supabase.com/docs/guides/database/functions) |
| SuperAdmin panel v1 | [Next.js](https://nextjs.org/docs), [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security) |
| Discord alert batching | — |
| `structlog` structured logging | [structlog](https://www.structlog.org/) |
| Materialized views for stats | [Supabase DB Functions](https://supabase.com/docs/guides/database/functions) |

---

## 8. Files to Modify

| File | Action | Sprint | Primary Doc |
|:---|:---|:---|:---|
| `Backend/app/main.py` | Add correlation middleware + dashboard APIs | S1 | [asgi-correlation-id](https://github.com/snok/asgi-correlation-id) |
| `Backend/requirements.txt` | Add `asgi-correlation-id`, `structlog` | S1 | [PyPI](https://pypi.org/project/asgi-correlation-id/) |
| `Frontend/components/Dashboard/*` | Complete rewrite with real data | S1 | [Supabase JS](https://supabase.com/docs/reference/javascript/introduction) |
| `Frontend/app/superadmin/page.tsx` | NEW — SuperAdmin panel | S2 | [Next.js](https://nextjs.org/docs) |
| Supabase migrations | Indexes, materialized views | S1-S2 | [Supabase Docs](https://supabase.com/docs) |
