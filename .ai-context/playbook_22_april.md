# 🎯 Playbook Operativo — Martes 22 de Abril

> **Contexto:** Día de ventas. Todo lo de abajo está organizado en bloques secuenciales con dependencias claras. Ejecutar en orden.

---

## Estado Actual de los Datos (Inventario)

| Fuente | Estado | Registros | Ubicación |
|:-------|:------:|:---------:|:----------|
| **ScrapeTable** (9 queries, 3 cuentas) | ✅ Procesado | ~250-350 | `data/raw/charlie/` (3 CSV limpios) |
| **Apify** | ✅ Procesado | ~185KB CSV | `data/raw/bravo/apify_google_maps_full.csv` |
| **Outscraper XLSX grande** (81 rows, 65 cols) | ❌ **SIN PROCESAR** | 80 negocios + teléfonos | `Downloads/Outscraper-20260420181541s43.xlsx` |
| **Outscraper XLSX chico** (11 rows, reviews) | ❌ **SIN PROCESAR** | 10 reviews (sólo reseñas, no negocios) | `Downloads/Outscraper-20260420161025s37.xlsx` |
| **PhantomBuster** | ❌ No ejecutado | 0 | Charlie tracker: Part 2 no se hizo |
| **`flash_crm_import_ready.csv`** | ⚠️ Existe, pero **sólo ScrapeTable** | ~195KB | `data/processed/` |

> [!IMPORTANT]
> El archivo chico de Outscraper (10 rows) es **sólo reviews**, no negocios. Tiene columnas de reseñas (`review_text`, `review_rating`, `author_title`). Esto alimenta `review_miner.py` directamente, **no** `csv_merger.py`.
>
> El archivo grande (80 rows) SÍ tiene negocios con `phone`, `name`, `address`, `rating`, `reviews`, `place_id`, `category`, `website`. Este va al pipeline estándar.

---

## BLOQUE 1: Pipeline de Datos (30-40 min) ⏰ Hacer PRIMERO

### Paso 1.1: Convertir XLSX → CSV
```bash
cd D:\WebDev\IA\SALES_STUFF
python -c "
import openpyxl, csv
wb = openpyxl.load_workbook(r'C:\Users\tomas\Downloads\Outscraper-20260420181541s43.xlsx')
ws = wb.active
with open('data/raw/alpha/outscraper_businesses.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    for row in ws.iter_rows(values_only=True):
        writer.writerow(row)
print('✅ Businesses CSV written')
"
```

```bash
python -c "
import openpyxl, csv
wb = openpyxl.load_workbook(r'C:\Users\tomas\Downloads\Outscraper-20260420161025s37.xlsx')
ws = wb.active
with open('data/raw/alpha/outscraper_reviews.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    for row in ws.iter_rows(values_only=True):
        writer.writerow(row)
print('✅ Reviews CSV written')
"
```

### Paso 1.2: Actualizar `preprocess_raw_data.py`

> [!WARNING]
> El preprocesador actual sólo mapea archivos de ScrapeTable. Hay que agregar la entrada del CSV de Outscraper al `FILE_MAP`. El XLSX de negocios Outscraper tiene columnas que **ya coinciden** con lo que espera `csv_merger.py` (`phone`, `name`, `address`, `rating`, `reviews`, `place_id`, `website`), así que el remap es mínimo.

**Cambio necesario en `FILE_MAP`:**
```python
# Outscraper business data → alpha
("outscraper_businesses.csv", "alpha", "outscraper_businesses_clean.csv"),
```

**Pero** el archivo ya estaría en `data/raw/alpha/`, no en Downloads. Para Outscraper podemos skipear el preprocess y ir directo al merger, ya que:
- Las columnas ya tienen nombres correctos (`phone`, `name`, `address`, etc.)
- Los teléfonos ya vienen con formato `+56 9 XXXX XXXX`
- Los registros son todos de Chile (query fue "en Chile")

**Acción recomendada:** Copiar el CSV a `data/raw/alpha/` y correr `csv_merger.py` directo.

### Paso 1.3: Review Mining (con el archivo de reviews)
```bash
python review_miner.py data/raw/alpha/outscraper_reviews.csv -o data/processed/pain_scored_outscraper.csv
```

### Paso 1.4: Merge Final → Flash CRM Ready
```bash
python csv_merger.py data/raw/ --pain-csv data/processed/pain_scored_outscraper.csv -o data/processed/flash_crm_import_ready_v2.csv
```

