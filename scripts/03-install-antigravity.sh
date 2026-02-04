#!/usr/bin/env bash
# ============================================================================
# 03-install-antigravity.sh
# Instala Google Antigravity IDE, CLI (agy), y extensiones
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../config/.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

ARCH=$(uname -m)
OS=$(uname -s | tr '[:upper:]' '[:lower:]')

# ============================================================================
# 1. Descargar e instalar Google Antigravity
# ============================================================================
header "INSTALANDO GOOGLE ANTIGRAVITY"

if command -v agy &>/dev/null || command -v antigravity &>/dev/null; then
    info "Antigravity ya está instalado."
    command -v agy &>/dev/null && info "  CLI: agy -> $(which agy)"
    command -v antigravity &>/dev/null && info "  CLI: antigravity -> $(which antigravity)"
else
    info "Descargando Google Antigravity para Linux..."
    info ""
    info "Antigravity debe descargarse desde la página oficial:"
    info "  https://developers.google.com/antigravity"
    info ""

    # Intentar descargar .deb para Debian/Ubuntu
    if command -v dpkg &>/dev/null; then
        info "Sistema detectado: Debian/Ubuntu (dpkg disponible)"
        info ""
        info "Opciones de instalación:"
        info "  1. Descargar manualmente desde: https://developers.google.com/antigravity"
        info "  2. Si tienes el .deb descargado, ejecuta:"
        info "     sudo dpkg -i antigravity-*.deb"
        info "     sudo apt-get install -f"
        info ""

        # Intentar descarga automática si está disponible
        DOWNLOAD_URL=""
        case "$ARCH" in
            x86_64|amd64) DOWNLOAD_URL="https://update.googleapis.com/service/update2/antigravity/linux-x64-stable" ;;
            aarch64|arm64) DOWNLOAD_URL="https://update.googleapis.com/service/update2/antigravity/linux-arm64-stable" ;;
        esac

        if [[ -n "$DOWNLOAD_URL" ]]; then
            read -rp "¿Intentar descarga automática? (s/n): " AUTO_DL
            if [[ "$AUTO_DL" =~ ^[sS]$ ]]; then
                TEMP_DEB="/tmp/antigravity-latest.deb"
                info "Descargando desde $DOWNLOAD_URL ..."
                curl -fsSL -o "$TEMP_DEB" "$DOWNLOAD_URL" 2>/dev/null && {
                    sudo dpkg -i "$TEMP_DEB" 2>/dev/null || sudo apt-get install -f -y
                    rm -f "$TEMP_DEB"
                    info "Antigravity instalado via .deb"
                } || {
                    warn "Descarga automática no disponible."
                    warn "Descarga manualmente desde: https://developers.google.com/antigravity"
                }
            fi
        fi
    elif command -v rpm &>/dev/null; then
        info "Sistema detectado: RPM-based (Fedora/RHEL/etc)"
        info "Descarga el .rpm desde: https://developers.google.com/antigravity"
    elif command -v pacman &>/dev/null; then
        info "Sistema detectado: Arch Linux"
        info "Busca en AUR: yay -S antigravity-bin"
    fi
fi

# ============================================================================
# 2. Configurar CLI (agy)
# ============================================================================
header "CONFIGURANDO CLI (agy)"

# Crear symlink si el binario se instaló como 'antigravity' pero no 'agy'
if command -v antigravity &>/dev/null && ! command -v agy &>/dev/null; then
    info "Creando symlink: agy -> antigravity"
    AGY_PATH=$(which antigravity)
    sudo ln -sf "$AGY_PATH" /usr/local/bin/agy 2>/dev/null || {
        mkdir -p "$HOME/.local/bin"
        ln -sf "$AGY_PATH" "$HOME/.local/bin/agy"
        if ! grep -q ".local/bin" "$HOME/.bashrc" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        fi
    }
    info "Symlink creado. Ahora puedes usar 'agy' desde la terminal."
fi

# ============================================================================
# 3. Instalar Gemini CLI (complemento de Antigravity)
# ============================================================================
header "INSTALANDO GEMINI CLI"

