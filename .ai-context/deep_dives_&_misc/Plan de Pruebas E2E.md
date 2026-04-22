# Plan de Pruebas E2E — Apr 21

## Tenants Activos con WhatsApp

| Tenant | Phone ID | Recursos | Servicios | Horario | Duración default |
|:---|:---|:---|:---|:---|:---|
| **CasaVitaCure** | `1041525325713013` | Box 1, Box 2 | Diagnóstico (30m), CelluDetox (60m), Lipedema (60m) | L-V 08:30-20:00, S 09:00-14:00 | 30 min |
| **Control Pest** | `1136728616179973` | equipo_1 | Desratización (120m), Desinfección (120m), Fumigación (120m), Sanitización (90m) | 24/7 | 120 min |

## 7 Herramientas del Asistente

| # | Tool | Función |
|:---|:---|:---|
| 1 | `get_merged_availability` | Consultar disponibilidad para una fecha |
| 2 | `get_my_appointments` | Ver citas del usuario o la agenda completa (staff) |
| 3 | `book_round_robin` | Agendar cita con round-robin entre recursos |
| 4 | `update_appointment` | Modificar una cita existente |
| 5 | `delete_appointment` | Cancelar cita (verifica phone match) |
| 6 | `request_human_escalation` | Escalar a humano (pausa bot) |
| 7 | `update_patient_scoring` | Actualizar scoring del paciente/contacto |

---

## FASE 1 — Flujos Pendientes (fixes de hoy)

Envía estos mensajes **desde tu teléfono personal** vía WhatsApp:

### Test 1.1: Bot CasaVitaCure responde (bot_active fix)
**Enviar a:** Número WhatsApp de CasaVitaCure
**Mensaje:** `Hola, buenas tardes`
**Esperado:** Bot responde (ya no está muted). Verificar en Sentry/Discord que no hay errores.
**Verificar en CRM:** `dash.tuasistentevirtual.cl/chats` → tenant CasaVitaCure → tu chat ya NO muestra "Intervención manual"

### Test 1.2: Bot Control Pest responde
**Enviar a:** Número WhatsApp de Control Pest
**Mensaje:** `Hola, necesito información sobre fumigación`
**Esperado:** Bot responde con info del servicio.

### Test 1.3: Staff message (RLS fix)
**En CRM:** `dash.tuasistentevirtual.cl/chats` → tenant CasaVitaCure → seleccionar tu chat → escribir como staff: `Este es un mensaje de prueba del equipo`
**Esperado:** 
- ❌ NO hay error 42501 en Sentry
- ✅ Mensaje aparece en el CRM con badge "Staff"
- ✅ Mensaje llega a tu teléfono vía WhatsApp

### Test 1.4: Resolver escalación persiste
**En CRM:** Si algún chat aún muestra "Intervención manual" → click "Resolver"
**Verificar en DB:** El contact debe tener `bot_active = true`
*Yo verifico después con SQL.*

### Test 1.5: Config por tenant (frontend fix)
**En CRM:** 
1. Sidebar → Tenant switcher → seleccionar **Control Pest**
2. Ir a `/config`
3. **Esperado:** Muestra el system prompt de Control Pest (empieza con "Eres parte del equipo de *Control Pest*...")
4. Sidebar → Tenant switcher → seleccionar **CasaVitaCure**
5. Ir a `/config`
6. **Esperado:** Muestra el system prompt de CasaVitaCure (empieza con "Eres Javiera, la asistente ejecutiva...")

---

## FASE 2 — E2E Herramientas del Asistente

> Prueba cada herramienta enviando mensajes reales por WhatsApp.
> Usar **CasaVitaCure** para todas las pruebas (tiene round-robin con 2 boxes y 3 servicios).

### Test 2.1: `get_merged_availability` — Consultar disponibilidad
**Mensaje:** `¿Qué horarios tienen disponibles para mañana?`
**Esperado:** Bot usa la herramienta, responde con horarios disponibles dentro de 08:30-20:00 (L-V) en slots de 30 min.
**Validar:** Respuesta incluye horarios reales y no genéricos.

