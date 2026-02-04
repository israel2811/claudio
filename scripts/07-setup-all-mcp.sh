#!/usr/bin/env bash
# ============================================================================
# 07-setup-all-mcp.sh
# Configura TODOS los servidores MCP para Claude Code, Antigravity,
# OpenCode y Claude Desktop/Cowork
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
CONFIG_DIR="${PROJECT_DIR}/config"
MCP_TEMPLATES_DIR="${CONFIG_DIR}/mcp"
ENV_FILE="${CONFIG_DIR}/.env"

# ============================================================================
# 0. Cargar variables de entorno
# ============================================================================
if [[ -f "$ENV_FILE" ]]; then
    info "Cargando variables de $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
else
    warn "No se encontró $ENV_FILE. Usando valores por defecto."
    warn "Copia config/.env.example a config/.env y configura tus valores."
fi

GCP_PROJECT="${GCP_PROJECT_ID:-YOUR_PROJECT_ID}"

# ============================================================================
# 1. Verificar requisitos
# ============================================================================
header "VERIFICANDO REQUISITOS"

if ! command -v node &>/dev/null; then
    error "Node.js no instalado. Instálalo primero: https://nodejs.org"
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [[ "$NODE_VERSION" -lt 18 ]]; then
    error "Node.js 18+ requerido. Versión actual: $(node -v)"
fi
info "Node.js $(node -v) OK"

if ! command -v npx &>/dev/null; then
    error "npx no encontrado. Instala npm: npm install -g npm"
fi
info "npx disponible"

# ============================================================================
# 2. Crear directorios necesarios
# ============================================================================
header "CREANDO DIRECTORIOS"

DIRS=(
    "$HOME/.claude"
    "$HOME/.claude/memory"
    "$HOME/.config/Claude"
    "$HOME/.config/Claude/memory"
    "$HOME/.config/Antigravity/User"
    "$HOME/.antigravity/memory"
    "$HOME/.opencode"
    "$HOME/.opencode/memory"
)

for dir in "${DIRS[@]}"; do
    mkdir -p "$dir"
    info "Creado: $dir"
done

# ============================================================================
# 3. Función para procesar templates JSON
# ============================================================================
process_template() {
    local template="$1"
    local output="$2"

    # Reemplazar variables de entorno en el template
    envsubst < "$template" > "$output"
    info "Generado: $output"
}

# ============================================================================
# 4. Configurar Claude Code MCP
# ============================================================================
header "CONFIGURANDO MCP PARA CLAUDE CODE"

CLAUDE_MCP_DIR="$HOME/.claude"
CLAUDE_MCP_FILE="$CLAUDE_MCP_DIR/mcp.json"

