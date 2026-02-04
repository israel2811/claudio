#!/usr/bin/env bash
# ============================================================================
# 05-setup-mcp-integration.sh
# Configura la integración MCP entre Antigravity y Claude Code
# con servidores MCP de Google Cloud
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
PROJECT_DIR="${SCRIPT_DIR}/.."
ENV_FILE="${PROJECT_DIR}/config/.env"

if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

GCP_PROJECT="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo 'YOUR_PROJECT_ID')}"
GCP_REGION="${GCP_REGION:-us-central1}"

# ============================================================================
# 1. Instalar dependencias para MCP servers
# ============================================================================
header "INSTALANDO DEPENDENCIAS MCP"

if command -v npx &>/dev/null; then
    info "npx disponible."
else
    warn "npx no encontrado. Asegúrate de tener Node.js 18+ instalado."
fi

# ============================================================================
# 2. Configurar MCP para Claude Code (.claude/mcp.json)
# ============================================================================
header "CONFIGURANDO MCP PARA CLAUDE CODE"

CLAUDE_MCP_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_MCP_DIR"

CLAUDE_MCP_FILE="$CLAUDE_MCP_DIR/mcp.json"

cat > "$CLAUDE_MCP_FILE" << MCPEOF
{
    "mcpServers": {
        "google-cloud-storage": {
            "command": "npx",
            "args": [
                "-y",
                "@anthropic-ai/mcp-server-gcs"
            ],
            "env": {
                "GCP_PROJECT_ID": "${GCP_PROJECT}",
                "GCS_BUCKET": "${GCP_PROJECT}-claudio-storage"
            }
        },
        "firebase": {
            "command": "npx",
            "args": [
                "-y",
                "firebase-tools@latest",
                "experimental:mcp"
            ],
            "env": {
                "FIREBASE_PROJECT": "${GCP_PROJECT}"
            }
        },
        "github": {
            "command": "npx",
            "args": [
                "-y",
                "@anthropic-ai/mcp-server-github"
            ],
            "env": {
                "GITHUB_TOKEN": "\${GITHUB_TOKEN}"
            }
        },
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@anthropic-ai/mcp-server-filesystem",
                "/home/user/claudio"
            ]
        },
        "google-maps": {
            "command": "npx",
            "args": [
                "-y",
                "@anthropic-ai/mcp-server-google-maps"
            ],
            "env": {
                "GOOGLE_MAPS_API_KEY": "\${GOOGLE_MAPS_API_KEY}"
            }
        }
    }
}
MCPEOF

info "Configuración MCP de Claude Code creada en: $CLAUDE_MCP_FILE"

# ============================================================================
# 3. Configurar MCP para Claude Desktop App (Cowork)
# ============================================================================
header "CONFIGURANDO MCP PARA CLAUDE DESKTOP (COWORK)"

CLAUDE_DESKTOP_CONFIG=""
if [[ -d "$HOME/.config/Claude" ]]; then
    CLAUDE_DESKTOP_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
elif [[ -d "$HOME/Library/Application Support/Claude" ]]; then
    CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
else
    CLAUDE_DESKTOP_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
    mkdir -p "$HOME/.config/Claude"
fi

cat > "$CLAUDE_DESKTOP_CONFIG" << DESKTOPEOF
{
    "mcpServers": {
        "google-cloud-storage": {
            "command": "npx",
            "args": [
                "-y",
                "@anthropic-ai/mcp-server-gcs"
            ],
            "env": {
                "GCP_PROJECT_ID": "${GCP_PROJECT}",
                "GCS_BUCKET": "${GCP_PROJECT}-claudio-storage"
            }
        },
        "firebase": {
            "command": "npx",
            "args": [
                "-y",
                "firebase-tools@latest",
                "experimental:mcp"
            ],
            "env": {
                "FIREBASE_PROJECT": "${GCP_PROJECT}"
            }
        },
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@anthropic-ai/mcp-server-filesystem",
                "/home/user/claudio"
            ]
        }
    },
    "globalShortcut": "Ctrl+Shift+Space"
}
DESKTOPEOF

info "Configuración MCP de Claude Desktop creada en: $CLAUDE_DESKTOP_CONFIG"

