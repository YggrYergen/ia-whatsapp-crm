# Evaluación de Template Messages de WhatsApp

## 1. Regla de las 24 Horas (Service Window)
Meta permite enviar **mensajes de sesión (libres y sin costo extra)** siempre que el paciente haya enviado un mensaje en las últimas 24 horas.

Si han pasado más de 24 horas desde que el paciente nos habló, el sistema CRM **solo puede contactarlo usando un Template Message** aprobado por Meta.

## 2. Lógica Sugerida para el Backend

```python
# Lógica conceptual propuesta para futura implementación
if time_since_last_patient_message < timedelta(hours=24):
    # Enviar mensaje libre 
    send_text_message(phone, text)
else:
    # Se requiere un Template Message
    send_template_message(phone, template_name="recordatorio_cita", variables=[paciente, fecha])
```

## 3. Templates Propuestos para Registro

Los siguientes templates deberían ser registrados en el **Administrador de WhatsApp Business**:

### A. Recordatorio de Cita (Utility)
- **Nombre:** `appointment_reminder`
- **Categoría:** Utility (Utilidad)
- **Cuerpo:** `Hola {{1}}, te escribimos de CasaVitaCure para recordar tu cita programada para el {{2}}. Responde a este mensaje para confirmar o cancelar.`

### B. Seguimiento Post-Atención (Utility)
- **Nombre:** `post_appointment_followup`
- **Categoría:** Utility
- **Cuerpo:** `Hola {{1}}, esperamos que tu experiencia en CasaVitaCure haya sido excelente. ¿Podrías dejarnos una reseña o cuéntanos si necesitas algo más?`

### C. Alerta Administrativa (Utility)
- **Nombre:** `admin_alert_contact`
- **Categoría:** Utility
- **Cuerpo:** `Hola {{1}}, nuestro equipo necesita comunicarse contigo por un asunto de tu cuenta o ficha clínica. Por favor, respóndenos cuando estés disponible.`

## 4. Costos (Precios aproximados Chile 2024/2025)

- **Conversación de Servicio (Iniciada por el usuario, libre en 24h):** Gratis los primeros 1,000 mensuales, luego ~$0.09 USD.
- **Conversación de Utilidad (Templates descritos arriba):** ~$0.04 USD por conversación (durante 24h).
- **Conversación de Marketing:** ~$0.07 USD por conversación.

> **Recomendación:** Implementar un botón "Pedir Handoff/Contactar" en el chat del frontend que llame al backend y evalúe si debe usar el `admin_alert_contact` o enviar un mensaje directo.