if command -v gemini &>/dev/null; then
    info "Gemini CLI ya está instalado: $(gemini --version 2>/dev/null || echo '')"
else
    info "Instalando Gemini CLI..."
    npm install -g @anthropic-ai/claude-code@latest 2>/dev/null || true

    # Gemini CLI se instala via npm
    if command -v npm &>/dev/null; then
        npm install -g @google/gemini-cli@latest 2>/dev/null && \
            info "Gemini CLI instalado." || \
            warn "No se pudo instalar Gemini CLI via npm."
    else
        warn "npm no disponible. Instala Node.js primero."
    fi
fi

# ============================================================================
# 4. Instalar extensión Claude Code en Antigravity
# ============================================================================
header "INSTALANDO EXTENSIÓN CLAUDE CODE EN ANTIGRAVITY"

install_extension() {
    local EXT_ID="$1"
    local EXT_NAME="$2"

    # Antigravity usa el mismo sistema de extensiones que VS Code
    for cmd in agy antigravity; do
        if command -v "$cmd" &>/dev/null; then
            info "Instalando extensión '$EXT_NAME' en Antigravity..."
            "$cmd" --install-extension "$EXT_ID" 2>/dev/null && {
                info "  '$EXT_NAME' instalada correctamente."
                return 0
            }
        fi
    done

    warn "  No se pudo instalar '$EXT_NAME' automáticamente."
    info "  Instálala manualmente desde Antigravity: Extensions > Buscar '$EXT_NAME'"
    return 1
}

# Extensiones clave
install_extension "anthropic.claude-code" "Claude Code" || true
install_extension "google.geminicodeassist" "Gemini Code Assist" || true
install_extension "googlecloudtools.cloudcode" "Google Cloud Code" || true

# ============================================================================
# 5. Configurar Antigravity para Google Cloud
# ============================================================================
header "CONFIGURANDO ANTIGRAVITY CON GOOGLE CLOUD"

# Configuración de settings para Antigravity (formato JSON, compatible con VS Code)
AGY_CONFIG_DIR="$HOME/.config/Antigravity/User"
mkdir -p "$AGY_CONFIG_DIR"

AGY_SETTINGS="$AGY_CONFIG_DIR/settings.json"

if [[ -f "$AGY_SETTINGS" ]]; then
    info "Archivo de settings existente encontrado. Haciendo backup..."
    cp "$AGY_SETTINGS" "${AGY_SETTINGS}.backup.$(date +%s)"
fi

GCP_PROJECT="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo 'YOUR_PROJECT_ID')}"

cat > "$AGY_SETTINGS" << EOF
{
    "// Configuración generada por claudio setup": true,

    "antigravity.agent.defaultModel": "gemini-3-pro",
    "antigravity.agent.enableBrowser": true,
    "antigravity.agent.enableTerminal": true,

    "cloudcode.project": "${GCP_PROJECT}",
    "cloudcode.enableTelemetry": false,

    "editor.fontSize": 14,
    "editor.wordWrap": "on",
    "terminal.integrated.defaultProfile.linux": "bash",

    "extensions.autoUpdate": true,
    "extensions.autoCheckUpdates": true
}
EOF

info "Settings de Antigravity configurados en: $AGY_SETTINGS"

# ============================================================================
# 6. Verificación
# ============================================================================
header "VERIFICACIÓN"
echo ""
info "Antigravity:  $(command -v agy 2>/dev/null || command -v antigravity 2>/dev/null || echo 'No instalado - descargar manualmente')"
info "Gemini CLI:   $(command -v gemini 2>/dev/null || echo 'No instalado')"
info "Proyecto GCP: $GCP_PROJECT"
echo ""
info "Para abrir Antigravity en este proyecto:"
info "  agy /home/user/claudio"
echo ""
info "Para abrir el Manager (agentes):"
info "  Ctrl+Shift+P > 'Antigravity: Open Manager'"
echo ""
info "Configuración de Antigravity completada."