### Paso 1.5: Verificación
```bash
python -c "
import csv
with open('data/processed/flash_crm_import_ready_v2.csv') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    phones = [r['phone'] for r in rows if r.get('phone')]
    print(f'Total records: {len(rows)}')
    print(f'With phone: {len(phones)}')
    print(f'Unique phones: {len(set(phones))}')
    tiers = {}
    for r in rows:
        t = r.get('tier', '?')
        tiers[t] = tiers.get(t, 0) + 1
    print(f'Tiers: {tiers}')
"
```

> **Resultado esperado:** ~400-600 registros únicos con teléfono, listos para importar a Flash CRM.

---

## BLOQUE 2: Material de Ventas — Inventario & Gaps (~20 min prep)

### ✅ Material que YA existe

| Asset | Ubicación | Estado |
|:------|:----------|:------:|
| Scripts de llamada (EN + ES) | `call_scripts.md` + `scripts_pocket_guide.md` | ✅ Listo |
| Scripts pocket guide PDF | `scripts_pocket_guide.pdf` (114KB) | ✅ Listo |
| Sales Engine Upgrade PDF | `sales_engine_upgrade.pdf` (125KB) | ✅ Listo |
| Mensajes Secret Shopper por vertical | `scripts_pocket_guide.md` §9 | ✅ 6 verticales |
| Templates ACA (A-E) | Flash CRM TemplateDrawer + `sales_execution_blueprint.md` §6 | ✅ 5 versiones |
| Flash CRM con DialerView, PostCallModal, etc. | `flash-crm-v2` repo | ✅ Operativo |

### ❌ Material FALTANTE

| Asset | Para qué | Prioridad | Tiempo estimado |
|:------|:---------|:---------:|:---------------:|
| **Imagen WhatsApp post-llamada** | Enviar después de la llamada como "tarjeta de presentación visual" | 🔴 Alta | 15 min (generar con AI) |
| **Video demo 1 min** | Follow-up Day 3 (cadencia §6). Enviar a "necesito pensarlo" | 🔴 Alta | 30-60 min (screen recording del demo bot real) |
| **IG profile content** (5 posts) | Sin IG = DMs muertos. Prospectos buscan y ven vacío | 🟡 Media | 45 min (Canva batch) |
| **Herramienta de videos personalizados** (Remotion) | Escalar video outreach. Pero es dev work | ⚪ Baja (Sprint 2+) | Horas de dev |
| **Cal.com configurado** | Demo booking link para enviar post-llamada | 🟡 Media | 15 min |
| **Auditoría WhatsApp PDF** (Lead Magnet §6) | Enviar como gancho a "no me interesa" | 🟡 Media | 30 min |

### Priorización para Mañana

> [!TIP]
> **Lo que realmente necesitas para el Día 1 de llamadas:**
> 1. ✅ Scripts (ya los tienes en PDF y MD)
> 2. ✅ Lista de leads procesada (Bloque 1)
> 3. ✅ Flash CRM operativo
> 4. 🔴 **Imagen WhatsApp** — crearla ANTES de las 10:30
> 5. 🔴 **Video demo** — puede esperar al Day 3 de cadencia, pero idealmente grabar hoy
> 6. 🟡 Cal.com — configurar durante el bloque de 8:30-10:00

---

## BLOQUE 3: Fix Frontend — Botones de Acción en /chats (15-20 min dev)

### Problema Detectado
En `/chats` → panel lateral `ClientProfilePanel.tsx`, la card de datos personales del contacto **NO tiene los botones de acción rápida** que SÍ existen en `/pacientes` → `PacientesView.tsx`.

### Comparativa

| Feature | `/pacientes` (PacientesView) | `/chats` (ClientProfilePanel) |
|:--------|:---:|:---:|
| Botón LLAMAR (`tel:`) | ✅ Línea 203 | ❌ Falta |
| Botón CHAT/WhatsApp (`wa.me`) | ✅ Línea 206 (Link a /chats) | ❌ Falta |
| Botón AGENDAR (Link a /agenda) | ✅ Línea 212 | ❌ Falta |

### Fix Propuesto

Agregar un bloque de 3 botones-ícono (solo íconos, sin texto) después del `Profile Summary` (después de la línea 193) y antes de la sección "Información de Contacto" (línea 196):

```tsx
{/* Quick Action Buttons */}
<div className="flex gap-2 justify-center pb-4 border-b border-slate-100">
    <a
        href={`tel:${selectedContact.phone_number}`}
        className="w-10 h-10 flex items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 hover:bg-emerald-100 transition-colors"
        title="Llamar"
    >
        <Phone size={18} />
    </a>
    <a
        href={`https://wa.me/${selectedContact.phone_number.replace(/\D/g, '')}`}
        target="_blank"
        rel="noopener noreferrer"
        className="w-10 h-10 flex items-center justify-center rounded-xl bg-green-50 text-green-600 hover:bg-green-100 transition-colors"
        title="Abrir WhatsApp"
    >
        <MessageCircle size={18} />
    </a>
    <a
        href="/agenda"
        className="w-10 h-10 flex items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition-colors"
        title="Agendar"
    >
        <Calendar size={18} />
    </a>
