# Deployment Guide

## Release Tracking

The API and Worker now include release tracking to verify deployed commits.

### Endpoints

**GET /api/v1/meta**
```json
{
  "git_sha": "787467b",
  "build_time": "2025-12-17T12:34:56Z"
}
```

### Environment Variables

Add these to your Render services (API and Worker):

```bash
# Set this to the current commit SHA
GIT_SHA=787467b

# Set this to the build timestamp (optional)
BUILD_TIME=2025-12-17T12:34:56Z
```

### Render Blueprint Setup

Add to your `render.yaml`:

```yaml
services:
  - type: web
    name: topfuelauto-api
    env: python
    envVars:
      - key: GIT_SHA
        sync: false
      - key: BUILD_TIME
        sync: false

  - type: worker
    name: topfuelauto-worker
    env: python
    envVars:
      - key: GIT_SHA
        sync: false
      - key: BUILD_TIME
        sync: false
```

### Manual Setup in Render Dashboard

1. Go to your service (API or Worker)
2. Navigate to **Environment** tab
3. Add environment variable:
   - Key: `GIT_SHA`
   - Value: `787467b` (current commit)
4. Add environment variable:
   - Key: `BUILD_TIME`
   - Value: `2025-12-17T12:34:56Z` (current timestamp)
5. Click **Save Changes**
6. Service will automatically redeploy

### Verification

#### Check API Deployment
```bash
curl https://api.topfuelauto.com/api/v1/meta
```

Expected output:
```json
{
  "git_sha": "787467b",
  "build_time": "2025-12-17T12:34:56Z"
}
```

#### Check Logs

**API Logs:**
```
=== API Starting ===
Git SHA: 787467b
Build Time: 2025-12-17T12:34:56Z
===================
```

**Worker Logs:**
```
=== Worker Starting ===
Git SHA: 787467b
Build Time: 2025-12-17T12:34:56Z
=======================
```

### Troubleshooting

**Issue**: Meta endpoint returns `"unknown"` for git_sha
- **Cause**: GIT_SHA environment variable not set
- **Fix**: Add GIT_SHA env var and redeploy

**Issue**: Worker logs show `unknown` for Git SHA
- **Cause**: Worker service doesn't have GIT_SHA env var
- **Fix**: Add GIT_SHA to worker service env vars (separate from API)

**Issue**: Old commit SHA showing after deployment
- **Cause**: Environment variable not updated
- **Fix**: Update GIT_SHA value in Render dashboard and redeploy

### Deployment Checklist

When deploying a new commit:

- [ ] Get current commit SHA: `git rev-parse --short HEAD`
- [ ] Get current timestamp: `date -u +"%Y-%m-%dT%H:%M:%SZ"`
- [ ] Update API service GIT_SHA env var in Render
- [ ] Update Worker service GIT_SHA env var in Render
- [ ] Update BUILD_TIME env var (optional)
- [ ] Wait for both services to redeploy
- [ ] Verify API: `curl https://api.topfuelauto.com/api/v1/meta`
- [ ] Check API logs for startup message
- [ ] Check Worker logs for startup message
- [ ] Verify functionality (test proxy usage, bot detection, etc.)

### Current Expected Commit

**Production should be on commit: `7a4d28a`**

This commit includes:
- ✅ Comprehensive page debug capture (status, timing, headers, body snippet)
- ✅ Strict bot detection (only HTTP {401,403,429,503} or keyword matches)
- ✅ Debug mode support (disable auto-pause via settings_json["debug"]=true)
- ✅ block_reason strings (http_status:403, keyword_match:cloudflare, etc.)
- ✅ All diagnostics stored in run.debug_json

Previous fixes also included:
- ✅ Issue #1A: DELETE source CASCADE handling (Core DELETE + passive_deletes)
- ✅ Issue #1B: CORS headers on all errors
- ✅ Issue #2: Proxy from Proxy Pool applied correctly
- ✅ Issue #3: Conservative bot detection (no false BLOCKED on 200)
- ✅ Issue #4: pages_planned never 0

If you see different behavior, verify the worker is on this commit by checking logs or the meta endpoint.