# ============================================================================
# 4. Configurar MCP para Antigravity
# ============================================================================
header "CONFIGURANDO MCP PARA ANTIGRAVITY"

AGY_CONFIG_DIR="$HOME/.config/Antigravity/User"
mkdir -p "$AGY_CONFIG_DIR"

# Antigravity usa un formato similar a VS Code para MCP
AGY_MCP_FILE="$AGY_CONFIG_DIR/mcp.json"

cat > "$AGY_MCP_FILE" << AGYEOF
{
    "servers": {
        "firebase": {
            "command": "npx",
            "args": [
                "-y",
                "firebase-tools@latest",
                "experimental:mcp"
            ],
            "env": {
                "FIREBASE_PROJECT": "${GCP_PROJECT}"
            }
        },
        "google-cloud-storage": {
            "command": "npx",
            "args": [
                "-y",
                "@anthropic-ai/mcp-server-gcs"
            ],
            "env": {
                "GCP_PROJECT_ID": "${GCP_PROJECT}",
                "GCS_BUCKET": "${GCP_PROJECT}-claudio-storage"
            }
        },
        "github": {
            "command": "npx",
            "args": [
                "-y",
                "@anthropic-ai/mcp-server-github"
            ],
            "env": {
                "GITHUB_TOKEN": "\${GITHUB_TOKEN}"
            }
        },
        "claude-code-bridge": {
            "command": "claude",
            "args": [
                "mcp",
                "serve"
            ],
            "env": {
                "CLAUDE_CODE_USE_VERTEX": "1",
                "ANTHROPIC_VERTEX_PROJECT_ID": "${GCP_PROJECT}"
            }
        }
    }
}
AGYEOF

info "Configuración MCP de Antigravity creada en: $AGY_MCP_FILE"

# ============================================================================
# 5. Configurar MCP a nivel de proyecto (.mcp.json)
# ============================================================================
header "CONFIGURANDO MCP A NIVEL DE PROYECTO"

PROJECT_MCP_FILE="${PROJECT_DIR}/.mcp.json"

cat > "$PROJECT_MCP_FILE" << PROJEOF
{
    "mcpServers": {
        "firebase": {
            "command": "npx",
            "args": [
                "-y",
                "firebase-tools@latest",
                "experimental:mcp"
            ],
            "env": {
                "FIREBASE_PROJECT": "${GCP_PROJECT}"
            }
        },
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@anthropic-ai/mcp-server-filesystem",
                "/home/user/claudio"
            ]
        }
    }
}
PROJEOF

info "Configuración MCP de proyecto creada en: $PROJECT_MCP_FILE"

# ============================================================================
# 6. Configurar Claude Code como servidor MCP dentro de Antigravity
# ============================================================================
header "CONFIGURANDO CLAUDE CODE COMO MCP SERVER EN ANTIGRAVITY"

info ""
info "Claude Code puede actuar como servidor MCP dentro de Antigravity."
info "Esto permite que los agentes de Antigravity usen Claude Code directamente."
info ""
info "Para configurarlo manualmente en Antigravity:"
info "  1. Abre Antigravity: agy /home/user/claudio"
info "  2. Ctrl+Shift+P > 'MCP: Add Server'"
info "  3. Selecciona 'Command (stdio)'"
info "  4. Comando: claude"
info "  5. Args: mcp serve"
info ""
info "O desde la terminal de Claude Code:"
info "  claude mcp add antigravity-bridge -- claude mcp serve"
info ""

# ============================================================================
# 7. Verificar servidores MCP
# ============================================================================
header "VERIFICANDO SERVIDORES MCP"

if command -v claude &>/dev/null; then
    info "Verificando servidores MCP registrados en Claude Code..."
    claude mcp list 2>/dev/null || warn "No se pudieron listar los servidores MCP."
fi

echo ""
info "Archivos MCP generados:"
info "  Claude Code:     $CLAUDE_MCP_FILE"
info "  Claude Desktop:  $CLAUDE_DESKTOP_CONFIG"
info "  Antigravity:     $AGY_MCP_FILE"
info "  Proyecto:        $PROJECT_MCP_FILE"
echo ""
info "Integración MCP configurada exitosamente."
