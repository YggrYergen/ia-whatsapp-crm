# ================================================================================
# Phase 5A: Webhook Simulation Scenarios
# ================================================================================
# Each scenario defines: a name, description, the payloads to send,
# timing/concurrency mode, and expected outcomes for verification.
#
# OBSERVABILITY RULE: Every error scenario MUST produce both a Sentry event
# AND a Discord notification. The runner validates this.
# ================================================================================

from dataclasses import dataclass, field
from typing import Literal
from scripts.simulation.payload_factory import (
    make_text_message,
    make_status_update,
    make_image_message,
    make_location_message,
    make_reaction_message,
    make_malformed_no_entry,
    make_malformed_no_changes,
    make_malformed_no_metadata,
    make_empty_message_body,
    make_very_long_message,
    make_special_characters_message,
)

# ── Simulation phone numbers (all fake, prefixed with 569SIM) ──────────
SIM_PHONES = {
    "happy_path": "56910000001",
    "booking": "56910000002",
    "escalation": "56910000003",
    "clinical": "56910000004",
    "burst_1": "56910000005",
    "concurrent_a": "56910000006",
    "concurrent_b": "56910000007",
    "concurrent_c": "56910000008",
}


@dataclass
class SimScenario:
    """A single simulation scenario."""
    name: str
    description: str
    payloads: list[dict]
    mode: Literal["sequential", "burst", "concurrent"] = "sequential"
    delay_between_ms: int = 500  # ms between sequential payloads
    expect_http_200: bool = True
    expect_llm_response: bool = True
    expect_tool_calls: list[str] = field(default_factory=list)
    expect_sentry_alert: bool = False
    expect_discord_alert: bool = False
    notes: str = ""


