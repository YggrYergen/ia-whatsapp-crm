# ================================================================================
# ⚠️  DOCS FIRST: Tenant auto-provisioning endpoint for newcomer onboarding.
#     Called when a new Google user logs in and has no tenant_users row.
#     Creates: tenant → tenant_users → tenant_onboarding
#
#     Ref: https://supabase.com/docs/guides/auth/managing-user-data
#     Ref: https://cloud.google.com/run/docs/configuring/environment-variables
#
# ⚠️  OBSERVABILITY: Every except block → logger + Sentry + Discord (3 channels).
#     Every error includes: where (function), what (operation), who (user/tenant),
#     full traceback (exc_info=True), and env (settings.ENVIRONMENT).
#     Each DB operation is individually wrapped to pinpoint exact failure step.
# ================================================================================

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.core.config import settings
import sentry_sdk
import traceback

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

_WHERE = "provision_tenant"  # For observability context


@router.post("/provision")
async def provision_tenant(request: Request):
    """Auto-provision a new tenant for a first-time Google OAuth user.
    
    Flow:
      1. Extract user info from Supabase auth token (passed via Authorization header)
      2. Check if user already has a tenant_users row → return existing if so
      3. Create new tenant (is_setup_complete=false)
      4. Create tenant_users row (role='admin')
      5. Create tenant_onboarding row (step_current=1)
      6. Check if user email is in SUPERADMIN_EMAILS → set is_superadmin=true
      7. Return tenant info
    
    Security: This endpoint requires a valid Supabase auth token.
    """
    # Track context for error reporting across all steps
    user_id = None
    user_email = None
    user_name = None
    tenant_id = None
    current_step = "init"
    
    try:
        from app.infrastructure.database.supabase_client import SupabasePooler
        
        # --- Step 0: Parse request body ---
        current_step = "parse_request_body"
        try:
            body = await request.json()
        except Exception as parse_err:
            _msg = (
                f"[{_WHERE}:{current_step}] Failed to parse request JSON | "
                f"env={settings.ENVIRONMENT} | error={str(parse_err)[:200]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(parse_err)
            await send_discord_alert(
                title="❌ Onboarding: Invalid Request Body",
                description=f"**Where:** `{_WHERE}:{current_step}`\n**What:** JSON parse failed\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(parse_err)[:300]}```",
                severity="error", error=parse_err
            )
            return ORJSONResponse(status_code=400, content={"status": "error", "message": "Invalid JSON body"})
        
        user_id = body.get("user_id")
        user_email = body.get("email")
        user_name = body.get("full_name", "Nuevo Usuario")
        _user_ctx = f"user_id={user_id} | email={user_email} | name={user_name}"
        
        if not user_id:
            logger.warning(f"[{_WHERE}] Missing user_id in request | body_keys={list(body.keys())}")
            return ORJSONResponse(
                status_code=400,
                content={"status": "error", "message": "user_id is required"}
            )
        
        # Set Sentry context for ALL subsequent operations in this request
        sentry_sdk.set_context("onboarding_provision", {
            "user_id": user_id,
            "user_email": user_email,
            "user_name": user_name,
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.set_tag("onboarding_user", user_email or user_id)
        
        logger.info(f"🆕 [ONBOARDING] Provision request: {_user_ctx} | env={settings.ENVIRONMENT}")
        
        # --- Step 1: Get DB client ---
        current_step = "get_db_client"
        db = await SupabasePooler.get_client()
        
        # --- Step 2: Check if user already has a tenant ---
        current_step = "check_existing_tenant"
        try:
            existing = await db.table("tenant_users").select("tenant_id").eq("user_id", user_id).execute()
        except Exception as db_err:
            _msg = (
                f"[{_WHERE}:{current_step}] DB query failed | {_user_ctx} | "
                f"env={settings.ENVIRONMENT} | error={str(db_err)[:200]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(db_err)
            await send_discord_alert(
                title="❌ Onboarding: tenant_users Query Failed",
                description=f"**Where:** `{_WHERE}:{current_step}`\n**Who:** {_user_ctx}\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(db_err)[:300]}```",
                severity="error", error=db_err
            )
            return ORJSONResponse(status_code=500, content={"status": "error", "message": "Error verificando usuario existente."})
        
        if existing.data:
            tenant_id = existing.data[0]["tenant_id"]
            logger.info(f"✅ [ONBOARDING] User already has tenant: {tenant_id} | {_user_ctx}")
            
            # Fetch tenant details
            try:
                tenant_res = await db.table("tenants").select("id, name, is_setup_complete").eq("id", tenant_id).execute()
                tenant_data = tenant_res.data[0] if tenant_res.data else {}
            except Exception as fetch_err:
                logger.warning(
                    f"[{_WHERE}] Failed to fetch tenant details (non-fatal) | "
                    f"tenant_id={tenant_id} | error={str(fetch_err)[:200]}",
                    exc_info=True
                )
                sentry_sdk.capture_exception(fetch_err)
                tenant_data = {}
            
            return {
                "status": "existing",
                "tenant_id": tenant_id,
                "tenant_name": tenant_data.get("name", ""),
                "is_setup_complete": tenant_data.get("is_setup_complete", False),
            }
        
        # --- Step 3: Create new tenant ---
        current_step = "create_tenant"
        tenant_name = user_name  # Will be updated to business name after onboarding
        tenant_payload = {
            "name": tenant_name,
            "llm_provider": "openai",
            "llm_model": "gpt-5.4-mini",
            "system_prompt": "",  # Will be generated by config agent
            "is_active": True,
            "is_setup_complete": False,
            # WhatsApp fields — NULL until manual WABA setup
            "ws_phone_id": None,
            "ws_token": None,
        }
        
        try:
            tenant_res = await db.table("tenants").insert(tenant_payload).execute()
        except Exception as insert_err:
            _msg = (
                f"[{_WHERE}:{current_step}] Tenant INSERT failed | {_user_ctx} | "
                f"env={settings.ENVIRONMENT} | error={str(insert_err)[:200]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(insert_err)
            await send_discord_alert(
                title="❌ Onboarding: Tenant Creation Failed",
                description=f"**Where:** `{_WHERE}:{current_step}`\n**Who:** {_user_ctx}\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(insert_err)[:300]}```",
                severity="error", error=insert_err
            )
            return ORJSONResponse(status_code=500, content={"status": "error", "message": "Error creando tenant."})
        
        if not tenant_res.data:
            _msg = f"[{_WHERE}:{current_step}] Tenant INSERT returned empty data | {_user_ctx} | env={settings.ENVIRONMENT}"
            logger.error(_msg)
            sentry_sdk.capture_message(_msg, level="error")
            await send_discord_alert(
                title="❌ Onboarding: Tenant Creation Empty Response",
                description=f"**Where:** `{_WHERE}:{current_step}`\n**What:** INSERT returned no data (no error but no row)\n**Who:** {_user_ctx}\n**Env:** {settings.ENVIRONMENT}",
                severity="error"
            )
            return ORJSONResponse(status_code=500, content={"status": "error", "message": "Failed to create tenant"})
        
        new_tenant = tenant_res.data[0]
        tenant_id = new_tenant["id"]
        sentry_sdk.set_tag("tenant_id", tenant_id)
        logger.info(f"✅ [ONBOARDING] Tenant created: {tenant_id} ({tenant_name}) | {_user_ctx}")
        
        # --- Step 4: Link user to tenant (admin role) ---
        current_step = "create_tenant_users"
        try:
            await db.table("tenant_users").insert({
                "user_id": user_id,
                "tenant_id": tenant_id,
                "role": "admin",
            }).execute()
            logger.info(f"✅ [ONBOARDING] tenant_users link created | user={user_id} → tenant={tenant_id}")
        except Exception as link_err:
            _msg = (
                f"[{_WHERE}:{current_step}] tenant_users INSERT failed | "
                f"tenant_id={tenant_id} | {_user_ctx} | env={settings.ENVIRONMENT} | "
                f"error={str(link_err)[:200]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(link_err)
            await send_discord_alert(
                title="❌ Onboarding: tenant_users Link Failed",
                description=(
                    f"**Where:** `{_WHERE}:{current_step}`\n"
                    f"**What:** User→Tenant link INSERT failed. Tenant {tenant_id} is ORPHANED.\n"
                    f"**Who:** {_user_ctx}\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(link_err)[:300]}```\n"
                    f"**⚠️ ACTION REQUIRED:** Manual cleanup — delete orphan tenant `{tenant_id}`"
                ),
                severity="error", error=link_err
            )
            return ORJSONResponse(status_code=500, content={"status": "error", "message": "Error vinculando usuario al tenant."})
        
        # --- Step 5: Create onboarding record ---
        current_step = "create_onboarding_record"
        try:
            await db.table("tenant_onboarding").insert({
                "tenant_id": tenant_id,
                "step_current": 1,
            }).execute()
            logger.info(f"✅ [ONBOARDING] Onboarding record created for tenant={tenant_id}")
        except Exception as onb_err:
            # Non-fatal: tenant is created and linked, onboarding can be created later
            _msg = (
                f"[{_WHERE}:{current_step}] tenant_onboarding INSERT failed (non-fatal) | "
                f"tenant_id={tenant_id} | {_user_ctx} | env={settings.ENVIRONMENT} | "
                f"error={str(onb_err)[:200]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(onb_err)
            await send_discord_alert(
                title="⚠️ Onboarding: Onboarding Record Failed (Non-Fatal)",
                description=(
                    f"**Where:** `{_WHERE}:{current_step}`\n"
                    f"**What:** tenant_onboarding INSERT failed. Tenant exists but wizard may not work.\n"
                    f"**Who:** {_user_ctx}\n"
                    f"**Tenant:** `{tenant_id}`\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(onb_err)[:300]}```"
                ),
                severity="warning", error=onb_err
            )
        
        # --- Step 6: Check superadmin status ---
        current_step = "check_superadmin"
        superadmin_emails = settings.SUPERADMIN_EMAILS or ""
        email_list = [e.strip().lower() for e in superadmin_emails.split(",") if e.strip()]
        
        if user_email and user_email.lower() in email_list:
            try:
                await db.table("profiles").update({
                    "is_superadmin": True
                }).eq("id", user_id).execute()
                logger.info(f"👑 [ONBOARDING] User {user_email} marked as superadmin | tenant={tenant_id}")
            except Exception as admin_err:
                # Non-fatal: user is still created, just not marked as superadmin
                _msg = (
                    f"[{_WHERE}:{current_step}] Superadmin UPDATE failed (non-fatal) | "
                    f"tenant_id={tenant_id} | {_user_ctx} | env={settings.ENVIRONMENT} | "
                    f"error={str(admin_err)[:200]}"
                )
                logger.error(_msg, exc_info=True)
                sentry_sdk.capture_exception(admin_err)
                await send_discord_alert(
                    title="⚠️ Onboarding: Superadmin Flag Failed (Non-Fatal)",
                    description=(
                        f"**Where:** `{_WHERE}:{current_step}`\n"
                        f"**What:** profiles UPDATE is_superadmin=true failed\n"
                        f"**Who:** {_user_ctx}\n"
                        f"**Tenant:** `{tenant_id}`\n"
                        f"**Env:** {settings.ENVIRONMENT}\n"
                        f"**Error:** ```{str(admin_err)[:300]}```"
                    ),
                    severity="warning", error=admin_err
                )
        
        # --- Step 7: Notify devs ---
        current_step = "notify_success"
        await send_discord_alert(
            title="🆕 New Tenant Provisioned!",
            description=(
                f"**User:** {user_name} ({user_email})\n"
                f"**Tenant ID:** `{tenant_id}`\n"
                f"**Env:** {settings.ENVIRONMENT}\n"
                f"**Status:** Setup pending\n"
                f"**Superadmin:** {'Yes' if (user_email and user_email.lower() in email_list) else 'No'}"
            ),
            severity="info"
        )
        
        return {
            "status": "created",
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "is_setup_complete": False,
        }
        
    except Exception as e:
        _tb = traceback.format_exc()
        _msg = (
            f"[{_WHERE}:{current_step}] UNEXPECTED failure | "
            f"user_id={user_id} | email={user_email} | tenant_id={tenant_id} | "
            f"env={settings.ENVIRONMENT} | error={str(e)[:300]}"
        )
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Onboarding Provision CRASH at {current_step}",
            description=(
                f"**Where:** `{_WHERE}:{current_step}`\n"
                f"**What:** Unexpected exception during provisioning\n"
                f"**Who:** user_id=`{user_id}` | email=`{user_email}`\n"
                f"**Tenant:** `{tenant_id or 'not yet created'}`\n"
                f"**Env:** {settings.ENVIRONMENT}\n"
                f"**Error:** ```{str(e)[:300]}```\n"
                f"**Traceback (last 500 chars):** ```{_tb[-500:]}```"
            ),
            severity="error",
            error=e
        )
        return ORJSONResponse(
            status_code=500,
            content={"status": "error", "message": "Error interno al crear el tenant."}
        )