# Generar config desde template
if [[ -f "$MCP_TEMPLATES_DIR/claude-code-mcp.json" ]]; then
    # Reemplazar variables
    sed -e "s|\${GCP_PROJECT_ID}|${GCP_PROJECT}|g" \
        -e "s|\${HOME}|${HOME}|g" \
        -e "s|\${OPENAI_API_KEY}|${OPENAI_API_KEY:-}|g" \
        -e "s|\${NOTION_TOKEN}|${NOTION_TOKEN:-}|g" \
        -e "s|\${GITHUB_TOKEN}|${GITHUB_TOKEN:-}|g" \
        -e "s|\${VERCEL_TOKEN}|${VERCEL_TOKEN:-}|g" \
        -e "s|\${SLACK_BOT_TOKEN}|${SLACK_BOT_TOKEN:-}|g" \
        -e "s|\${SLACK_TEAM_ID}|${SLACK_TEAM_ID:-}|g" \
        -e "s|\${LINEAR_API_KEY}|${LINEAR_API_KEY:-}|g" \
        -e "s|\${ASANA_ACCESS_TOKEN}|${ASANA_ACCESS_TOKEN:-}|g" \
        -e "s|\${ZAPIER_API_KEY}|${ZAPIER_API_KEY:-}|g" \
        -e "s|\${N8N_API_URL}|${N8N_API_URL:-}|g" \
        -e "s|\${N8N_API_KEY}|${N8N_API_KEY:-}|g" \
        -e "s|\${GITLAB_TOKEN}|${GITLAB_TOKEN:-}|g" \
        -e "s|\${POSTGRES_CONNECTION_STRING}|${POSTGRES_CONNECTION_STRING:-}|g" \
        -e "s|\${SUPABASE_URL}|${SUPABASE_URL:-}|g" \
        -e "s|\${SUPABASE_KEY}|${SUPABASE_KEY:-}|g" \
        -e "s|\${REDIS_URL}|${REDIS_URL:-}|g" \
        -e "s|\${BRAVE_API_KEY}|${BRAVE_API_KEY:-}|g" \
        -e "s|\${EXA_API_KEY}|${EXA_API_KEY:-}|g" \
        -e "s|\${STRIPE_API_KEY}|${STRIPE_API_KEY:-}|g" \
        -e "s|\${PAYPAL_CLIENT_ID}|${PAYPAL_CLIENT_ID:-}|g" \
        -e "s|\${PAYPAL_CLIENT_SECRET}|${PAYPAL_CLIENT_SECRET:-}|g" \
        -e "s|\${GOOGLE_CLIENT_ID}|${GOOGLE_CLIENT_ID:-}|g" \
        -e "s|\${GOOGLE_CLIENT_SECRET}|${GOOGLE_CLIENT_SECRET:-}|g" \
        -e "s|\${JULES_API_KEY}|${JULES_API_KEY:-}|g" \
        "$MCP_TEMPLATES_DIR/claude-code-mcp.json" > "$CLAUDE_MCP_FILE"
    info "Configuración MCP de Claude Code instalada"
else
    warn "Template claude-code-mcp.json no encontrado"
fi

# ============================================================================
# 5. Configurar Claude Desktop / Cowork MCP
# ============================================================================
header "CONFIGURANDO MCP PARA CLAUDE DESKTOP / COWORK"

CLAUDE_DESKTOP_CONFIG=""
if [[ -d "$HOME/Library/Application Support/Claude" ]]; then
    CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
else
    CLAUDE_DESKTOP_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
fi

if [[ -f "$MCP_TEMPLATES_DIR/claude-desktop-mcp.json" ]]; then
    sed -e "s|\${GCP_PROJECT_ID}|${GCP_PROJECT}|g" \
        -e "s|\${HOME}|${HOME}|g" \
        -e "s|\${OPENAI_API_KEY}|${OPENAI_API_KEY:-}|g" \
        -e "s|\${NOTION_TOKEN}|${NOTION_TOKEN:-}|g" \
        -e "s|\${GITHUB_TOKEN}|${GITHUB_TOKEN:-}|g" \
        -e "s|\${SLACK_BOT_TOKEN}|${SLACK_BOT_TOKEN:-}|g" \
        -e "s|\${SLACK_TEAM_ID}|${SLACK_TEAM_ID:-}|g" \
        -e "s|\${ASANA_ACCESS_TOKEN}|${ASANA_ACCESS_TOKEN:-}|g" \
        -e "s|\${ZAPIER_API_KEY}|${ZAPIER_API_KEY:-}|g" \
        -e "s|\${BRAVE_API_KEY}|${BRAVE_API_KEY:-}|g" \
        -e "s|\${GOOGLE_CLIENT_ID}|${GOOGLE_CLIENT_ID:-}|g" \
        -e "s|\${GOOGLE_CLIENT_SECRET}|${GOOGLE_CLIENT_SECRET:-}|g" \
        "$MCP_TEMPLATES_DIR/claude-desktop-mcp.json" > "$CLAUDE_DESKTOP_CONFIG"
    info "Configuración MCP de Claude Desktop instalada"
fi

# ============================================================================
# 6. Configurar Antigravity MCP
# ============================================================================
header "CONFIGURANDO MCP PARA ANTIGRAVITY"

