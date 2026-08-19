#!/usr/bin/env bash
# ============================================================================
# 06-install-ai-tools.sh
# Instala/configura clientes de IA adicionales: OpenAI Codex CLI, accesos
# tipo app (PWA) para ChatGPT y Perplexity, y GitHub CLI.
#
# IMPORTANTE: ChatGPT y Perplexity no publican cliente de escritorio oficial
# para Linux. Este script instala lo que SÍ es instalable por línea de
# comandos (Codex CLI, gh CLI) y crea accesos "modo app" (PWA) para los
# demás, que abren en una ventana propia sin barra de navegador.
# ============================================================================
set -euo pipefail

YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
CYAN='\033[1;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
header(){ echo -e "${CYAN}=== $* ===${NC}"; }

# ============================================================================
# 1. OpenAI Codex CLI (npm) — agente de código de OpenAI en terminal
# ============================================================================
header "INSTALANDO OPENAI CODEX CLI"

if command -v codex &>/dev/null; then
    info "Codex CLI ya está instalado: $(codex --version 2>/dev/null || echo '')"
elif command -v npm &>/dev/null; then
    info "Instalando @openai/codex vía npm..."
    npm install -g @openai/codex@latest 2>/dev/null && \
        info "Codex CLI instalado. Autentica con: codex login" || \
        warn "No se pudo instalar Codex CLI automáticamente. Instala manualmente: npm install -g @openai/codex"
else
    warn "npm no disponible. Instala Node.js primero (scripts/02 o nvm)."
fi

# ============================================================================
# 2. GitHub CLI (gh) — útil para complementar el MCP de GitHub
# ============================================================================
header "INSTALANDO GITHUB CLI (gh)"

if command -v gh &>/dev/null; then
    info "GitHub CLI ya está instalado: $(gh --version 2>/dev/null | head -1)"
else
    if command -v apt-get &>/dev/null; then
        info "Instalando gh vía apt..."
        (type -p wget >/dev/null || sudo apt-get install -y wget) && \
        sudo mkdir -p -m 755 /etc/apt/keyrings && \
        wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null && \
        sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null && \
        sudo apt-get update -y && sudo apt-get install -y gh && \
        info "GitHub CLI instalado." || warn "No se pudo instalar gh vía apt."
    elif command -v brew &>/dev/null; then
        brew install gh && info "GitHub CLI instalado vía Homebrew."
    else
        warn "Instala gh manualmente: https://github.com/cli/cli#installation"
    fi
fi

# ============================================================================
# 3. Accesos "modo app" (PWA) para ChatGPT y Perplexity
#    No existe cliente de escritorio oficial de ninguno de los dos para
#    Linux; esto crea un .desktop que abre cada servicio en su propia
#    ventana (sin pestañas ni barra de direcciones) usando Chrome/Brave.
# ============================================================================
header "CREANDO ACCESOS DE ESCRITORIO (MODO APP) PARA CHATGPT Y PERPLEXITY"

BROWSER_BIN=""
for b in google-chrome brave-browser chromium chromium-browser; do
    if command -v "$b" &>/dev/null; then
        BROWSER_BIN="$b"
        break
    fi
done

create_pwa_shortcut() {
    local name="$1"
    local url="$2"
    local icon="$3"
    local desktop_dir="$HOME/.local/share/applications"
    mkdir -p "$desktop_dir"

    if [[ -z "$BROWSER_BIN" ]]; then
        warn "No se encontró Chrome/Brave/Chromium. Ejecuta scripts/04-setup-cowork-browsers.sh primero."
        return 1
    fi

    cat > "$desktop_dir/${name// /-}.desktop" << DESKTOPEOF
[Desktop Entry]
Name=${name}
Exec=${BROWSER_BIN} --app=${url} --name=${name// /-}
Terminal=false
Type=Application
Icon=${icon}
Categories=Network;
DESKTOPEOF
    info "Acceso creado: $desktop_dir/${name// /-}.desktop"
}

create_pwa_shortcut "ChatGPT" "https://chatgpt.com" "web-browser"
create_pwa_shortcut "Perplexity" "https://www.perplexity.ai" "web-browser"

echo ""
warn "ChatGPT Plus/Codex (la app web) y Perplexity requieren tu propia cuenta y"
warn "suscripción; este script NO crea cuentas ni introduce credenciales por ti."
warn "Antigravity ya se instala con scripts/03-install-antigravity.sh."

# ============================================================================
# 4. Verificación
# ============================================================================
header "VERIFICACIÓN"
echo ""
info "Codex CLI:    $(command -v codex 2>/dev/null || echo 'No instalado')"
info "GitHub CLI:   $(command -v gh 2>/dev/null || echo 'No instalado')"
info "Navegador:    ${BROWSER_BIN:-No detectado}"
echo ""
info "Herramientas de IA configuradas."
