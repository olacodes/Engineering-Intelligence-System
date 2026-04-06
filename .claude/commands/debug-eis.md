# Debug EIS Deployment

Run this diagnostic sequence on the Hetzner server and report findings for each step.
Do NOT apply any fixes until I confirm.

## Container State

Run: `docker compose -f docker-compose.prod.yml ps`
Expected: both eis-app and eis-qdrant show "running", restart count = 0

## Recent Logs (last 100 lines each)

Run: `docker compose -f docker-compose.prod.yml logs --tail=100 eis`
Run: `docker compose -f docker-compose.prod.yml logs --tail=100 qdrant`
Flag: any ERROR, CRITICAL, or traceback lines

## Network Check

Run: `docker network inspect eis_eis-network`
Confirm: both containers are attached to the same network

## Disk Space

Run: `df -h /`
Flag: if usage > 80%

## Memory Pressure

Run: `free -h` and `docker stats --no-stream`
Flag: if any container is using > 80% of its limit

## Environment Variables (safe check — no secret values)

Run: `docker compose -f docker-compose.prod.yml config | grep -E "^[[:space:]]+(ENVIRONMENT|DEBUG|API_HOST|QDRANT_URL|LLM_MODEL)"`
Confirm: ENVIRONMENT=production, DEBUG=false

## Summarise

After all checks, give me a one-paragraph diagnosis and rank the issues by likely impact.