def get_all_scenarios() -> list[SimScenario]:
    """Return all simulation scenarios in execution order."""
    return [
        # ── 1. Happy Path: Single text message ──────────────────────────
        SimScenario(
            name="1_happy_path_single_text",
            description="Single text message → full pipeline (LLM inference + response + persistence)",
            payloads=[
                make_text_message(
                    from_number=SIM_PHONES["happy_path"],
                    text="Hola, quisiera información sobre sus tratamientos disponibles",
                    profile_name="Sim Happy Path",
                ),
            ],
            expect_llm_response=True,
            notes="Baseline test. Should create a new contact, process through LLM, persist reply.",
        ),
        
        # ── 2. Tool Trigger: Booking Intent ──────────────────────────────
        SimScenario(
            name="2_tool_trigger_booking",
            description="Booking intent → should trigger availability/booking tool",
            payloads=[
                make_text_message(
                    from_number=SIM_PHONES["booking"],
                    text="Quiero agendar una cita para mañana a las 10 de la mañana por favor",
                    profile_name="Sim Booking User",
                ),
            ],
            expect_tool_calls=["get_merged_availability", "book_round_robin"],
            notes="Expected to call availability/booking tools. May fail if calendar is disconnected in dev — that's a known expected error, should appear in Sentry.",
        ),
        
        # ── 3. Tool Trigger: Escalation ──────────────────────────────────
        SimScenario(
            name="3_tool_trigger_escalation",
            description="Explicit human escalation request → request_human_escalation tool",
            payloads=[
                make_text_message(
                    from_number=SIM_PHONES["escalation"],
                    text="Necesito hablar con un humano, el bot no puede ayudarme con esto",
                    profile_name="Sim Escalation User",
                ),
            ],
            expect_tool_calls=["request_human_escalation"],
            notes="Should call request_human_escalation tool and disable bot for this contact.",
        ),
        
        # ── 4. Clinical Keyword: Force Escalation ────────────────────────
        SimScenario(
            name="4_clinical_keyword_force_escalation",
            description="Clinical keyword detected → force_escalation=True, tool_choice override",
            payloads=[
                make_text_message(
                    from_number=SIM_PHONES["clinical"],
                    text="Tengo dolor severo después del tratamiento de ayer, estoy sangrando",
                    profile_name="Sim Clinical Emergency",
                ),
            ],
            expect_tool_calls=["request_human_escalation"],
            notes="Keywords 'dolor' and 'sangrando' trigger force_escalation=True. "
                  "LLM tool_choice is forced to request_human_escalation.",
        ),
        
        # ── 5. Status-Only Webhook (No Messages) ─────────────────────────
        SimScenario(
            name="5_status_only_webhook",
            description="Delivery status webhook with no messages array → graceful skip",
            payloads=[
                make_status_update(status="delivered"),
                make_status_update(status="read"),
            ],
            expect_llm_response=False,
            notes="Backend should return 200 and log 'No messages in payload'. No LLM call.",
        ),
        
        # ── 6. Malformed Payloads → Error Handling ───────────────────────
        SimScenario(
            name="6_malformed_payloads",
            description="Broken payloads → graceful error handling + Sentry + Discord alerts",
            payloads=[
                make_malformed_no_entry(),
                make_malformed_no_changes(),
                make_malformed_no_metadata(),
            ],
            mode="sequential",
            delay_between_ms=1000,
            expect_llm_response=False,
            expect_sentry_alert=True,
            expect_discord_alert=True,
            notes="All 3 payloads should fail gracefully with HTTP 200 (Meta requires 200). "
                  "Each should generate a Sentry event AND a Discord alert.",
        ),
        
        # ── 7. Rapid Burst (Same User) → Mutex Test ─────────────────────
        SimScenario(
            name="7_rapid_burst_same_user",
            description="5 messages in rapid succession from same phone → is_processing_llm mutex",
            payloads=[
                make_text_message(from_number=SIM_PHONES["burst_1"], text=f"Mensaje burst {i+1}", profile_name="Sim Burst User")
                for i in range(5)
            ],
            mode="burst",
            delay_between_ms=100,  # 100ms between — near-simultaneous
            expect_llm_response=True,
            notes="First message should process. Subsequent messages should be blocked by "
                  "is_processing_llm=True. Only 1-2 LLM responses expected.",
        ),
        
        # ── 8. Multi-User Concurrent → Tenant Isolation ─────────────────
        SimScenario(
            name="8_multi_user_concurrent",
            description="3 different phone numbers send simultaneously → no cross-talk",
            payloads=[
                make_text_message(from_number=SIM_PHONES["concurrent_a"], text="Soy el usuario A, ¿cuáles son los precios?", profile_name="Sim User A"),
                make_text_message(from_number=SIM_PHONES["concurrent_b"], text="Soy el usuario B, ¿dónde están ubicados?", profile_name="Sim User B"),
                make_text_message(from_number=SIM_PHONES["concurrent_c"], text="Soy el usuario C, ¿qué tratamientos ofrecen?", profile_name="Sim User C"),
            ],
            mode="concurrent",
            expect_llm_response=True,
            notes="All 3 should process independently. Verify: each contact gets their own "
                  "response. No cross-contamination in message history.",
        ),
        
        # ── 9. Edge Cases: Empty, Long, Special Chars, Media ─────────────
        SimScenario(
            name="9_edge_cases",
            description="Boundary conditions: empty msg, very long msg, special chars, image, location, reaction",
            payloads=[
                make_empty_message_body(),
                make_very_long_message(length=5000),
                make_special_characters_message(),
                make_image_message(from_number="56910000009"),
                make_location_message(from_number="56910000010"),
                make_reaction_message(from_number="56910000011"),
            ],
            mode="sequential",
            delay_between_ms=2000,
            expect_llm_response=True,  # For text ones at least
            notes="Tests robustness against unusual inputs. Image/location/reaction may not "
                  "produce LLM responses if the backend doesn't handle non-text types, "
                  "but should NOT crash.",
        ),
    ]
