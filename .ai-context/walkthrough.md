# Phase 1D Walkthrough: Backend Deploy Pipeline Fix

## Problem
Cloud Build trigger was failing to deploy the backend to Cloud Run after every push to `main`. Multiple consecutive FAILURE builds with no new revisions deployed.

## Root Causes Found (3 separate issues, each backed by official docs)

### 1. IAM Permissions Missing
**Error:** `Permission 'iam.serviceaccounts.actAs' denied on service account ia-calendar-bot@...`
**Doc:** [Cloud Build IAM](https://cloud.google.com/build/docs/securing-builds/configure-access-control)
**Fix:** Granted 3 roles to `ia-calendar-bot@saas-javiera.iam.gserviceaccount.com`:
- `roles/cloudbuild.builds.builder`
- `roles/run.admin`
- `roles/iam.serviceAccountUser` ← root cause of the specific error

### 2. Trigger Had No Deploy Step
**Error:** Build succeeded (`docker build` + image push) but no new revision was created on Cloud Run.
**Doc:** [Cloud Build Deploy to Cloud Run](https://cloud.google.com/build/docs/deploying-builds/deploy-cloud-run)
**Fix:** Added 3-step pipeline to trigger:
```yaml
steps:
- id: Build    # docker build
- id: Push     # docker push
- id: Deploy   # gcloud run services update --image=...
```

### 3. Secrets Not in Secret Manager
**Error:** `pydantic_core.ValidationError: 5 validation errors for Settings` — WHATSAPP_VERIFY_TOKEN, OPENAI_API_KEY, etc. missing at runtime.
**Doc:** [Configure secrets for Cloud Run](https://cloud.google.com/run/docs/configuring/services/secrets)
**Root cause:** Previous deploys via `gcloud run deploy --source .` (buildpacks) had secrets baked into the image at build time. Custom Dockerfile doesn't have this — secrets must be explicitly configured via Secret Manager.
**Fix:**
1. Created `WHATSAPP_VERIFY_TOKEN` secret in Secret Manager
2. Granted `roles/secretmanager.secretAccessor` to SA for all 6 secrets
3. Configured service with `--update-secrets` flag — secrets now injected at startup via `secretKeyRef`

## Verification Results

| Check | Result |
|:---|:---|
| Build `c1c97b1b` | ✅ SUCCESS (3 steps) |
| Revision `00046-hfx` | ✅ Active, Ready=True |
| Traffic | ✅ 100% on latest |
| API `/api/debug-ping` | ✅ 200 OK |
| Secrets in revision spec | ✅ 6 `secretKeyRef` entries confirmed |
| Auto-trigger on push | ✅ Push to main fires Build→Push→Deploy |

## Documentation Updated
- `README.md` — Full trigger YAML, Secret Manager table, IAM commands, warnings
- `implementation_plan.md` — Phase 1D marked COMPLETE
- `task.md` — All 1D subtasks checked off

## Key Lesson
The entire issue chain was solvable by reading the official docs. Three separate doc pages each contained the exact fix for their respective issue. The "Docs-First" rule prevented further wheel-reinvention.
