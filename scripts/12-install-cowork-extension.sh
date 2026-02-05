#!/usr/bin/env bash
# ============================================================================
# 12-install-cowork-extension.sh
# Instala la extensión Claude/Cowork en Chrome y Brave
# ============================================================================
set -euo pipefail

GREEN='\033[1;32m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
header(){ echo -e "\n${CYAN}=== $* ===${NC}"; }

# URL de la extensión Claude in Chrome
EXTENSION_URL="https://chromewebstore.google.com/detail/claude/hbpcjcmaepkknjiakjhmmpdkbjdcacoj"
EXTENSION_ID="hbpcjcmaepkknjiakjhmmpdkbjdcacoj"

# ============================================================================
# 1. Detectar navegadores instalados
# ============================================================================
header "DETECTANDO NAVEGADORES"

CHROME_BIN=""
BRAVE_BIN=""

for bin in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$bin" &>/dev/null; then
        CHROME_BIN="$bin"
        break
    fi
done

for bin in brave brave-browser brave-browser-stable; do
    if command -v "$bin" &>/dev/null; then
        BRAVE_BIN="$bin"
        break
    fi
done

[[ -n "$CHROME_BIN" ]] && info "Chrome: $CHROME_BIN" || warn "Chrome no encontrado"
[[ -n "$BRAVE_BIN" ]] && info "Brave: $BRAVE_BIN" || warn "Brave no encontrado"

# ============================================================================
# 2. Configurar políticas para pre-autorizar la extensión
# ============================================================================
header "CONFIGURANDO POLÍTICAS DE EXTENSIÓN"

# Política JSON para permitir la extensión
POLICY_JSON='{
    "ExtensionInstallAllowlist": ["'$EXTENSION_ID'"],
    "ExtensionSettings": {
        "'$EXTENSION_ID'": {
            "installation_mode": "normal_installed",
            "update_url": "https://clients2.google.com/service/update2/crx"
        }
    }
}'

# Chrome policies (Linux)
CHROME_POLICY_DIR="/etc/opt/chrome/policies/managed"
if [[ -n "$CHROME_BIN" ]]; then
    if sudo mkdir -p "$CHROME_POLICY_DIR" 2>/dev/null; then
        echo "$POLICY_JSON" | sudo tee "$CHROME_POLICY_DIR/claude-cowork.json" > /dev/null
        info "Política de Chrome configurada"
    fi
fi

# Brave policies (Linux)
BRAVE_POLICY_DIR="/etc/brave/policies/managed"
if [[ -n "$BRAVE_BIN" ]]; then
    if sudo mkdir -p "$BRAVE_POLICY_DIR" 2>/dev/null; then
        echo "$POLICY_JSON" | sudo tee "$BRAVE_POLICY_DIR/claude-cowork.json" > /dev/null
        info "Política de Brave configurada"
    fi
fi

# ============================================================================
# 3. Abrir Chrome Web Store en ambos navegadores
# ============================================================================
header "ABRIENDO CHROME WEB STORE"

if [[ -n "$CHROME_BIN" ]]; then
    info "Abriendo en Chrome..."
    "$CHROME_BIN" "$EXTENSION_URL" 2>/dev/null &
    sleep 2
fi

if [[ -n "$BRAVE_BIN" ]]; then
    info "Abriendo en Brave..."
    "$BRAVE_BIN" "$EXTENSION_URL" 2>/dev/null &
    sleep 2
fi

# ============================================================================
# 4. Instrucciones para el usuario
# ============================================================================
header "INSTRUCCIONES DE INSTALACIÓN"

echo ""
info "Se han abierto los navegadores en la página de la extensión Claude."
echo ""
echo "Para CADA navegador (Chrome y Brave):"
echo ""
echo "  1. Haz clic en 'Añadir a Chrome' (o 'Add to Chrome')"
echo "  2. Confirma los permisos"
echo "  3. Una vez instalada, haz clic en el icono de Claude (puzzle piece)"
echo "  4. Inicia sesión con tu cuenta Claude (necesitas Claude Pro o Max)"
echo ""
warn "IMPORTANTE para Brave:"
echo "  Si Brave no permite instalar, ve a brave://extensions/"
echo "  y activa 'Allow extensions from other stores'"
echo ""

# ============================================================================
# 5. Verificar instalación
# ============================================================================
header "VERIFICACIÓN"

# Chrome extensions directory
CHROME_EXT_DIR="$HOME/.config/google-chrome/Default/Extensions/$EXTENSION_ID"
BRAVE_EXT_DIR="$HOME/.config/BraveSoftware/Brave-Browser/Default/Extensions/$EXTENSION_ID"

echo ""
info "Después de instalar, verifica que la extensión aparece aquí:"
echo ""
if [[ -n "$CHROME_BIN" ]]; then
    echo "  Chrome: chrome://extensions/"
fi
if [[ -n "$BRAVE_BIN" ]]; then
    echo "  Brave:  brave://extensions/"
fi
echo ""
info "La extensión debería mostrar 'Claude' con el logo de Anthropic."
echo ""

# ============================================================================
# 6. Configurar MCP para browser automation
# ============================================================================
header "CONFIGURANDO MCP PARA BROWSER"

# Verificar que puppeteer MCP está en la config de Claude Desktop
CLAUDE_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"

if [[ -f "$CLAUDE_CONFIG" ]]; then
    if grep -q "puppeteer" "$CLAUDE_CONFIG"; then
        info "MCP puppeteer ya configurado en Claude Desktop"
    else
        warn "Añadiendo puppeteer MCP a Claude Desktop config..."
        # Hacer backup
        cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.bak"

        # Añadir puppeteer si no existe (esto es un poco hacky pero funciona)
        if command -v jq &>/dev/null; then
            jq '.mcpServers.puppeteer = {"command": "npx", "args": ["-y", "@anthropic-ai/mcp-server-puppeteer"]}' \
                "$CLAUDE_CONFIG" > "$CLAUDE_CONFIG.tmp" && mv "$CLAUDE_CONFIG.tmp" "$CLAUDE_CONFIG"
            info "Puppeteer MCP añadido"
        fi
    fi
fi

echo ""
info "Configuración de extensión Cowork completada."
echo ""
warn "Recuerda: Necesitas Claude Pro o Max para usar Cowork."
