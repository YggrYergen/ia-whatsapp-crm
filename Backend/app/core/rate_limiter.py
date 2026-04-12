# ================================================================================
# Block E2: LLM Rate Limiter Per Contact
#
# In-memory rate limiter that caps LLM calls per contact per hour.
# Prevents cost runaway from spam, loops, or abuse.
#
# Storage: Simple dict + timestamp list (warm instance memory).
# Cloud Run note: Each instance has its own dict. Under single-instance
# dev setup this is fine. For multi-instance prod, consider Redis.
#
# ⚠️  OBSERVABILITY: Every limit hit reports to Sentry + Discord (§6).
# ================================================================================
import time
from typing import Tuple

import sentry_sdk

from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert

# Configurable limit — per §2 decision table: 20/hour max
MAX_LLM_CALLS_PER_CONTACT_PER_HOUR = 20
WINDOW_SECONDS = 3600  # 1 hour


class ContactRateLimiter:
    """
    In-memory sliding window rate limiter for LLM calls per contact.
    
    Key: "{tenant_id}:{phone}" 
    Value: list of Unix timestamps of recent LLM calls
    
    Thread safety: Python's GIL makes dict operations atomic enough
    for our single-threaded async event loop. No lock needed.
    """
    
    def __init__(self):
        self._buckets: dict[str, list[float]] = {}
    
    def _prune(self, key: str) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.time() - WINDOW_SECONDS
        if key in self._buckets:
            self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]
            # Clean up empty buckets to prevent memory leak
            if not self._buckets[key]:
                del self._buckets[key]
    
    async def check_and_increment(
        self, tenant_id: str, phone: str
    ) -> Tuple[bool, int, int]:
        """
        Check if a contact is within rate limit and increment counter.
        
        Returns:
            (allowed, remaining, reset_seconds)
            - allowed: True if under limit, False if blocked
            - remaining: how many calls left in window
            - reset_seconds: seconds until oldest entry expires (approx)
        """
        key = f"{tenant_id}:{phone}"
        self._prune(key)
        
        timestamps = self._buckets.get(key, [])
        count = len(timestamps)
        
        if count >= MAX_LLM_CALLS_PER_CONTACT_PER_HOUR:
            # RATE LIMITED — calculate reset time
            oldest = min(timestamps) if timestamps else time.time()
            reset_seconds = int((oldest + WINDOW_SECONDS) - time.time())
            reset_seconds = max(reset_seconds, 1)  # At least 1 second
            
            logger.warning(
                f"🚫 [RATE] Contact {phone} hit rate limit ({count}/{MAX_LLM_CALLS_PER_CONTACT_PER_HOUR}/hr) "
                f"| Tenant {tenant_id} | Resets in {reset_seconds}s"
            )
            sentry_sdk.set_context("rate_limit", {
                "tenant_id": tenant_id,
                "phone": phone,
                "count": count,
                "max": MAX_LLM_CALLS_PER_CONTACT_PER_HOUR,
                "reset_seconds": reset_seconds,
            })
            sentry_sdk.capture_message(
                f"Rate limit hit: {phone} ({count}/{MAX_LLM_CALLS_PER_CONTACT_PER_HOUR}/hr) | Tenant {tenant_id}",
                level="warning"
            )
            await send_discord_alert(
                title=f"🚫 Rate Limit Hit | Tenant {tenant_id}",
                description=(
                    f"Contact `{phone}` exceeded {MAX_LLM_CALLS_PER_CONTACT_PER_HOUR} LLM calls/hour.\n"
                    f"Current count: {count}\n"
                    f"Auto-resumes in ~{reset_seconds}s.\n"
                    f"⚠️ Investigate if this is spam or a stuck loop."
                ),
                severity="warning"
            )
            return (False, 0, reset_seconds)
        
        # ALLOWED — record this call
        if key not in self._buckets:
            self._buckets[key] = []
        self._buckets[key].append(time.time())
        
        remaining = MAX_LLM_CALLS_PER_CONTACT_PER_HOUR - (count + 1)
        return (True, remaining, 0)
    
    def get_stats(self) -> dict:
        """Return current state for debugging."""
        return {
            "active_contacts": len(self._buckets),
            "total_entries": sum(len(v) for v in self._buckets.values()),
        }


# Module-level singleton
rate_limiter = ContactRateLimiter()
