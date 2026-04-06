#!/usr/bin/env bash
# bootstrap-hetzner.sh
#
# Prepares a fresh Hetzner CX22 (Ubuntu 24.04) server for EIS deployment.
# Idempotent: safe to run multiple times — each step checks before acting.
#
# Usage:
#   bash bootstrap-hetzner.sh

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }

# ── 1. System update ──────────────────────────────────────────────────────────
info "Updating system packages..."
apt-get update -q
apt-get upgrade -y -q
success "System packages up to date."

# ── 2. Docker ─────────────────────────────────────────────────────────────────
if command -v docker &>/dev/null; then
    warn "Docker already installed ($(docker --version)). Skipping."
else
    info "Installing Docker via get.docker.com..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
    success "Docker installed and started."
fi

# ── 3. Add current user to docker group ───────────────────────────────────────
# SUDO_USER is set when running via sudo; fall back to USER otherwise.
TARGET_USER="${SUDO_USER:-$USER}"
if id -nG "$TARGET_USER" | grep -qw docker; then
    warn "User '$TARGET_USER' is already in the docker group. Skipping."
else
    info "Adding '$TARGET_USER' to the docker group..."
    usermod -aG docker "$TARGET_USER"
    success "User '$TARGET_USER' added to docker group."
    warn "Group membership takes effect on next login. Run 'newgrp docker' to apply now."
fi

# ── 4. Caddy ──────────────────────────────────────────────────────────────────
if command -v caddy &>/dev/null; then
    warn "Caddy already installed ($(caddy version)). Skipping."
else
    info "Installing Caddy from the official Cloudsmith apt repository..."

    apt-get install -y -q debian-keyring debian-archive-keyring apt-transport-https curl

    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        | tee /etc/apt/sources.list.d/caddy-stable.list

    apt-get update -q
    apt-get install -y -q caddy

    systemctl enable --now caddy
    success "Caddy installed and started."
fi

# ── 5. Create /opt/eis with correct permissions ───────────────────────────────
EIS_DIR="/opt/eis"

if [[ -d "$EIS_DIR" ]]; then
    warn "$EIS_DIR already exists. Skipping directory creation."
else
    info "Creating $EIS_DIR..."
    mkdir -p "$EIS_DIR"
    success "$EIS_DIR created."
fi

# Ensure the deploying user owns the directory so they can write files without sudo.
chown "${TARGET_USER}:${TARGET_USER}" "$EIS_DIR"
chmod 750 "$EIS_DIR"
success "Permissions set on $EIS_DIR (owner: $TARGET_USER, mode: 750)."

# ── 6. Create .env.example ────────────────────────────────────────────────────
ENV_EXAMPLE="$EIS_DIR/.env.example"

if [[ -f "$ENV_EXAMPLE" ]]; then
    warn "$ENV_EXAMPLE already exists. Skipping."
else
    info "Writing $ENV_EXAMPLE..."
    cat > "$ENV_EXAMPLE" <<'EOF'
# EIS production environment variables
# Copy this file to .env and fill in every value before starting the stack.
#
#   cp /opt/eis/.env.example /opt/eis/.env
#   chmod 600 /opt/eis/.env   # restrict read access
#   nano /opt/eis/.env

# Qdrant authentication key — choose a strong random string.
QDRANT_API_KEY=

# OpenAI API key used for generating embeddings (text-embedding-3-large).
EMBEDDING_API_KEY=

# Anthropic API key used by the LLM service.
ANTHROPIC_API_KEY=

# Claude model to use, e.g. claude-sonnet-4-6
LLM_MODEL=

# Comma-separated list of allowed CORS origins, JSON-encoded.
# Example: '["https://yourdomain.com"]'
CORS_ORIGINS=
EOF
    chown "${TARGET_USER}:${TARGET_USER}" "$ENV_EXAMPLE"
    chmod 640 "$ENV_EXAMPLE"
    success "$ENV_EXAMPLE written."
fi

# ── 7. Next steps ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Bootstrap complete — next steps                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}1. Fill in secrets${NC}"
echo "     cp /opt/eis/.env.example /opt/eis/.env"
echo "     chmod 600 /opt/eis/.env"
echo "     nano /opt/eis/.env          # set all values"
echo ""
echo -e "  ${CYAN}2. Copy project files to the server${NC}"
echo "     rsync -av --exclude='.git' --exclude='__pycache__' \\"
echo "       ./ user@<server-ip>:/opt/eis/"
echo ""
echo -e "  ${CYAN}3. Start the stack${NC}"
echo "     cd /opt/eis"
echo "     docker compose -f docker-compose.prod.yml --env-file .env up -d"
echo ""
echo -e "  ${CYAN}4. Configure Caddy${NC}"
echo "     Edit /etc/caddy/Caddyfile to reverse-proxy your domain to localhost:8000,"
echo "     then run: systemctl reload caddy"
echo ""
if id -nG "$TARGET_USER" | grep -qw docker; then
    : # already in group, no extra warning needed
else
    echo -e "  ${YELLOW}NOTE:${NC} Log out and back in (or run 'newgrp docker') so"
    echo "        '$TARGET_USER' can run docker without sudo."
    echo ""
fi
