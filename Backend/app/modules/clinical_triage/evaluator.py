from app.core.models import TenantContext
from app.core.event_bus import event_bus
from app.infrastructure.telemetry.logger_service import logger

class TriageEvaluator:
    """Domain logic for clinical evaluations and routing."""
    
    @staticmethod
    async def evaluate_symptoms(tenant: TenantContext, symptoms: str, patient_phone: str) -> str:
        """Evaluates symptoms and delegates alerts using EventBus if critical."""
        logger.info(f"Evaluating symptoms for {patient_phone} in tenant {tenant.id}")
        
        # Domain Clinical Rule
        critical_keywords = ["dolor pecho", "sangrado", "emergencia"]
        is_critical = any(k in symptoms.lower() for k in critical_keywords)
        
        if is_critical:
            logger.warning("Critical symptoms detected! Emitting async triage_alert.")
            
            # Decoupled alert, avoiding circular dependencies to Meta endpoints
            await event_bus.publish("triage_alert", {
                "tenant_id": tenant.id,
                "patient_phone": patient_phone,
                "staff_number": tenant.staff_notification_number,
                "symptoms": symptoms
            })
            return "critical_alert_triggered"
            
        return "routine_evaluation"