AGY_CONFIG_DIR="$HOME/.config/Antigravity/User"
AGY_MCP_FILE="$AGY_CONFIG_DIR/mcp.json"

if [[ -f "$MCP_TEMPLATES_DIR/antigravity-mcp.json" ]]; then
    sed -e "s|\${GCP_PROJECT_ID}|${GCP_PROJECT}|g" \
        -e "s|\${HOME}|${HOME}|g" \
        -e "s|\${OPENAI_API_KEY}|${OPENAI_API_KEY:-}|g" \
        -e "s|\${NOTION_TOKEN}|${NOTION_TOKEN:-}|g" \
        -e "s|\${GITHUB_TOKEN}|${GITHUB_TOKEN:-}|g" \
        -e "s|\${VERCEL_TOKEN}|${VERCEL_TOKEN:-}|g" \
        -e "s|\${SLACK_BOT_TOKEN}|${SLACK_BOT_TOKEN:-}|g" \
        -e "s|\${SLACK_TEAM_ID}|${SLACK_TEAM_ID:-}|g" \
        -e "s|\${LINEAR_API_KEY}|${LINEAR_API_KEY:-}|g" \
        -e "s|\${ZAPIER_API_KEY}|${ZAPIER_API_KEY:-}|g" \
        -e "s|\${N8N_API_URL}|${N8N_API_URL:-}|g" \
        -e "s|\${N8N_API_KEY}|${N8N_API_KEY:-}|g" \
        -e "s|\${SUPABASE_URL}|${SUPABASE_URL:-}|g" \
        -e "s|\${SUPABASE_KEY}|${SUPABASE_KEY:-}|g" \
        -e "s|\${POSTGRES_CONNECTION_STRING}|${POSTGRES_CONNECTION_STRING:-}|g" \
        -e "s|\${BRAVE_API_KEY}|${BRAVE_API_KEY:-}|g" \
        -e "s|\${STRIPE_API_KEY}|${STRIPE_API_KEY:-}|g" \
        -e "s|\${GOOGLE_CLIENT_ID}|${GOOGLE_CLIENT_ID:-}|g" \
        -e "s|\${GOOGLE_CLIENT_SECRET}|${GOOGLE_CLIENT_SECRET:-}|g" \
        -e "s|\${JULES_API_KEY}|${JULES_API_KEY:-}|g" \
        "$MCP_TEMPLATES_DIR/antigravity-mcp.json" > "$AGY_MCP_FILE"
    info "Configuración MCP de Antigravity instalada"
fi

# ============================================================================
# 7. Configurar OpenCode MCP
# ============================================================================
header "CONFIGURANDO MCP PARA OPENCODE"

OPENCODE_CONFIG_DIR="$HOME/.opencode"
OPENCODE_MCP_FILE="$OPENCODE_CONFIG_DIR/config.json"

if [[ -f "$MCP_TEMPLATES_DIR/opencode-mcp.json" ]]; then
    sed -e "s|\${GCP_PROJECT_ID}|${GCP_PROJECT}|g" \
        -e "s|\${HOME}|${HOME}|g" \
        -e "s|\${NOTION_TOKEN}|${NOTION_TOKEN:-}|g" \
        -e "s|\${GITHUB_TOKEN}|${GITHUB_TOKEN:-}|g" \
        -e "s|\${VERCEL_TOKEN}|${VERCEL_TOKEN:-}|g" \
        -e "s|\${ZAPIER_API_KEY}|${ZAPIER_API_KEY:-}|g" \
        -e "s|\${SUPABASE_URL}|${SUPABASE_URL:-}|g" \
        -e "s|\${SUPABASE_KEY}|${SUPABASE_KEY:-}|g" \
        -e "s|\${JULES_API_KEY}|${JULES_API_KEY:-}|g" \
        "$MCP_TEMPLATES_DIR/opencode-mcp.json" > "$OPENCODE_MCP_FILE"
    info "Configuración MCP de OpenCode instalada"
fi

