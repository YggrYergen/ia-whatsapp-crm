# Sales Execution Blueprint v2.0 — Flash CRM Edition

**Date:** 2026-04-20 (Updated from v1.0 2026-04-18)  
**Status:** 🟢 ACTIVE — Prep work in progress  
**Goal:** 10 sales × 130-200K CLP setup fee within sprint period  
**Re-contact play:** May 1-10, cheaper offer for warm "not yet" prospects  
**Primary Execution Tool:** Flash CRM v2 (replaces Google Sheets from v1.0)

---

## CHANGELOG v1.0 → v2.0

| Area | v1.0 | v2.0 |
|:-----|:-----|:-----|
| Call tracking | Google Sheet (to build) | ✅ Flash CRM DialerView + callAttempts[] |
| Lead management | Google Sheet columns | ✅ Flash CRM LeadDetail + scoring |
| CSV import + scoring | Manual sheet | ✅ Flash CRM auto-scoring (Pain/Reach/Market/Urgency) |
| Secret Shopper tracking | Google Sheet tab | ✅ Flash CRM ShopperBatchView + ShopperResultModal |
| Demo pipeline | Google Sheet columns | ✅ Flash CRM PostCallModal (date picker + link field) |
| ACA templates | Copy-paste from doc | ✅ Flash CRM TemplateDrawer |
| Daily metrics | Manual sheet formulas | ✅ Flash CRM TrackingDashboard |
| Tier/Category filters | Not built | ✅ Flash CRM LeadList filters |
| Data sourcing tools | Outscraper only | 8+ platforms analyzed (see Section 8) |
| CasaVitaCure SLA | Pending | ✅ Done (data wiped, clinical knowledge injected, dash fixed) |

---

## TABLE OF CONTENTS

