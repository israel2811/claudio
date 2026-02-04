#!/usr/bin/env bash
# ============================================================================
# setup.sh - Script maestro de instalación
# Configura Antigravity + Claude Code + Cowork con Google Cloud
# ============================================================================
set -euo pipefail

CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
MAGENTA='\033[1;35m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
header(){ echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${SCRIPT_DIR}/scripts"

# ============================================================================
# Banner
# ============================================================================
echo -e "${MAGENTA}"
cat << 'BANNER'

   ██████╗██╗      █████╗ ██╗   ██╗██████╗ ██╗ ██████╗
  ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██║██╔═══██╗
  ██║     ██║     ███████║██║   ██║██║  ██║██║██║   ██║
  ██║     ██║     ██╔══██║██║   ██║██║  ██║██║██║   ██║
  ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝██║╚██████╔╝
   ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝

  Local Development + Google Cloud Setup
  Antigravity + Claude Code + Cowork

BANNER
echo -e "${NC}"

# ============================================================================
# Verificar archivo .env
# ============================================================================
ENV_FILE="${SCRIPT_DIR}/config/.env"
if [[ ! -f "$ENV_FILE" ]] || [[ ! -s "$ENV_FILE" ]]; then
    if [[ -f "${SCRIPT_DIR}/config/.env.example" ]]; then
        cp "${SCRIPT_DIR}/config/.env.example" "$ENV_FILE"
        warn "Archivo .env creado desde .env.example"
        warn "Edita config/.env con tu GCP_PROJECT_ID antes de continuar."
    fi
fi

# ============================================================================
# Menú de instalación
# ============================================================================
echo -e "${BOLD}¿Qué deseas instalar?${NC}"
echo ""
echo "  1) Todo (instalación completa)"
echo "  2) Solo Google Cloud SDK"
echo "  3) Solo Claude Code CLI + Vertex AI"
echo "  4) Solo Google Antigravity"
echo "  5) Solo Cowork + Navegadores (Brave/Chrome)"
echo "  6) Solo integraciones MCP"
echo "  0) Salir"
echo ""
read -rp "Selecciona una opción [1-6, 0]: " CHOICE

run_script() {
    local script="$1"
    local name="$2"
    if [[ -f "$script" ]]; then
        header "$name"
        chmod +x "$script"
        bash "$script"
        echo ""
        info "$name completado."
    else
        error "Script no encontrado: $script"
    fi
}

case "$CHOICE" in
    1)
        run_script "$SCRIPTS_DIR/01-install-gcloud.sh"          "Google Cloud SDK"
        run_script "$SCRIPTS_DIR/02-install-claude-code.sh"     "Claude Code CLI + Vertex AI"
        run_script "$SCRIPTS_DIR/03-install-antigravity.sh"     "Google Antigravity"
        run_script "$SCRIPTS_DIR/04-setup-cowork-browsers.sh"   "Cowork + Navegadores"
        run_script "$SCRIPTS_DIR/05-setup-mcp-integration.sh"   "Integraciones MCP"
        ;;
    2) run_script "$SCRIPTS_DIR/01-install-gcloud.sh"           "Google Cloud SDK" ;;
    3) run_script "$SCRIPTS_DIR/02-install-claude-code.sh"      "Claude Code CLI + Vertex AI" ;;
    4) run_script "$SCRIPTS_DIR/03-install-antigravity.sh"      "Google Antigravity" ;;
    5) run_script "$SCRIPTS_DIR/04-setup-cowork-browsers.sh"    "Cowork + Navegadores" ;;
    6) run_script "$SCRIPTS_DIR/05-setup-mcp-integration.sh"    "Integraciones MCP" ;;
    0) info "Saliendo."; exit 0 ;;
    *) error "Opción inválida: $CHOICE" ;;
esac

# ============================================================================
# Resumen final
# ============================================================================
header "INSTALACIÓN COMPLETADA"

echo -e "${BOLD}Herramientas configuradas:${NC}"
echo ""

check_tool() {
    local name="$1"
    local cmd="$2"
    if command -v "$cmd" &>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} $name ($cmd)"
    else
        echo -e "  ${RED}[--]${NC} $name (no encontrado: $cmd)"
    fi
}

check_tool "Google Cloud SDK"   "gcloud"
check_tool "Claude Code CLI"    "claude"
check_tool "Antigravity"        "agy"
check_tool "Gemini CLI"         "gemini"
check_tool "Google Chrome"      "google-chrome"
check_tool "Brave Browser"      "brave-browser"
check_tool "Node.js"            "node"
check_tool "npm"                "npm"

echo ""
echo -e "${BOLD}Archivos de configuración:${NC}"
echo ""
for f in "$HOME/.claude/mcp.json" "$HOME/.claude/.env" "$HOME/.config/Antigravity/User/settings.json" "$HOME/.config/Antigravity/User/mcp.json" "$HOME/.config/Claude/claude_desktop_config.json"; do
    if [[ -f "$f" ]]; then
        echo -e "  ${GREEN}[OK]${NC} $f"
    else
        echo -e "  ${RED}[--]${NC} $f"
    fi
done

echo ""
echo -e "${BOLD}Próximos pasos:${NC}"
echo ""
echo "  1. Edita config/.env con tu GCP_PROJECT_ID"
echo "  2. Ejecuta: source ~/.bashrc"
echo "  3. Verifica Google Cloud: gcloud auth list"
echo "  4. Verifica Claude Code: claude /status"
echo "  5. Abre Antigravity: agy /home/user/claudio"
echo "  6. Instala la extensión Claude in Chrome en Brave y Chrome"
echo "  7. Activa Cowork desde Claude Desktop App"
echo ""
info "Documentación completa en README.md"