### Test 2.2: `book_round_robin` — Agendar cita
**Mensaje:** `Quiero agendar una sesión de diagnóstico para mañana a las 10:00, mi nombre es Tomás Gemes`
**Esperado:** Bot confirma la cita con hora, fecha, y nombre del servicio.
**Verificar en CRM:** `/agenda` → debe aparecer la cita en Box 1 o Box 2.
**Verificar en DB:** `SELECT * FROM appointments WHERE client_name ILIKE '%gemes%' ORDER BY created_at DESC LIMIT 1`

### Test 2.3: `get_my_appointments` — Ver mis citas
**Mensaje:** `¿Tengo alguna cita agendada?`
**Esperado:** Bot lista la cita que acabas de crear (Test 2.2).

### Test 2.4: `update_appointment` — Modificar cita
**Mensaje:** `¿Pueden cambiar mi cita de mañana a las 15:00?`
**Esperado:** Bot confirma el cambio de hora.
**Verificar en DB:** El `start_time` debe ser las 15:00.

### Test 2.5: `delete_appointment` — Cancelar cita
**Mensaje:** `Necesito cancelar mi cita de mañana`
**Esperado:** Bot confirma la cancelación.
**Verificar en DB:** `status = 'cancelled'` y `cancelled_at` tiene timestamp.

### Test 2.6: `request_human_escalation` — Escalar a humano
**Mensaje:** `Quiero hablar con una persona real, esto es urgente`
**Esperado:**
- Bot responde confirmando que transfiere a un humano
- Contact `bot_active` → `false`
- Alerta aparece en el CRM dashboard
- Discord recibe notificación de escalación
**Verificar en CRM:** Chat muestra "Intervención manual" con badge naranja

### Test 2.7: `update_patient_scoring` — Scoring (automático)
**No requiere mensaje explícito.** Esta herramienta se llama automáticamente durante la conversación.
**Verificar después de Tests 2.1-2.6:**
```sql
SELECT metadata FROM contacts 
WHERE phone_number = 'TU_NUMERO'
AND tenant_id = 'd8376510-911e-42ef-9f3b-e018d9f10915';
```
Debería tener scoring actualizado en `metadata.scoring`.

---

## FASE 3 — Cross-Tenant Isolation

### Test 3.1: Cita en Control Pest
**Enviar a:** Número WhatsApp de Control Pest
**Mensaje:** `Necesito agendar una fumigación para el viernes`
**Esperado:** Bot agenda con `equipo_1`. Duración = 120 min (default de Control Pest).
**Verificar:** La cita NO aparece en la agenda de CasaVitaCure.

### Test 3.2: Las citas de un tenant NO se ven en otro
**En CRM:** Cambiar a CasaVitaCure → `/agenda` → no debe haber citas de Control Pest.
**En CRM:** Cambiar a Control Pest → `/agenda` → solo citas de Control Pest.

---

## Señales de Éxito / Fallo

| Señal | ✅ OK | ❌ Fallo |
|:---|:---|:---|
| Sentry | Sin nuevos errores en últimos 30 min | Error `42501` o nuevo exception |
| Discord | No `INVALID Webhook Signature` | Signature errors = HMAC broken |
| CRM chats | Mensajes fluyen en realtime | Chat congelado o "pausado" sin razón |
| Agenda | Citas reflejan round-robin | Cita sin recurso o en recurso incorrecto |
| Config page | Muestra prompt del tenant activo | Siempre muestra el mismo prompt |

---

## Después de las Pruebas

Una vez que termines, avísame y yo:
1. Verifico DB (appointments, contacts.bot_active, messages)
2. Reviso Sentry por errores nuevos
3. Reviso Cloud Run logs
4. Limpio las citas de prueba si es necesario