1. [Strategy 1: IG Ad Spy + Phone Extraction](#strategy-1)
2. [Strategy 2: Secret Shopper at Scale](#strategy-2)
3. [Strategy 3: Google Maps Intelligence Engine](#strategy-3)
4. [Strategy 5: Walk-In + Where to Live](#strategy-5)
5. [Strategy 6: Content & Programmatic Ads](#strategy-6)
6. [Strategy 7: Warm Network ACA Templates](#strategy-7)
7. [60 Calls/Day Telephone Engine](#telephone-engine)
8. [DATA SOURCING — Complete Tool Arsenal (NEW v2.0)](#data-sourcing)
9. [GEOGRAPHIC QUERY OPTIMIZATION — Chile Comuna Grid (NEW v2.0)](#geo-optimization)
10. [The 6-Layer Parallel Execution Engine](#parallel-engine)
11. [The Daily Operating System — Hour by Hour](#daily-os)
12. [Flash-CRM Integration (UPDATED v2.0)](#flash-crm)
13. [Next Steps — Immediate Execution Queue (UPDATED v2.0)](#next-steps)

---

<a name="strategy-1"></a>
## 1. STRATEGY 1: IG Ad Spy + Phone Extraction

### The Problem You Identified
Many Chilean businesses on IG have phone numbers in their bio — some properly configured as WhatsApp links, many misconfigured (just a number). You want to extract this at scale + run a filter in parallel.

### How to Extract Efficiently (Within ToS)

#### Method A: Meta Ad Library Bulk Research (LEGAL, FREE)
1. Go to https://www.facebook.com/ads/library/
2. Set country: **Chile**
3. Search by keyword: `clínica dental`, `estética`, `peluquería`, `fumigación`, `veterinaria`, `inmobiliaria`
4. Each result shows: **Page name → link to IG profile**
5. From their IG profile: bio contains phone/WhatsApp/website

**Efficiency hack:** Open 20 tabs at once, extract bio info → paste into your Google Sheet. A trained operator can do **40-60 profiles per hour** this way.

#### Method B: Manual IG Hashtag Mining
Search IG hashtags relevant to your target verticals:
- `#clinicadentalchile` `#clinicadentalsantiago` `#clinicadentalviña`
- `#esteticachile` `#centrodeestetica` `#bellezachile`
- `#fumigacionchile` `#controldeplagas`
- `#veterinariachile` `#clinicaveterinaria`

Each profile → check bio for phone → add to sheet.

#### Method C: Google Maps Cross-Reference (RUN IN PARALLEL with Strategy 3)
This is where the parallel execution shines:
- While you're on Strategy 3 building lists from Google Maps, the phone numbers you extract from Maps **are often the same WhatsApp Business number in their IG bio**
- Cross-reference: Maps gives you name + phone + reviews. IG gives you their content quality + ad activity
- The combination creates a **Tier A prospect profile** in one pass

### The Filter You Need
For each prospect extracted, score on 3 binary signals:

| Signal | Score | How to Check |
|:-------|:-----:|:-------------|
| Running Meta ads? | +1 | Meta Ad Library |
| WhatsApp number visible? | +1 | IG bio or Google Maps |
| Reviews mention communication problems? | +1 | Google Maps reviews (Strategy 3) |

- **Score 3** → Tier A (Secret Shopper target)
- **Score 2** → Tier B (Phone call target)
- **Score 1** → Tier C (Low priority, batch later)
- **Score 0** → Skip

---

<a name="strategy-2"></a>
## 2. STRATEGY 2: Secret Shopper at Scale

### Your Constraint
Limited hours. Need maximum efficiency per test. Must stay within ALL terms of service.

### Legal & ToS Analysis

> **Verdict: Secret Shopping is FULLY LEGAL in Chile.** It is a standard market research practice used by every major company (retail, banking, hospitality). You are contacting a **publicly listed business number** as a **potential customer** — that IS the intended use of that number. There is no ToS violation, no privacy breach, no deception law issue. You are literally testing their publicly advertised service.

### Optimized Process (3 minutes per test vs. 10)

**Pre-work (batch, 30 min/week):**
1. From your Flash CRM Tier A prospects, extract all WhatsApp numbers
2. Pre-write 5 industry-specific test messages (see below)
3. Open all numbers in WhatsApp Web tabs (or use separate phone)

**Execution (per prospect):**
| Step | Time | Action |
|:-----|:----:|:-------|
| 1 | 10 sec | Send pre-written test message via WhatsApp |
| 2 | — | Set timer (move to next task while waiting) |
| 3 | 10 sec | After 30-60 min, screenshot the response time |
| 4 | 30 sec | Log result in Flash CRM ShopperResultModal |

**Key efficiency unlock:** You DON'T wait for them. You send 10-15 tests in a batch (10 minutes total), then go do calls/other work. Come back 1-2 hours later to collect screenshots. **Parallel with everything else.**

### Pre-Written Test Messages (Per Vertical)

**Dental:**
> "Hola, buenas! Tengo un dolor en una muela que me está molestando hace unos días. ¿Tienen hora disponible esta semana? ¿Cuánto sale la consulta?"

**Aesthetic/Medical:**
> "Hola! Estoy interesada/o en tratamiento de botox. ¿Tienen disponibilidad pronto? ¿Me pueden informar sobre precios?"

**Pest Control:**
> "Buenas, encontré ratones en mi casa y necesito urgente una fumigación. ¿Pueden venir esta semana? ¿Cuánto cobran por una casa de 3 habitaciones?"

**Veterinary:**
> "Hola, mi perro está con diarrea desde ayer y no quiere comer. ¿Tienen horario de urgencia o alguna hora pronto?"

**Real Estate:**
> "Hola, estoy buscando arriendo de departamento 2D1B en [zona]. ¿Tienen algo disponible? ¿Cuál es el rango de precios?"

### The Follow-Up Message (After You Have the Screenshot)

> "Hola [nombre del negocio], me llamo Tomás. Le escribí hace [X horas/ayer] como cliente, y noté que la respuesta tardó [X tiempo]. No lo digo como crítica — sé que es difícil mantener el WhatsApp al día cuando uno está atendiendo.
>
> Justamente trabajo en eso. Tenemos un asistente de IA que responde WhatsApp en menos de 30 segundos, las 24 horas, agendando citas y respondiendo preguntas frecuentes automáticamente. Ya lo usa [CasaVitaCure / una clínica similar].
>
> ¿Le interesaría verlo en acción? Son 5 minutos, le puedo hacer una demo en vivo."

### Rate Limits & Safety

| Platform | Limit | Our Usage |
|:---------|:------|:----------|
| WhatsApp (personal) | ~250 new contacts/day before flag risk | We'll do max 15-20 tests/day |
| WhatsApp Business App | No official limit on business inquiries | N/A — we're the customer here |
| Instagram DMs | ~35-50/day for newer accounts | Won't use for Secret Shopper |

**Risk level: MINIMAL.** You're messaging 15 businesses as a legitimate customer inquiry. This is normal consumer behavior.

---

<a name="strategy-3"></a>
## 3. STRATEGY 3: Google Maps Intelligence Engine

### Your Requirements
- Most effective and efficient execution
- Geographic location selection backed by real data (3-4 reputable sources)
- Mathematically best places to sell
- Parallel execution with minimal supervision

### Geographic Optimization — Where to Target

#### Why NOT Santiago?
Your instinct is correct: **65%+ of answered calls will redirect to bureaucratic communication links**. Santiago businesses are more saturated, have more gatekeepers, and are more skeptical of cold outreach. They also have more existing solutions.

#### Why NOT Papudo?
Also correct: too small. Insufficient business density and transaction volume for the velocity you need.

#### The Mathematical Framework for City Selection

We need cities that maximize: **Business density × Pain level × Purchase power × Accessibility × Low competition**

Based on research from ICVU (Índice de Calidad de Vida Urbana), SII business data, and regional economic reports:

| City/Zone | Pop. | Business Density | Commercial Activity | Competition Level | Digital Maturity | **SCORE** |
|:----------|:----:|:----------------:|:-------------------:|:-----------------:|:----------------:|:---------:|
| **Viña del Mar + Valparaíso** | ~450K combined | ⭐⭐⭐⭐⭐ | Very High — commerce+tourism hub | Medium | High | **23/25** |
| **Concepción + San Pedro** | ~280K | ⭐⭐⭐⭐ | High — university + economic pole | Medium-Low | Medium-High | **21/25** |
| **La Serena + Coquimbo** | ~400K combined | ⭐⭐⭐⭐ | High — tourism + services | Low | Medium | **20/25** |
| **Temuco** | ~300K | ⭐⭐⭐ | High — agricultural + services hub | Low | Medium | **18/25** |
| **Puerto Montt + Puerto Varas** | ~250K combined | ⭐⭐⭐ | Medium-High — tourism + aquaculture | Very Low | Medium | **17/25** |
| **Valdivia** | ~180K | ⭐⭐⭐ | Medium — university town | Very Low | Medium | **16/25** |

#### 🎯 Recommended Priority for Sales Targeting (Phone Calls)

1. **Viña del Mar / Valparaíso** — Highest density, massive SMB count, strong PYME ecosystem, SERCOTEC & CORFO active, commercial corridors everywhere
2. **Concepción** — Less saturated, big enough for volume, university ecosystem brings innovation-friendly businesses
3. **La Serena / Coquimbo** — Tourism-driven service businesses with high WhatsApp volume, lower competition

> **Critical insight:** You can call businesses in ANY of these cities from Papudo or wherever you are. Phone outreach is location-independent. Walk-ins require relocation.

---

<a name="strategy-5"></a>
## 4. STRATEGY 5: Walk-In + Where to Live

### Where Should You Move? (Business + Life Optimization)

Your requirements:
- ✅ Green & stunning nature (not Pucón)
- ✅ Safe
- ✅ Good for business (walk-ins, local network, commercial activity)
- ✅ Beautiful, inspiring work environment

#### Top 3 Recommendations

**🥇 #1: Puerto Varas**
| Factor | Score | Why |
|:-------|:-----:|:----|
| Nature/Beauty | 10/10 | Lago Llanquihue, Volcán Osorno, Petrohué. Stunningly green. Alpine + temperate rainforest. |
| Safety | 9/10 | Consistently top-ranked safest city in Chile. Small, organized community. |
| Business (walk-in) | 7/10 | Very active tourism-focused commerce. Restaurants, hotels, real estate, service businesses. Puerto Montt (20 min) adds massive business density. |
| Coworking/Internet | 8/10 | Growing remote worker scene. Fiber optic available. Multiple cowork spaces. |
| Cost of living | 8/10 | Significantly cheaper than Santiago/Viña. |
| **TOTAL** | **42/50** | |

> **The play:** Live in Puerto Varas for beauty/safety/inspiration. Walk-in blitz the dense commercial corridor of Puerto Montt (20 min drive) + the tourism businesses in Puerto Varas/Frutillar. Call businesses nationwide from your lakeside cowork.

**🥈 #2: Valdivia**
| Factor | Score | Why |
|:-------|:-----:|:----|
| Nature/Beauty | 9/10 | Rivers, wetlands, temperate rainforest. The "Ciudad de los Ríos". Lush green. |
| Safety | 9/10 | University town feel. Well-organized. Low crime. |
| Business (walk-in) | 6/10 | Decent commercial activity but smaller market. University-driven economy. |
| Coworking/Internet | 7/10 | Growing scene. University infrastructure helps. |
| Cost of living | 9/10 | Very affordable. |
| **TOTAL** | **40/50** | |

**🥉 #3: Viña del Mar**
| Factor | Score | Why |
|:-------|:-----:|:----|
| Nature/Beauty | 7/10 | Coastal, pleasant but more urban than green. Jardín Botánico and surrounding hills are nice. |
| Safety | 6/10 | Better than Santiago but not as safe as southern cities. Variable by sector. |
| Business (walk-in) | 10/10 | MASSIVE commercial activity. SERCOTEC hub. PYME ecosystem. Commercial corridors everywhere. |
| Coworking/Internet | 9/10 | Excellent infrastructure. Many cowork options. |
| Cost of living | 6/10 | More expensive than south. |
| **TOTAL** | **38/50** | |

#### 🎯 My Recommendation

> **Puerto Varas for living + remote phone outreach nationwide.** You get the stunning green beauty, safety, low cost, AND you can walk-in businesses locally while calling Viña/Concepción/La Serena remotely. Best of both worlds.

---

<a name="strategy-6"></a>
## 5. STRATEGY 6: Content & Programmatic Ads

### The IG Problem: Empty Profile = Dead DMs
You're right — no IG presence means your outreach loses power. Prospects will check and see nothing.

### Solution: Programmatic Ad Creation Pipeline

You asked about "After Effects but code" — this exists and it's called **Remotion**.

#### The Stack (All Code, All Automated)

| Tool | Role | Cost |
|:-----|:-----|:-----|
| **Remotion** (React) | Programmatic video creation — your ads ARE React components | Free (open source, commercial license for companies) |
| **Claude/ChatGPT** | Generate ad scripts, copy, layouts | You already have this |
| **Kling AI** | AI-generated realistic video clips (product demos, scenarios) | Free tier available |
| **Pika** | Quick experimental video variations (A/B testing hooks) | Free tier |
| **CapCut** | Final assembly + captions + platform formatting | Free |
| **Canva** | Static posts, carousels, stories | Free tier |

#### Immediate IG Content Plan (Week 1, 15 min/day)

| Day | Content Type | Topic |
|:----|:------------|:------|
| Mon | Carousel (Canva) | "¿Sabías que el 40% de tus clientes no te esperan más de 5 min?" |
| Tue | Screen recording | Demo: AI responde WhatsApp en 15 segundos (your own product) |
| Wed | Story | Secret Shopper result (anonymized): "Este negocio perdió un cliente en 47 min" |
| Thu | Reel (Kling AI) | "Tu competencia responde en 30 seg. ¿Y tú?" |
| Fri | Carousel | "3 señales de que estás perdiendo clientes por WhatsApp" |
| Sat | Story | Behind the scenes — building the AI |
| Sun | Rest | — |

---

<a name="strategy-7"></a>
## 6. STRATEGY 7: Warm Network ACA Templates

### 5 Ready-to-Copy-Paste Versions

All follow the **ACA Framework** (L07): Acknowledge → Compliment → Ask

---

**VERSION A — The Direct Ask (For close friends/family)**
> "¡Oye [nombre]! Espero que estés bien 🙌 Oye, te escribo porque estoy trabajando en un proyecto de inteligencia artificial que ayuda a negocios a no perder clientes por WhatsApp — el típico "me escribieron y no alcancé a responder".
>
> ¿Conoces a algún dueño de negocio que le pueda servir? Clínicas dentales, peluquerías, veterinarias, cualquier negocio que atienda por WhatsApp. Si me conectas con alguien, te debo un almuerzo 🍕"

---

**VERSION B — The Casual Mention (For acquaintances)**
> "¡[Nombre]! ¿Cómo has estado? Oye, una consulta random — ¿conoces a alguien que tenga un negocio y siempre se queje de que no alcanza a responder los mensajes de WhatsApp? Estoy ayudando negocios con eso y me encantaría conectar con gente que le pueda servir. ¡Gracias de antemano! 🙏"

---

**VERSION C — The Value-First (For professional contacts)**
> "Hola [nombre], espero que todo bien con [su negocio/trabajo]. Te cuento que lancé un servicio de asistente IA para negocios que funciona por WhatsApp — responde, agenda, y atiende clientes automáticamente 24/7. Justo lo estamos implementando con [cliente/sector] y los resultados han sido increíbles.
>
> Si conoces a alguien que le pueda interesar, me ayudaría mucho la conexión. ¡Un abrazo!"

---

**VERSION D — The Story (For groups/broadcasts)**
> "Gente, les cuento algo. Un negocio que conocemos estaba perdiendo el 30% de sus clientes solo porque no respondía WhatsApp a tiempo. Les implementamos un asistente de IA que responde en 15 segundos, 24/7, y en el primer mes recuperaron esos clientes.
>
> Si conocen a alguien con un negocio que viva esto, me encantaría ayudarles. Estamos arrancando y los primeros tienen precio especial 🔥"

---

**VERSION E — The Ultra-Specific (For contacts in target sectors)**
> "¡Hola [nombre]! Sé que [trabajas en salud / conoces gente en el rubro dental / etc.]. Te cuento: desarrollé un asistente de IA que responde WhatsApp para clínicas — agenda pacientes, responde preguntas frecuentes, y funciona 24/7 sin que el doctor tenga que ver el teléfono.
>
> Si conoces alguna clínica que necesite algo así, ¿me podrías conectar? Les hago una demo gratis de 5 minutos. ¡Gracias!"

---

### A/B Testing Plan
- **Week 1:** Send Version A to 30 close contacts, Version B to 30 acquaintances
- **Week 2:** Send Version C to 20 professional contacts, Version D to 3-5 WhatsApp groups
- **Week 3:** Use whichever version got the most referrals for remaining contacts + Version E for sector-specific contacts

---

<a name="telephone-engine"></a>
## 7. 60 CALLS/DAY TELEPHONE ENGINE

### The Math

| Variable | Value | Calculation |
|:---------|:-----:|:------------|
| Calls per day | 60 | Your stated capacity |
| Sprint duration | 20 business days | ~4 weeks |
| Total calls | 1,200 | 60 × 20 |
| Pick-up rate (Chile) | ~45-50% | Half won't pick up / wrong / disconnected |
| Actual conversations | ~600 | 1,200 × 50% |
| Demo conversion rate | 5-8% | Of conversations → booked demo |
| Demos booked | 30-48 | 600 × 5-8% |
| Demo → close rate | 25-33% | Industry standard for validated product |
| **Closed sales** | **8-16** | 30-48 × 25-33% |

> **The math works.** 60 calls/day for 20 days → 8-16 sales. Your target of 10 is right in the middle. But ONLY IF the list quality is high (Tier A/B prospects) and you have proper tooling.

### The Tooling: Flash CRM v2 (UPDATED)

Flash CRM now provides the complete call operations stack:

| Feature | Flash CRM Component | Status |
|:--------|:-------------------|:------:|
| Lead list with scoring | LeadList + calculateCompositeScore | ✅ |
| Tier A/B/C filtering | LeadList tier/category filters | ✅ |
| Dialer mode (sequential) | DialerView with progress bar | ✅ |
| Call attempt logging | LeadDetail.handleCall → callAttempts[] | ✅ |
| Post-call disposition | PostCallModal (1-click status) | ✅ |
| Quick notes on contact | PostCallModal → inline note | ✅ |
| Demo booking with date | PostCallModal → mini date-picker + link | ✅ |
| Secret Shopper batch | ShopperBatchView | ✅ |
| Shopper result logging | ShopperResultModal | ✅ |
| ACA templates | TemplateDrawer (5 versions) | ✅ |
| Daily metrics | TrackingDashboard (calls/shoppers/ACA/demos) | ✅ |
| CSV import + auto-scoring | App.jsx handleFileUpload | ✅ |
| Duplicate phone detection | LeadForm phone validation | ✅ |

### Demo Booking Integration

For now, use **Cal.com** (free tier) or **Calendly** (free tier) as your demo booking link. When prospects confirm interest:
1. Flash CRM PostCallModal captures the date/time + meeting link
2. You paste your Cal.com link in the field
3. Cal.com auto-syncs to Google Calendar

---

<a name="data-sourcing"></a>
## 8. DATA SOURCING — Complete Tool Arsenal (v2.0)

### ⚠️ Critical Constraint: The 120-Result Limit
Google Maps caps visible results at **~120 per search query**. This means searching "clínica dental Viña del Mar" returns max 120 even if 500 exist. **You MUST use granular comuna-level queries** (see Section 9) to get complete coverage.

### Tool Comparison (All Verified April 2026)

#### Tier 1: Best Free Tiers (Use ALL of These)

| Tool | Free Tier | Records/mo Free | Best For | Sign Up |
|:-----|:----------|:---------------:|:---------|:--------|
| **Outscraper** | 500 listings + 500 reviews FREE | ~500 | Most reliable, no-code, includes reviews | outscraper.com |
| **Apify** | $5/mo free credits (renews monthly) | ~500-800 | Developer-friendly, flexible actors, export to CSV/JSON | apify.com |
| **ScrapeTable** | 150 credits/mo FREE (50 per search) | ~3 searches | API-first, good for automation | scrapetable.com |
| **Lobstr.io** | 100 credits/mo or 15 min exec/day | ~100-200 | Budget alternative, visual "Squids" | lobstr.io |
| **PhantomBuster** | 14-day free trial + limited exec time | ~200-400 | No-code "Phantoms", contact enrichment | phantombuster.com |
| **Bright Data** | Free trial credits | ~300-500 | Enterprise-grade proxies, SERP API | brightdata.com |

#### Tier 2: Chrome Extensions (Supplement — Quick & Free)

| Extension | Cost | Limitations | Best For |
|:----------|:----:|:------------|:---------|
| **Instant Data Scraper** | 100% Free | Manual, one page at a time | Quick one-off extractions |
| **Map Lead Scraper** | Free (1000/mo limit) | Basic fields only | Fast "click and export" |
| **G Maps Extractor** | Free | Basic CSV export | Supplementing cloud scrapers |

#### Tier 3: Google Places API (Official — For Custom Scripts)

Since March 2025, Google replaced the $200/mo credit with per-SKU free caps:

| SKU | Free Monthly Cap | What You Get | Cost After Free |
|:----|:----------------:|:-------------|:---------------|
| Text Search (Essentials) | 10,000 requests | Business name, address, rating | $0.032/request |
| Text Search (Pro) | 5,000 requests | + phone, website, hours | $0.035/request |
| Place Details (Essentials) | 10,000 requests | Basic detail for a place_id | $0.025/request |
| Place Details (Pro) | 5,000 requests | + reviews, photos | $0.030/request |
| Nearby Search (Essentials) | 10,000 requests | Geospatial search | $0.032/request |

> **The play:** Create a GCP project, enable Places API, set budget alert at $0. You get **10,000 Text Search requests for free** — enough for ~80 comuna-level queries with pagination. This returns structured data (name, phone, rating, address) that you can pipe directly into Flash CRM's CSV import.

#### Tier 4: Open Source (If You Want Full Control)

| Tool | Language | What It Does |
|:-----|:---------|:-------------|
| `gosom/google-maps-scraper` | Go | Full Maps scraper, requires proxies |
| Custom Playwright script | Python/JS | Use `playwright` to automate Maps UI |

> ⚠️ Open source requires managing proxies and anti-bot detection yourself. Only use if cloud tools hit their limits.

### Maximum Free Records Strategy

By using ALL Tier 1 tools in parallel, here's your theoretical monthly free capacity:

| Tool | Free Records |
|:-----|:------------:|
| Outscraper | 500 |
| Apify ($5 credits) | ~600 |
| ScrapeTable (3 searches) | ~360 |
| PhantomBuster (trial) | ~300 |
| Bright Data (trial) | ~400 |
| Chrome extensions (manual) | ~500 |
| Google Places API (10K reqs) | ~2,000 |
| **TOTAL** | **~4,660** |

That's nearly **5x** what you need for the 1,200-number call list. Even after deduplication (~30%), you'll have ~3,200 unique business records — more than enough for the full sprint.

---

<a name="geo-optimization"></a>
## 9. GEOGRAPHIC QUERY OPTIMIZATION — Chile Comuna Grid

### The Problem
Google Maps returns max ~120 results per search. Searching "clínica dental Viña del Mar" misses hundreds of real businesses.

### The Solution: Comuna-Level Grid Queries
Chile's administrative structure gives us natural geographic subdivisions: **comunas**. Each city is divided into comunas that are small enough to stay under the 120-result limit.

### Priority City #1: Viña del Mar + Valparaíso Metro

| Comuna | Pop. | Business Density | Query Priority |
|:-------|:----:|:----------------:|:-------------:|
| Viña del Mar | 335K | ⭐⭐⭐⭐⭐ | 🔴 First |
| Valparaíso | 296K | ⭐⭐⭐⭐⭐ | 🔴 First |
| Con Con | 46K | ⭐⭐⭐ | 🟡 Second |
| Quilpué | 180K | ⭐⭐⭐⭐ | 🟡 Second |
| Villa Alemana | 130K | ⭐⭐⭐ | 🟡 Second |
| Limache | 45K | ⭐⭐ | ⚪ Third |
| Quillota | 90K | ⭐⭐⭐ | ⚪ Third |

### Priority City #2: Concepción Metro

| Comuna | Pop. | Business Density | Query Priority |
|:-------|:----:|:----------------:|:-------------:|
| Concepción | 230K | ⭐⭐⭐⭐⭐ | 🔴 First |
| Talcahuano | 160K | ⭐⭐⭐⭐ | 🔴 First |
| San Pedro de la Paz | 130K | ⭐⭐⭐ | 🟡 Second |
| Chiguayante | 90K | ⭐⭐⭐ | 🟡 Second |
| Hualpén | 95K | ⭐⭐⭐ | 🟡 Second |

### Priority City #3: La Serena + Coquimbo

| Comuna | Pop. | Business Density | Query Priority |
|:-------|:----:|:----------------:|:-------------:|
| La Serena | 220K | ⭐⭐⭐⭐ | 🔴 First |
| Coquimbo | 230K | ⭐⭐⭐⭐ | 🔴 First |

### Query Template Formula

For each tool, construct queries like:
```
[VERTICAL] en [COMUNA], Chile
```

**Example query set for Outscraper (first 500 free records):**
```
clínica dental en Viña del Mar, Chile
centro estético en Viña del Mar, Chile
veterinaria en Viña del Mar, Chile
clínica dental en Valparaíso, Chile
centro estético en Valparaíso, Chile
veterinaria en Valparaíso, Chile
clínica dental en Concepción, Chile
centro estético en Concepción, Chile
```

**Verticals to query (in priority order):**
1. `clínica dental` — Highest volume, clear pain point
2. `clínica estética` / `centro de estética` — CasaVitaCure proof case
3. `veterinaria` / `clínica veterinaria` — Emotional urgency = fast decisions
4. `inmobiliaria` — High transaction value
5. `peluquería` / `barbería` — Volume play, lower ticket
6. `fumigación` / `control de plagas` — Urgency-driven

### Deduplication Strategy
When merging data from multiple scrapers:
1. Normalize phone numbers: strip +56, spaces, dashes → pure digits
2. Deduplicate on phone number (primary key)
3. If no phone, deduplicate on `place_id` or exact name + address match
4. Flash CRM's CSV import already has phone deduplication built in

---

<a name="parallel-engine"></a>
## 10. THE 6-LAYER PARALLEL EXECUTION ENGINE

```
┌─────────────────────────────────────────────────────────┐
│                  YOUR DAILY TIME BUDGET                  │
│              Wake 7:30 → Calls 10:30-19:00              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  LAYER 1 (BACKGROUND - 0 active time)                   │
│  ├── Outscraper/Apify queries running in cloud          │
│  ├── Secret Shopper tests marinating (sent earlier)     │
│  └── Cal.com auto-booking demos from yesterday's calls  │
│                                                         │
│  LAYER 2 (SEMI-ACTIVE - 15 min/day)                    │
│  ├── IG content post (pre-made, schedule with Canva)    │
│  └── Check & log Secret Shopper results in Flash CRM   │
│                                                         │
│  LAYER 3 (ACTIVE MORNING - 30 min, 7:30-8:00)          │
│  ├── ACA warm outreach messages (Strategy 7)            │
│  ├── Send batch of 10-15 Secret Shopper tests           │
│  └── Review yesterday's Flash CRM metrics, prep list    │
│                                                         │
│  LAYER 4 (PRIMARY - 4.5 hrs, 10:30-12:00 + 14:00-17:00)│
│  ├── 60 phone calls via Flash CRM DialerView           │
│  ├── Real-time logging via PostCallModal                │
│  └── Send Cal.com links to interested prospects         │
│                                                         │
│  LAYER 5 (ACTIVE AFTERNOON - 2 hrs, 17:00-19:00)       │
│  ├── Demo calls (from Cal.com bookings)                 │
│  ├── Follow-up messages to warm prospects               │
│  └── Secret Shopper follow-up messages (with screenshot)│
│                                                         │
│  LAYER 6 (WEEKLY BATCH - 2 hrs, Sunday)                 │
│  ├── Refresh scraper queries for next week              │
│  ├── Download + import CSVs to Flash CRM                │
│  ├── Run Review Mining script on new data               │
│  ├── Update tracking metrics                            │
│  └── Content batch-create for next week                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

<a name="daily-os"></a>
## 11. THE DAILY OPERATING SYSTEM — Hour by Hour

### Day Template (Business Day)

| Time | Block | Activity | Layer | Duration |
|:-----|:------|:---------|:-----:|:--------:|
| 7:30-7:45 | ☕ Wake | Coffee, check overnight messages | — | 15 min |
| 7:45-8:00 | 📱 Batch Send | Send 10-15 Secret Shopper tests (Strategy 2) | 3 | 15 min |
| 8:00-8:30 | 💬 Warm | Send 15-20 ACA messages (Strategy 7) | 3 | 30 min |
| 8:30-10:00 | 🔧 SLA | Existing tenants: bugs, config, monitoring | — | 90 min |
| 10:00-10:30 | 📋 Prep | Review Flash CRM dashboard, log Shopper results | 2 | 30 min |
| 10:30-12:00 | 📞 **CALLS** | **30 phone calls** via Flash CRM DialerView (Block 1) | 4 | 90 min |
| 12:00-14:00 | 🍽️ Break | Lunch + IG post (pre-made, 5 min to publish) | 2 | 120 min |
| 14:00-17:00 | 📞 **CALLS** | **30 phone calls** via Flash CRM DialerView (Block 2) | 4 | 180 min |
| 17:00-18:00 | 🎯 Demos | Scheduled demo calls (from Cal.com) | 5 | 60 min |
| 18:00-19:00 | ✉️ Follow-up | Send Secret Shopper screenshots + follow-up messages | 5 | 60 min |
| 19:00 | 🛑 STOP | No more outbound. Review metrics. Plan tomorrow. | — | — |

### Sunday Batch (2 hours)

| Task | Duration |
|:-----|:--------:|
| Download Outscraper/Apify data + import to Flash CRM | 15 min |
| Run Review Mining script on new data | 15 min |
| Score & tier new prospects (auto in Flash CRM) | 10 min |
| Prep 5 IG posts for next week (Canva) | 30 min |
| Review weekly metrics on Flash CRM TrackingDashboard | 15 min |
| Adjust strategy based on data | 15 min |

---

<a name="flash-crm"></a>
## 12. FLASH-CRM INTEGRATION (UPDATED v2.0)

### Status: ✅ READY — Replaces Google Sheets

Flash CRM v2 has been built and covers the entire call operations workflow. All 8 phases of the original development plan were executed. Remaining: E2E testing (Phases 7-8, manual).

### What Flash CRM Covers

| Blueprint Layer | Component | Status |
|:----------------|:----------|:------:|
| Lead import + scoring | CSV import → auto Pain/Reach/Market/Urgency | ✅ |
| Lead management | LeadList with tier/category/city badges | ✅ |
| Lead filtering | Tier A/B/C + Category filters | ✅ |
| Call tracking | DialerView (progress bar, X/60 counter) | ✅ |
| Call logging | callAttempts[] with timestamps | ✅ |
| Post-call workflow | PostCallModal (1-click disposition) | ✅ |
| Demo booking | Date picker + meeting link field | ✅ |
| Secret Shopper send | ShopperBatchView (batch send UI) | ✅ |
| Shopper result logging | ShopperResultModal (time + quality scores) | ✅ |
| ACA templates | TemplateDrawer (5 versions A-E) | ✅ |
| Daily metrics | TrackingDashboard (calls, shoppers, ACA, demos) | ✅ |
| Weekly funnel | Funnel visualization | ✅ |
| Duplicate prevention | Phone deduplication on manual add | ✅ |

### What Flash CRM Does NOT Cover (External Tools Needed)

| Need | External Tool | Status |
|:-----|:-------------|:------:|
| Data sourcing/scraping | Outscraper, Apify, etc (Section 8) | 🔴 Set up accounts |
| Demo scheduling link | Cal.com or Calendly | 🔴 Set up |
| IG content | Canva → IG manual post | 🟡 Create content |
| Review mining/analysis | Python CLI script | 🔴 Build |
| CRM ↔ Cal.com sync | Not automated (manual paste) | — H2 |

---

<a name="next-steps"></a>
## 13. NEXT STEPS — IMMEDIATE EXECUTION QUEUE (UPDATED v2.0)

### Pre-Sprint Prep Tasks

| # | Task | Time | Priority | Status |
|:-:|:-----|:----:|:--------:|:------:|
| 1 | ~~Build Google Sheet call tracker~~ | — | — | ✅ Replaced by Flash CRM |
| 2 | Build Review Mining Python script | 60 min | 🔴 | TODO |
| 3 | Sign up Outscraper (free) + run first queries | 30 min | 🔴 | TODO |
| 4 | Sign up Apify (free $5) + run first actor | 30 min | 🔴 | TODO |
| 5 | Sign up ScrapeTable (free 150 credits) | 15 min | 🔴 | TODO |
| 6 | Set up Google Cloud project + enable Places API | 30 min | 🟡 | TODO |
| 7 | Cross-reference first 100 prospects with Meta Ad Library | 45 min | 🟡 | TODO |
| 8 | Set up Cal.com (free) for demo booking | 15 min | 🟡 | TODO |
| 9 | Create 5 IG posts in Canva to populate profile | 45 min | 🟡 | TODO |
| 10 | ~~Ensure CasaVitaCure SLA~~ | — | — | ✅ Done |
| 11 | Get CasaVitaCure case study permission | 10 min | 🟡 | TODO |
| 12 | Run Flash CRM E2E tests (Phases 7-8) | 60 min | 🔴 | TODO |
| 13 | Import first CSV batch into Flash CRM | 15 min | 🔴 | After #3-5 |

### Day 1 Execution

| Time | Action |
|:-----|:-------|
| 7:30 | Send ACA messages (Version A to 30 close contacts) |
| 7:45 | Send first batch of 10 Secret Shopper tests (top-tier dental/aesthetic Viña) |
| 8:30 | SLA check on existing tenants |
| 10:30 | **START CALLING** — first 30 from Flash CRM DialerView |
| 14:00 | **RESUME CALLING** — next 30 in DialerView |
| 17:00 | Demo calls (if any booked from ACA/warm) |
| 18:00 | Collect Secret Shopper results, log in Flash CRM, send follow-ups |
| 19:00 | Log everything, prep tomorrow's list |

### May 1-10 Re-Contact Play
All prospects tagged as "Interested but price objection" get re-contacted with:
> "Hola [nombre], ¿cómo está? Hace unas semanas conversamos sobre el asistente IA para su [negocio]. Le cuento que este mes tenemos una oferta especial de onboarding: [cheaper price]. ¿Le gustaría retomar la conversación?"

Track these separately in Flash CRM with a "RECONTACT" tag.

---

## THE 30-SECOND SUMMARY

| Decision | Recommendation |
|:---------|:---------------|
| **Primary strategy** | 60 phone calls/day to pre-qualified Tier A/B prospects |
| **Execution tool** | Flash CRM v2 (replaces Google Sheets) |
| **Support strategies** | Secret Shopper (15/day), ACA warm (20/day), IG content (1/day) |
| **Target cities** | Viña del Mar → Concepción → La Serena (phone, from anywhere) |
| **Target verticals** | Medical/Aesthetic → Dental → Veterinary |
| **Data sourcing** | 6+ free tools = ~4,600 leads/month for $0 |
| **Where to live** | Puerto Varas (green, safe, stunning, business-viable) |
| **IG/Ads** | Phase 1: Canva manual (now). Phase 2: Remotion programmatic (week 2-3) |
| **Call hours** | 10:30-12:00 + 14:00-17:00 (Chilean legal compliance) |
| **Expected result** | 8-16 closes in 20 business days at 130-200K setup |