</div>
```

> [!NOTE]
> - Usa `MessageCircle` + `Calendar` que ya están importados en el componente
> - El botón de WhatsApp abre `wa.me/` en nueva pestaña (el más útil desde /chats)
> - En `/pacientes` el botón "CHAT" navega a `/chats`, pero acá **ya estamos en /chats**, así que el equivalente es abrir WhatsApp directamente
> - Solo íconos (sin texto) para que sea compacto en el panel lateral estrecho (320-380px)

### Archivos a Modificar
- [ClientProfilePanel.tsx](file:///D:/WebDev/IA/Frontend/components/Conversations/ClientProfilePanel.tsx) — agregar bloque de botones + import `MessageCircle`

---

## BLOQUE 4: Timeline del Día (según Daily OS)

```
┌────────────────────────────────────────────────────────────────┐
│  MARTES 22 DE ABRIL — DÍA DE VENTAS                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  🌅 7:30   Despertar. Café.                                   │
│                                                                │
│  📊 7:45   BLOQUE 1: Pipeline de Datos (30-40 min)            │
│            → Convertir XLSX → CSV                              │
│            → Correr review_miner + csv_merger                  │
│            → Verificar flash_crm_import_ready_v2.csv           │
│                                                                │
│  📱 8:15   BLOQUE 2 parcial: Crear imagen WA post-llamada     │
│            → AI image gen (15 min)                             │
│                                                                │
│  💬 8:30   ACA Warm Outreach (15-20 msgs)                     │
│            → Usar Template A para cercanos, B para conocidos   │
│            → Enviar batch Secret Shopper (10-15 tests a        │
│              negocios Tier A dental/estética del CSV nuevo)     │
│                                                                │
│  🔧 9:00   BLOQUE 3: Fix frontend (15-20 min)                 │
│            → Implementar botones acción en ClientProfilePanel  │
│            → Verificar en dash.tuasistentevirtual.cl           │
│                                                                │
│  📋 9:30   Importar CSV a Flash CRM                            │
│            → Abrir Flash CRM                                   │
│            → Import flash_crm_import_ready_v2.csv              │
│            → Revisar scoring y filtrar por Tier A/B            │
│                                                                │
│  ⚙️ 10:00  Configurar Cal.com (15 min)                        │
│            → Crear link de booking para demos                   │
│                                                                │
│  📞 10:30  === BLOQUE LLAMADAS MAÑANA ===                      │
│            30 llamadas via Flash CRM DialerView                │
│            → Scripts: pocket_guide.md abierto en 2da pantalla  │
│            → Log cada llamada en PostCallModal                 │
│                                                                │
│  🍽️ 12:00  Almuerzo + IG post (pre-hecho o Canva rápido)      │
│                                                                │
│  📞 14:00  === BLOQUE LLAMADAS TARDE ===                       │
│            30 llamadas via Flash CRM DialerView                │
│                                                                │
│  🎯 17:00  Demo calls (si hay agendadas de ACA/warm)           │
│                                                                │
│  ✉️ 18:00  Recoger resultados Secret Shopper                   │
│            → Screenshots de response time                      │
│            → Log en Flash CRM ShopperResultModal               │
│            → Enviar follow-ups con el mensaje Post-Shopper     │
│                                                                │
│  🛑 19:00  STOP. Revisar métricas del día.                     │
│            → Preparar lista de mañana en Flash CRM             │
│            → Grabar video demo si no se hizo (para Day 3 FU)   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Decisiones Pendientes (Tu Input)

1. **¿Imagen WhatsApp post-llamada?** — ¿Quieres que genere una imagen profesional con tu branding (`tuAsistenteVirtual`) que sirva como tarjeta de presentación visual para enviar por WA después de la llamada?

2. **¿Video demo?** — ¿Prefieres grabar una screen recording del bot de CasaVitaCure/ControlPest respondiendo en vivo, o prefieres generar algo más producido? El script sugiere video de 1 min para el Day 3 follow-up.

3. **¿Fix frontend ahora o mañana temprano?** — El fix de botones en ClientProfilePanel es ~15 min de código + deploy. Puedo hacerlo ahora si prefieres despertar con eso listo.

4. **¿PhantomBuster?** — Quedó sin ejecutar (Part 2 del Agent CHARLIE). ¿Lo hacemos esta noche o lo dejamos para otra ronda?
