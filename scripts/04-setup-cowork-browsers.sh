#!/usr/bin/env bash
# ============================================================================
# 04-setup-cowork-browsers.sh
# Configura Claude Cowork, la extensión Claude in Chrome para Brave y Chrome
# ============================================================================
set -euo pipefail

YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
CYAN='\033[1;36m'
MAGENTA='\033[1;35m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
header(){ echo -e "${CYAN}=== $* ===${NC}"; }
note()  { echo -e "${MAGENTA}[NOTA]${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../config/.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

# ============================================================================
# 1. Instalar Claude Desktop App (requerida para Cowork)
# ============================================================================
header "CLAUDE DESKTOP APP (requerida para Cowork)"

if command -v claude-desktop &>/dev/null || [[ -d "/opt/Claude" ]] || [[ -f "$HOME/.local/share/applications/claude.desktop" ]]; then
    info "Claude Desktop App parece estar instalada."
else
    info "Claude Desktop App es necesaria para Cowork."
    info ""
    info "Descarga desde: https://claude.ai/download"
    info ""

    # Intentar instalar automáticamente en Linux
    if command -v dpkg &>/dev/null; then
        ARCH=$(uname -m)
        case "$ARCH" in
            x86_64|amd64) DEB_ARCH="amd64" ;;
            aarch64|arm64) DEB_ARCH="arm64" ;;
            *) DEB_ARCH="" ;;
        esac

        if [[ -n "$DEB_ARCH" ]]; then
            read -rp "¿Intentar descarga automática de Claude Desktop? (s/n): " AUTO_DL
            if [[ "$AUTO_DL" =~ ^[sS]$ ]]; then
                TEMP_DEB="/tmp/claude-desktop.deb"
                info "Descargando Claude Desktop..."
                curl -fsSL -o "$TEMP_DEB" "https://claude.ai/download/linux/${DEB_ARCH}" 2>/dev/null && {
                    sudo dpkg -i "$TEMP_DEB" 2>/dev/null || sudo apt-get install -f -y
                    rm -f "$TEMP_DEB"
                    info "Claude Desktop instalado."
                } || {
                    warn "Descarga automática falló."
                    info "Descarga manualmente desde: https://claude.ai/download"
                }
            fi
        fi
    fi
fi

# ============================================================================
# 2. Configurar Cowork
# ============================================================================
header "CONFIGURANDO CLAUDE COWORK"

info "Cowork es una funcionalidad integrada en Claude Desktop App."
info ""
note "Requisitos para Cowork:"
note "  1. Suscripción Claude Max ($100-200/mes)"
note "  2. Claude Desktop App instalada"
note "  3. macOS (Windows en desarrollo, Linux experimental)"
info ""
info "Para activar Cowork:"
info "  1. Abre Claude Desktop App"
info "  2. Inicia sesión con tu cuenta Claude Max"
info "  3. Selecciona 'Cowork' desde el menú principal"
info "  4. Apunta Claude a la carpeta del proyecto:"
info "     $(pwd)"
info ""

# Crear directorio de proyecto para Cowork
COWORK_DIR="$HOME/.claude/cowork"
mkdir -p "$COWORK_DIR"

# Crear configuración de Cowork skills
cat > "$COWORK_DIR/skills.json" << EOF
{
    "projectDirectory": "/home/user/claudio",
    "skills": [
        {
            "name": "google-cloud-deploy",
            "description": "Deploy to Google Cloud Run",
            "triggers": ["deploy", "publicar", "subir a la nube"]
        },
        {
            "name": "gcs-file-sync",
            "description": "Sync files to Google Cloud Storage",
            "triggers": ["sync", "sincronizar", "backup"]
        }
    ],
    "connectors": {
        "googleCloud": true,
        "github": true
    }
}
EOF
info "Configuración de Cowork skills creada en: $COWORK_DIR/skills.json"

# ============================================================================
# 3. Instalar extensión Claude in Chrome
# ============================================================================
header "CLAUDE IN CHROME - EXTENSIÓN PARA NAVEGADORES"

CHROME_EXT_URL="https://chromewebstore.google.com/detail/claude/hbpcjcmaepkknjiakjhmmpdkbjdcacoj"

info ""
info "La extensión 'Claude in Chrome' permite a Claude interactuar con el navegador."
info "Funciona tanto en Google Chrome como en Brave (basado en Chromium)."
info ""

# --- Google Chrome ---
header "GOOGLE CHROME"
CHROME_BIN=""
for bin in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$bin" &>/dev/null; then
        CHROME_BIN="$bin"
        break
    fi
done

if [[ -n "$CHROME_BIN" ]]; then
    info "Google Chrome encontrado: $CHROME_BIN"
    info "  Versión: $($CHROME_BIN --version 2>/dev/null || echo 'desconocida')"
else
    info "Google Chrome no encontrado. Instalando..."
    if command -v apt-get &>/dev/null; then
        read -rp "¿Instalar Google Chrome? (s/n): " INSTALL_CHROME
        if [[ "$INSTALL_CHROME" =~ ^[sS]$ ]]; then
            TEMP_DEB="/tmp/google-chrome.deb"
            curl -fsSL -o "$TEMP_DEB" "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" 2>/dev/null && {
                sudo dpkg -i "$TEMP_DEB" 2>/dev/null || sudo apt-get install -f -y
                rm -f "$TEMP_DEB"
                info "Google Chrome instalado."
                CHROME_BIN="google-chrome-stable"
            } || warn "No se pudo instalar Chrome."
        fi
    else
        info "Descarga Chrome desde: https://www.google.com/chrome/"
    fi