# ============================================================================
# 8. Actualizar .mcp.json del proyecto
# ============================================================================
header "ACTUALIZANDO MCP DEL PROYECTO"

PROJECT_MCP="${PROJECT_DIR}/.mcp.json"

cat > "$PROJECT_MCP" << PROJEOF
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": {
        "MEMORY_FILE": "${HOME}/.claude/memory/project-claudio.json"
      }
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "firebase": {
      "command": "npx",
      "args": ["-y", "firebase-tools@latest", "experimental:mcp"],
      "env": {
        "FIREBASE_PROJECT": "${GCP_PROJECT}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-filesystem", "${PROJECT_DIR}"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN:-}"
      }
    }
  }
}
PROJEOF
info "MCP del proyecto actualizado"

# ============================================================================
# 9. Pre-instalar paquetes MCP comunes (opcional pero recomendado)
# ============================================================================
header "PRE-INSTALANDO PAQUETES MCP COMUNES"

subheader "Instalando servidores MCP esenciales..."

# Lista de paquetes MCP esenciales
MCP_PACKAGES=(
    "@modelcontextprotocol/server-memory"
    "@modelcontextprotocol/server-sequential-thinking"
    "@notionhq/notion-mcp-server"
    "firebase-tools"
    "mcp-knowledge-graph"
)

for pkg in "${MCP_PACKAGES[@]}"; do
    info "Pre-cacheando: $pkg"
    npx -y "$pkg" --version 2>/dev/null || true
done

# ============================================================================
# 10. Verificar configuraciones
# ============================================================================
header "VERIFICANDO CONFIGURACIONES"

echo ""
info "Archivos MCP generados:"
echo "  Claude Code:     $CLAUDE_MCP_FILE"
echo "  Claude Desktop:  $CLAUDE_DESKTOP_CONFIG"
echo "  Antigravity:     $AGY_MCP_FILE"
echo "  OpenCode:        $OPENCODE_MCP_FILE"
echo "  Proyecto:        $PROJECT_MCP"
echo ""

# Verificar JSON válido
for file in "$CLAUDE_MCP_FILE" "$CLAUDE_DESKTOP_CONFIG" "$AGY_MCP_FILE" "$PROJECT_MCP"; do
    if [[ -f "$file" ]]; then
        if command -v jq &>/dev/null; then
            if jq empty "$file" 2>/dev/null; then
                info "JSON válido: $(basename "$file")"
            else
                warn "JSON inválido: $file"
            fi
        fi
    fi
done

# ============================================================================
# 11. Instrucciones finales
# ============================================================================
header "CONFIGURACIÓN MCP COMPLETADA"

echo ""
info "Servidores MCP configurados:"
echo ""
echo "  MEMORIA Y PERSISTENCIA:"
echo "    - memory (Knowledge Graph persistente)"
echo "    - knowledge-graph (Grafo de conocimiento)"
echo "    - sequential-thinking (Razonamiento secuencial)"
echo ""
echo "  GOOGLE CLOUD:"
echo "    - firebase, google-cloud-storage, google-drive"
echo "    - google-calendar, bigquery, vertex-ai"
echo ""
echo "  MULTI-AI:"
echo "    - openai, chatgpt, codex-cli, jules"
echo ""
echo "  PRODUCTIVIDAD:"
echo "    - notion, slack, linear, asana"
echo ""
echo "  AUTOMATIZACIÓN:"
echo "    - zapier, n8n"
echo ""
echo "  DESARROLLO:"
echo "    - github, gitlab, vercel, docker"
echo ""
echo "  BASES DE DATOS:"
echo "    - postgres, supabase, redis"
echo ""
echo "  UTILIDADES:"
echo "    - filesystem, brave-search, time, fetch, puppeteer"
echo ""
info "Para activar los cambios:"
echo "  1. Reinicia Claude Desktop/Cowork"
echo "  2. Reinicia Antigravity"
echo "  3. En Claude Code: claude mcp list"
echo ""
warn "Recuerda configurar tus API keys en config/.env"
