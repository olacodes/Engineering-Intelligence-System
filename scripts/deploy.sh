#!/usr/bin/env bash
# deploy.sh
#
# Deploys EIS from a local machine to a Hetzner server over SSH.
#
# Usage:
#   SERVER_HOST=1.2.3.4 bash scripts/deploy.sh
#   SERVER_HOST=1.2.3.4 SERVER_USER=deploy DEPLOY_PATH=/opt/eis bash scripts/deploy.sh
#
# Required:
#   SERVER_HOST   IP address or hostname of the target server
#
# Optional:
#   SERVER_USER   SSH user                  (default: root)
#   DEPLOY_PATH   Remote deployment path    (default: /opt/eis)

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Configuration (args / env / defaults) ─────────────────────────────────────
SERVER_HOST="${SERVER_HOST:-}"
SERVER_USER="${SERVER_USER:-root}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/eis}"

COMPOSE_FILE="docker-compose.prod.yml"

# ── 1. Validate required inputs ───────────────────────────────────────────────
if [[ -z "$SERVER_HOST" ]]; then
    error "SERVER_HOST is not set."
    error "Usage: SERVER_HOST=<ip-or-hostname> bash scripts/deploy.sh"
    exit 1
fi

ok "Deploying to ${SERVER_USER}@${SERVER_HOST}:${DEPLOY_PATH}"

# ── 2. Validate compose file locally before touching the server ───────────────
info "Validating $COMPOSE_FILE..."
if ! docker compose -f "$COMPOSE_FILE" config --quiet 2>&1; then
    error "$COMPOSE_FILE failed validation. Fix the errors above before deploying."
    exit 1
fi
ok "$COMPOSE_FILE is valid."

# ── 3. Rsync project files to the server ─────────────────────────────────────
# Excludes:
#   .env            — secrets must already exist on the server; never overwrite
#   .git/           — version control history is not needed at runtime
#   __pycache__/    — Python bytecode is platform-specific; regenerated on start
#   *.pyc           — compiled bytecode (belt-and-suspenders alongside __pycache__)
#   .DS_Store       — macOS metadata noise
#   node_modules/   — not used by this project, but excluded defensively
info "Syncing project files to ${SERVER_HOST}:${DEPLOY_PATH}..."
rsync -az --delete \
    --exclude='.env' \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='node_modules/' \
    -e "ssh -o StrictHostKeyChecking=accept-new" \
    ./ "${SERVER_USER}@${SERVER_HOST}:${DEPLOY_PATH}/"
ok "Files synced."

# ── 4. Remote deployment steps ────────────────────────────────────────────────
info "Starting remote deployment on ${SERVER_HOST}..."

# All four remote steps run in a single SSH session to avoid repeated
# connection overhead and to ensure they execute in the same shell context.
ssh -o StrictHostKeyChecking=accept-new "${SERVER_USER}@${SERVER_HOST}" \
    DEPLOY_PATH="$DEPLOY_PATH" \
    COMPOSE_FILE="$COMPOSE_FILE" \
    'bash -euo pipefail -s' <<'REMOTE'

    GREEN='\033[0;32m'
    CYAN='\033[0;36m'
    NC='\033[0m'
    info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
    ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }

    cd "$DEPLOY_PATH"

    # 4a. Pull updated base images (no-op if already current)
    info "Pulling latest base images..."
    docker compose -f "$COMPOSE_FILE" pull
    ok "Images up to date."

    # 4b. Build and start services
    info "Building and starting services..."
    docker compose -f "$COMPOSE_FILE" up -d --build
    ok "Services started."

    # 4c. Show final container status
    info "Container status:"
    docker compose -f "$COMPOSE_FILE" ps

REMOTE

ok "Remote deployment complete."

# ── 5. Print public URL ───────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Deployment successful               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Server:${NC}  ${SERVER_USER}@${SERVER_HOST}"
echo -e "  ${CYAN}Path:${NC}    ${DEPLOY_PATH}"
echo -e "  ${CYAN}URL:${NC}     https://\${EIS_DOMAIN}   (as configured in .env on the server)"
echo ""
echo "  To tail logs:"
echo "  ssh ${SERVER_USER}@${SERVER_HOST} 'docker compose -f ${DEPLOY_PATH}/${COMPOSE_FILE} logs -f'"
echo ""
