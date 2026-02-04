#!/usr/bin/env bash
# ============================================================================
# 10-setup-antigravity-full.sh
# Configuración completa de Google Antigravity con todas las extensiones,
# Jules, NotebookLM, CLI y integración con Claude Code
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
header(){ echo -e "\n${CYAN}=== $* ===${NC}"; }
subheader(){ echo -e "${MAGENTA}--- $* ---${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."
ENV_FILE="${PROJECT_DIR}/config/.env"

# Cargar variables de entorno
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

GCP_PROJECT="${GCP_PROJECT_ID:-YOUR_PROJECT_ID}"

# ============================================================================
# 1. Verificar instalación de Antigravity
# ============================================================================
header "VERIFICANDO ANTIGRAVITY"

ANTIGRAVITY_PATH=""
AGY_CMD=""

# Buscar Antigravity instalado
if command -v agy &>/dev/null; then
    AGY_CMD="agy"
    info "CLI 'agy' encontrado"
elif command -v antigravity &>/dev/null; then
    AGY_CMD="antigravity"
    info "CLI 'antigravity' encontrado"
elif [[ -f "/usr/bin/antigravity" ]]; then
    AGY_CMD="/usr/bin/antigravity"
elif [[ -f "$HOME/.local/bin/antigravity" ]]; then
    AGY_CMD="$HOME/.local/bin/antigravity"
elif [[ -d "/opt/Antigravity" ]]; then
    AGY_CMD="/opt/Antigravity/antigravity"
elif [[ -d "$HOME/Antigravity" ]]; then
    AGY_CMD="$HOME/Antigravity/antigravity"
elif [[ -d "$HOME/Desktop/Antigravity" ]]; then
    AGY_CMD="$HOME/Desktop/Antigravity/antigravity"
    info "Antigravity encontrado en Desktop"
fi

if [[ -z "$AGY_CMD" ]]; then
    warn "Antigravity no encontrado automáticamente."
    info "Buscando en ubicaciones comunes..."

    # Buscar en el sistema
    FOUND_PATH=$(find /opt /usr /home -name "antigravity" -type f -executable 2>/dev/null | head -1)
    if [[ -n "$FOUND_PATH" ]]; then
        AGY_CMD="$FOUND_PATH"
        info "Encontrado: $AGY_CMD"
    else
        warn "No se encontró Antigravity instalado."
        warn "Si ya lo tienes, indica la ruta."
    fi
fi

# ============================================================================
# 2. Crear symlink 'agy' si no existe
# ============================================================================
header "CONFIGURANDO CLI 'agy'"

if [[ -n "$AGY_CMD" ]] && ! command -v agy &>/dev/null; then
    info "Creando symlink 'agy'..."
    if [[ -w "/usr/local/bin" ]]; then
        sudo ln -sf "$AGY_CMD" /usr/local/bin/agy
        info "Symlink creado: /usr/local/bin/agy"
    elif [[ -d "$HOME/.local/bin" ]]; then
        ln -sf "$AGY_CMD" "$HOME/.local/bin/agy"
        info "Symlink creado: ~/.local/bin/agy"
        warn "Asegúrate de que ~/.local/bin esté en tu PATH"
    fi
fi

# ============================================================================
# 3. Configurar directorio de settings de Antigravity
# ============================================================================
header "CONFIGURANDO SETTINGS DE ANTIGRAVITY"

AGY_CONFIG_DIR="$HOME/.config/Antigravity/User"
mkdir -p "$AGY_CONFIG_DIR"

# ============================================================================
# 4. Configurar settings.json de Antigravity
# ============================================================================
subheader "Configurando settings.json"

AGY_SETTINGS="$AGY_CONFIG_DIR/settings.json"

cat > "$AGY_SETTINGS" << SETTINGSEOF
{
    "// === MODELOS Y AI ===": "",
    "antigravity.defaultModel": "gemini-3-pro",
    "antigravity.claudeModel": "claude-opus-4-5-thinking",
    "antigravity.enableClaudeCode": true,
    "antigravity.enableJules": true,
    "antigravity.agentAutoApprove": false,

    "// === GOOGLE CLOUD ===": "",
    "antigravity.googleCloud.projectId": "${GCP_PROJECT}",
    "antigravity.googleCloud.region": "us-central1",
    "antigravity.vertexAI.enabled": true,

    "// === MCP SERVERS ===": "",
    "antigravity.mcp.enabled": true,
    "antigravity.mcp.configPath": "${AGY_CONFIG_DIR}/mcp.json",

    "// === JULES ===": "",
    "antigravity.jules.enabled": true,
    "antigravity.jules.autoSync": true,
    "antigravity.jules.projectPath": "/home/user/claudio",

    "// === MANAGER (AGENTES) ===": "",
    "antigravity.manager.enabled": true,
    "antigravity.manager.artifactsPath": "${HOME}/.antigravity/artifacts",
    "antigravity.manager.autoSaveArtifacts": true,

    "// === BROWSER INTEGRATION ===": "",
    "antigravity.browser.enabled": true,
    "antigravity.browser.headless": false,
    "antigravity.browser.screenshots": true,

    "// === EDITOR ===": "",
    "editor.fontSize": 14,
    "editor.fontFamily": "'JetBrains Mono', 'Fira Code', monospace",
    "editor.tabSize": 2,
    "editor.formatOnSave": true,
    "editor.minimap.enabled": false,

    "// === TERMINAL ===": "",
    "terminal.integrated.fontSize": 13,
    "terminal.integrated.fontFamily": "'JetBrains Mono', monospace",

    "// === EXTENSIONES RECOMENDADAS ===": "",
    "extensions.autoUpdate": true,

    "// === TELEMETRÍA ===": "",
    "telemetry.telemetryLevel": "off"
}
SETTINGSEOF

info "Settings de Antigravity configurados"

# ============================================================================
# 5. Configurar extensiones recomendadas
# ============================================================================
header "CONFIGURANDO EXTENSIONES"

# Lista de extensiones recomendadas para Antigravity
EXTENSIONS=(
    # Claude Code
    "anthropic.claude-code"

    # Desarrollo
    "dbaeumer.vscode-eslint"
    "esbenp.prettier-vscode"
    "eamodio.gitlens"
    "github.copilot"

    # Google Cloud
    "googlecloudtools.cloudcode"

    # Lenguajes
    "ms-python.python"
    "golang.go"
    "rust-lang.rust-analyzer"

    # Utilidades
    "bradlc.vscode-tailwindcss"
    "formulahendry.auto-rename-tag"
    "christian-kohler.path-intellisense"
)

info "Extensiones recomendadas para instalar en Antigravity:"
for ext in "${EXTENSIONS[@]}"; do
    echo "  - $ext"
done

# Intentar instalar extensiones si agy está disponible
if [[ -n "$AGY_CMD" ]]; then
    subheader "Instalando extensiones..."
    for ext in "${EXTENSIONS[@]}"; do
        info "Instalando: $ext"
        "$AGY_CMD" --install-extension "$ext" 2>/dev/null || warn "No se pudo instalar $ext"
    done
fi

# ============================================================================
# 6. Configurar integración con Jules
# ============================================================================
header "CONFIGURANDO INTEGRACIÓN CON JULES"

JULES_CONFIG_DIR="$HOME/.config/jules"
mkdir -p "$JULES_CONFIG_DIR"

cat > "$JULES_CONFIG_DIR/config.json" << JULESEOF
{
    "projectId": "${GCP_PROJECT}",
    "defaultRepository": "/home/user/claudio",
    "autoSync": true,
    "notifications": true,
    "model": "gemini-3-flash",
    "planningCritic": true,
    "mcp": {
        "enabled": true,
        "servers": ["linear", "supabase", "github"]
    }
}
JULESEOF

info "Configuración de Jules creada"

# ============================================================================
# 7. Configurar Claude Code como extensión en Antigravity
# ============================================================================
header "CONFIGURANDO CLAUDE CODE EN ANTIGRAVITY"

# Crear script para abrir Claude Code dentro de Antigravity
cat > "${SCRIPT_DIR}/open-claude-in-antigravity.sh" << 'OPENCEOF'
#!/usr/bin/env bash
# Abre Claude Code dentro de Antigravity
# Uso: ./open-claude-in-antigravity.sh [directorio]

DIR="${1:-$(pwd)}"
AGY_CMD="${AGY_CMD:-agy}"

if command -v "$AGY_CMD" &>/dev/null; then
    # Abrir Antigravity en el directorio
    "$AGY_CMD" "$DIR"

    echo ""
    echo "En Antigravity:"
    echo "  1. Ctrl+Shift+P -> 'Claude Code: Open Panel'"
    echo "  2. O haz clic en el icono de Claude en la barra lateral"
    echo "  3. Usa /init para inicializar Claude Code en el proyecto"
else
    echo "Error: Antigravity no encontrado"
    echo "Instala Antigravity primero: bash scripts/03-install-antigravity.sh"
fi
OPENCEOF

chmod +x "${SCRIPT_DIR}/open-claude-in-antigravity.sh"
info "Script de apertura creado"

# ============================================================================
# 8. Configurar keybindings
# ============================================================================
header "CONFIGURANDO ATAJOS DE TECLADO"

AGY_KEYBINDINGS="$AGY_CONFIG_DIR/keybindings.json"

cat > "$AGY_KEYBINDINGS" << KEYSEOF
[
    {
        "key": "ctrl+shift+c",
        "command": "claude-code.openPanel"
    },
    {
        "key": "ctrl+shift+j",
        "command": "antigravity.openJules"
    },
    {
        "key": "ctrl+shift+m",
        "command": "antigravity.openManager"
    },
    {
        "key": "ctrl+shift+a",
        "command": "antigravity.newAgent"
    },
    {
        "key": "ctrl+enter",
        "command": "antigravity.sendToAgent",
        "when": "editorTextFocus"
    }
]
KEYSEOF

info "Keybindings configurados:"
echo "  Ctrl+Shift+C -> Abrir Claude Code"
echo "  Ctrl+Shift+J -> Abrir Jules"
echo "  Ctrl+Shift+M -> Abrir Manager (agentes)"
echo "  Ctrl+Shift+A -> Nuevo agente"
echo "  Ctrl+Enter   -> Enviar a agente"

# ============================================================================
# 9. Crear archivo de Skills personalizadas
# ============================================================================
header "CONFIGURANDO SKILLS DE ANTIGRAVITY"

SKILLS_DIR="$HOME/.antigravity/skills"
mkdir -p "$SKILLS_DIR"

# Skill: Sincronizar con Claude Code
cat > "$SKILLS_DIR/sync-claude-code/SKILL.md" << 'SKILLEOF'
# Skill: Sincronizar con Claude Code

## Descripción
Sincroniza el contexto actual con Claude Code CLI para trabajo en terminal.

## Triggers
- "sincronizar con claude"
- "sync claude code"
- "pasar a terminal"

## Acciones
1. Guardar contexto actual en ~/.ai-shared-memory/context/
2. Abrir terminal
3. Ejecutar: cd [proyecto] && claude

## Notas
Esta skill permite cambiar fluidamente entre Antigravity (IDE) y Claude Code (terminal).
SKILLEOF

mkdir -p "$SKILLS_DIR/sync-claude-code"
info "Skill 'sync-claude-code' creada"

# ============================================================================
# 10. Resumen
# ============================================================================
header "CONFIGURACIÓN DE ANTIGRAVITY COMPLETADA"

echo ""
info "Archivos configurados:"
echo "  Settings:     $AGY_SETTINGS"
echo "  MCP:          $AGY_CONFIG_DIR/mcp.json"
echo "  Keybindings:  $AGY_KEYBINDINGS"
echo "  Jules:        $JULES_CONFIG_DIR/config.json"
echo "  Skills:       $SKILLS_DIR/"
echo ""
info "Integraciones habilitadas:"
echo "  - Claude Code (extensión + CLI bridge)"
echo "  - Jules (agente asíncrono de Google)"
echo "  - Gemini 3 Pro (modelo por defecto)"
echo "  - Claude Opus 4.5 Thinking (modelo alternativo)"
echo "  - MCP servers compartidos"
echo "  - Manager de agentes"
echo "  - Browser automation"
echo ""
info "Para abrir Antigravity:"
if [[ -n "$AGY_CMD" ]]; then
    echo "  $AGY_CMD /home/user/claudio"
else
    echo "  agy /home/user/claudio  (o busca el ejecutable)"
fi
echo ""
info "Atajos importantes:"
echo "  Ctrl+Shift+C -> Claude Code"
echo "  Ctrl+Shift+J -> Jules"
echo "  Ctrl+Shift+M -> Manager"
