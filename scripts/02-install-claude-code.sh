#!/usr/bin/env bash
# ============================================================================
# 02-install-claude-code.sh
# Instala Claude Code CLI y lo configura para usar Google Cloud Vertex AI
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

# --- Cargar variables de entorno ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../config/.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

# ============================================================================
# 1. Instalar Node.js si no está disponible
# ============================================================================
header "VERIFICANDO NODE.JS"
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    info "Node.js ya instalado: $NODE_VER"
    # Verificar versión mínima (18+)
    NODE_MAJOR=$(echo "$NODE_VER" | sed 's/v//' | cut -d. -f1)
    if [[ "$NODE_MAJOR" -lt 18 ]]; then
        warn "Claude Code requiere Node.js 18+. Versión actual: $NODE_VER"
        warn "Actualizando Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null || true
        sudo apt-get install -y nodejs 2>/dev/null || true
    fi
else
    info "Instalando Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null || {
        warn "No se pudo instalar via apt. Intentando con nvm..."
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        # shellcheck disable=SC1091
        [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
        nvm install 20
        nvm use 20
    }
    sudo apt-get install -y nodejs 2>/dev/null || true
fi

# ============================================================================
# 2. Instalar Claude Code CLI
# ============================================================================
header "INSTALANDO CLAUDE CODE CLI"
if command -v claude &>/dev/null; then
    info "Claude Code ya está instalado: $(claude --version 2>/dev/null || echo 'versión desconocida')"
    read -rp "¿Deseas reinstalar/actualizar? (s/n): " REINSTALL
    if [[ ! "$REINSTALL" =~ ^[sS]$ ]]; then
        info "Omitiendo reinstalación."
    else
        info "Actualizando Claude Code..."
        npm install -g @anthropic-ai/claude-code@latest 2>/dev/null || {
            warn "npm falló, intentando con instalador nativo..."
            curl -fsSL https://claude.ai/install.sh | bash
        }
    fi
else
    info "Instalando Claude Code CLI..."

    # Método 1: Instalador nativo (recomendado)
    curl -fsSL https://claude.ai/install.sh | bash 2>/dev/null || {
        warn "Instalador nativo falló. Intentando con npm..."

        # Método 2: npm global (sin sudo)
        mkdir -p "$HOME/.npm-global"
        npm config set prefix "$HOME/.npm-global"
        if ! grep -q ".npm-global/bin" "$HOME/.bashrc" 2>/dev/null; then
            echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> "$HOME/.bashrc"
        fi
        export PATH="$HOME/.npm-global/bin:$PATH"

        npm install -g @anthropic-ai/claude-code@latest
    }

    info "Claude Code CLI instalado."
fi

# ============================================================================
# 3. Configurar Claude Code para usar Google Cloud Vertex AI
# ============================================================================
header "CONFIGURANDO VERTEX AI PARA CLAUDE CODE"

GCP_PROJECT="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo '')}"

if [[ -z "$GCP_PROJECT" ]]; then
    read -rp "Ingresa tu Google Cloud Project ID: " GCP_PROJECT
fi

VERTEX_REGION="${GCP_VERTEX_REGION:-global}"

# Crear/actualizar archivo de configuración de entorno para Claude Code
CLAUDE_ENV_FILE="$HOME/.claude/.env"
mkdir -p "$HOME/.claude"

cat > "$CLAUDE_ENV_FILE" << EOF
# ============================================================================
# Claude Code - Configuración Vertex AI
# Generado por claudio setup script
# ============================================================================

# Usar Vertex AI como backend
CLAUDE_CODE_USE_VERTEX=1

# Región de Vertex AI (global o us-east5, europe-west1, etc.)
CLOUD_ML_REGION=${VERTEX_REGION}

# ID del proyecto de Google Cloud
ANTHROPIC_VERTEX_PROJECT_ID=${GCP_PROJECT}

# Modelos (ajustar según disponibilidad en tu región)
# ANTHROPIC_MODEL=claude-opus-4-5@20251101
# ANTHROPIC_SMALL_FAST_MODEL=claude-haiku-4-5@20251001

# Descomenta si necesitas desactivar prompt caching
# DISABLE_PROMPT_CACHING=1
EOF

info "Archivo de configuración creado en: $CLAUDE_ENV_FILE"

# También exportar las variables para la sesión actual
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION="$VERTEX_REGION"
export ANTHROPIC_VERTEX_PROJECT_ID="$GCP_PROJECT"

# ============================================================================
# 4. Agregar variables al perfil del shell
# ============================================================================
SHELL_RC="$HOME/.bashrc"
if ! grep -q "CLAUDE_CODE_USE_VERTEX" "$SHELL_RC" 2>/dev/null; then
    cat >> "$SHELL_RC" << 'ENVBLOCK'

# === Claude Code + Vertex AI ===
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION="${CLOUD_ML_REGION:-global}"
if command -v gcloud &>/dev/null; then
    export ANTHROPIC_VERTEX_PROJECT_ID="${ANTHROPIC_VERTEX_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
fi
ENVBLOCK
    info "Variables de entorno agregadas a $SHELL_RC"
fi

# ============================================================================
# 5. Verificar autenticación de Google Cloud
# ============================================================================
header "VERIFICANDO AUTENTICACIÓN"
if gcloud auth application-default print-access-token &>/dev/null 2>&1; then
    info "Autenticación de Application Default Credentials: OK"
else
    warn "No hay Application Default Credentials."
    warn "Ejecuta: gcloud auth application-default login"
fi

# Verificar permisos de Vertex AI
if [[ -n "$GCP_PROJECT" ]]; then
    info "Verificando API de Vertex AI en proyecto $GCP_PROJECT..."
    if gcloud services list --project="$GCP_PROJECT" --filter="name:aiplatform.googleapis.com" --format="value(name)" 2>/dev/null | grep -q "aiplatform"; then
        info "API de Vertex AI: HABILITADA"
    else
        warn "API de Vertex AI no habilitada. Habilitando..."
        gcloud services enable aiplatform.googleapis.com --project="$GCP_PROJECT" --quiet 2>/dev/null || \
            warn "No se pudo habilitar. Habilítala manualmente en la consola de GCP."
    fi
fi

# ============================================================================
# 6. Verificación final
# ============================================================================
header "VERIFICACIÓN FINAL"
echo ""
info "Claude Code CLI:    $(command -v claude 2>/dev/null || echo 'No encontrado')"
info "Vertex AI Backend:  CLAUDE_CODE_USE_VERTEX=$CLAUDE_CODE_USE_VERTEX"
info "Región:             CLOUD_ML_REGION=$CLOUD_ML_REGION"
info "Proyecto GCP:       ANTHROPIC_VERTEX_PROJECT_ID=$GCP_PROJECT"
echo ""
info "Para verificar la configuración completa, ejecuta:"
info "  claude /status"
echo ""
info "Para iniciar sesión en Claude Code (si usas API key directo):"
info "  claude /login"
echo ""
info "Claude Code instalado y configurado con Vertex AI."