fi

# --- Brave Browser ---
header "BRAVE BROWSER"
BRAVE_BIN=""
for bin in brave brave-browser brave-browser-stable; do
    if command -v "$bin" &>/dev/null; then
        BRAVE_BIN="$bin"
        break
    fi
done

if [[ -n "$BRAVE_BIN" ]]; then
    info "Brave Browser encontrado: $BRAVE_BIN"
    info "  Versión: $($BRAVE_BIN --version 2>/dev/null || echo 'desconocida')"
else
    info "Brave Browser no encontrado. Instalando..."
    if command -v apt-get &>/dev/null; then
        read -rp "¿Instalar Brave Browser? (s/n): " INSTALL_BRAVE
        if [[ "$INSTALL_BRAVE" =~ ^[sS]$ ]]; then
            sudo curl -fsSLo /usr/share/keyrings/brave-browser-archive-keyring.gpg \
                https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg 2>/dev/null
            echo "deb [signed-by=/usr/share/keyrings/brave-browser-archive-keyring.gpg] https://brave-browser-apt-release.s3.brave.com/ stable main" | \
                sudo tee /etc/apt/sources.list.d/brave-browser-release.list > /dev/null
            sudo apt-get update -qq 2>/dev/null
            sudo apt-get install -y brave-browser 2>/dev/null && {
                info "Brave Browser instalado."
                BRAVE_BIN="brave-browser"
            } || warn "No se pudo instalar Brave."
        fi
    else
        info "Descarga Brave desde: https://brave.com/linux/"
    fi
fi

# ============================================================================
# 4. Configurar extensión Claude en ambos navegadores
# ============================================================================
header "INSTRUCCIONES PARA INSTALAR LA EXTENSIÓN CLAUDE"

info ""
info "Instala la extensión 'Claude in Chrome' en AMBOS navegadores:"
info ""
info "  URL: $CHROME_EXT_URL"
info ""
info "  GOOGLE CHROME:"
info "    1. Abre Chrome y ve a: $CHROME_EXT_URL"
info "    2. Haz clic en 'Añadir a Chrome'"
info "    3. Inicia sesión con tu cuenta Claude"
info ""
info "  BRAVE BROWSER:"
info "    1. Abre Brave y ve a: $CHROME_EXT_URL"
info "    2. Brave te pedirá permitir extensiones del Chrome Web Store"
info "    3. Haz clic en 'Añadir a Brave'"
info "    4. Inicia sesión con tu cuenta Claude"
info ""
note "  IMPORTANTE: Brave es compatible con extensiones de Chrome Web Store"
note "  ya que está basado en Chromium."
info ""

# Crear script helper para abrir la extensión en ambos navegadores
HELPER_SCRIPT="${SCRIPT_DIR}/open-claude-extension.sh"
cat > "$HELPER_SCRIPT" << 'EOF'
#!/usr/bin/env bash
# Abre la página de la extensión Claude in Chrome en los navegadores disponibles
EXT_URL="https://chromewebstore.google.com/detail/claude/hbpcjcmaepkknjiakjhmmpdkbjdcacoj"

for browser in google-chrome google-chrome-stable brave brave-browser brave-browser-stable; do
    if command -v "$browser" &>/dev/null; then
        echo "Abriendo en $browser..."
        "$browser" "$EXT_URL" &
    fi
done
EOF
chmod +x "$HELPER_SCRIPT"
info "Script helper creado: $HELPER_SCRIPT"

# ============================================================================
# 5. Configurar políticas de extensiones para integración
# ============================================================================
header "CONFIGURANDO POLÍTICAS DE NAVEGADOR"

# Configurar políticas de Chrome para pre-autorizar la extensión
CHROME_POLICIES_DIR="/etc/opt/chrome/policies/managed"
BRAVE_POLICIES_DIR="/etc/brave/policies/managed"

for POLICY_DIR in "$CHROME_POLICIES_DIR" "$BRAVE_POLICIES_DIR"; do
    if sudo mkdir -p "$POLICY_DIR" 2>/dev/null; then
        sudo tee "$POLICY_DIR/claude-extension.json" > /dev/null 2>&1 << 'POLICY'
{
    "ExtensionInstallAllowlist": [
        "hbpcjcmaepkknjiakjhmmpdkbjdcacoj"
    ],
    "ExtensionSettings": {
        "hbpcjcmaepkknjiakjhmmpdkbjdcacoj": {
            "installation_mode": "normal_installed",
            "update_url": "https://clients2.google.com/service/update2/crx"
        }
    }
}
POLICY
        info "Política de extensiones configurada en: $POLICY_DIR"
    fi
done

# ============================================================================
# 6. Resumen
# ============================================================================
header "RESUMEN"
echo ""
info "Chrome:    ${CHROME_BIN:-'No instalado'}"
info "Brave:     ${BRAVE_BIN:-'No instalado'}"
info "Cowork:    Requiere Claude Desktop App + Claude Max"
info "Extensión: Instalar manualmente desde Chrome Web Store"
echo ""
info "Configuración de navegadores y Cowork completada."
