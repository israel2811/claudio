#!/usr/bin/env bash
# ============================================================================
# 01-install-gcloud.sh
# Instala Google Cloud SDK, autentica y configura el proyecto
# ============================================================================
set -euo pipefail

YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# --- Cargar variables de entorno si existen ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../config/.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

# --- Verificar dependencias base ---
for cmd in curl python3; do
    command -v "$cmd" &>/dev/null || error "Se requiere '$cmd'. Instálalo primero."
done

# ============================================================================
# 1. Instalar Google Cloud SDK
# ============================================================================
if command -v gcloud &>/dev/null; then
    info "Google Cloud SDK ya está instalado: $(gcloud version 2>/dev/null | head -1)"
else
    info "Instalando Google Cloud SDK..."
    curl -fsSL https://sdk.cloud.google.com | bash -s -- --disable-prompts --install-dir="$HOME"

    # Agregar al PATH
    GCLOUD_PATH="$HOME/google-cloud-sdk/bin"
    if ! grep -q "google-cloud-sdk" "$HOME/.bashrc" 2>/dev/null; then
        echo "" >> "$HOME/.bashrc"
        echo "# Google Cloud SDK" >> "$HOME/.bashrc"
        echo "source $HOME/google-cloud-sdk/path.bash.inc" >> "$HOME/.bashrc"
        echo "source $HOME/google-cloud-sdk/completion.bash.inc" >> "$HOME/.bashrc"
    fi
    export PATH="$GCLOUD_PATH:$PATH"
    info "Google Cloud SDK instalado correctamente."
fi

# ============================================================================
# 2. Instalar componentes adicionales
# ============================================================================
info "Instalando componentes adicionales de gcloud..."
gcloud components install beta --quiet 2>/dev/null || true
gcloud components install alpha --quiet 2>/dev/null || true
gcloud components update --quiet 2>/dev/null || true

# ============================================================================
# 3. Autenticación
# ============================================================================
info "=== AUTENTICACIÓN CON GOOGLE CLOUD ==="
info "Se abrirá un navegador para autenticarte con tu cuenta de Google."
info "Si estás en un entorno sin navegador, usa: gcloud auth login --no-launch-browser"
echo ""

read -rp "¿Deseas autenticarte ahora? (s/n): " AUTH_NOW
if [[ "$AUTH_NOW" =~ ^[sS]$ ]]; then
    gcloud auth login
    gcloud auth application-default login
    info "Autenticación completada."
else
    warn "Omitiendo autenticación. Ejecuta manualmente:"
    warn "  gcloud auth login"
    warn "  gcloud auth application-default login"
fi

# ============================================================================
# 4. Configurar proyecto
# ============================================================================
if [[ -n "${GCP_PROJECT_ID:-}" ]]; then
    info "Configurando proyecto: $GCP_PROJECT_ID"
    gcloud config set project "$GCP_PROJECT_ID"
else
    echo ""
    read -rp "Ingresa tu Google Cloud Project ID (o Enter para omitir): " PROJECT_ID
    if [[ -n "$PROJECT_ID" ]]; then
        gcloud config set project "$PROJECT_ID"
        # Guardar en .env
        if [[ -f "$ENV_FILE" ]]; then
            if grep -q "GCP_PROJECT_ID" "$ENV_FILE"; then
                sed -i "s/^GCP_PROJECT_ID=.*/GCP_PROJECT_ID=$PROJECT_ID/" "$ENV_FILE"
            else
                echo "GCP_PROJECT_ID=$PROJECT_ID" >> "$ENV_FILE"
            fi
        fi
        info "Proyecto configurado: $PROJECT_ID"
    else
        warn "No se configuró proyecto. Hazlo manualmente con: gcloud config set project TU_PROJECT_ID"
    fi
fi

# ============================================================================
# 5. Configurar región por defecto
# ============================================================================
REGION="${GCP_REGION:-us-central1}"
gcloud config set compute/region "$REGION"
info "Región configurada: $REGION"

# ============================================================================
# 6. Habilitar APIs necesarias
# ============================================================================
info "Habilitando APIs necesarias en Google Cloud..."
APIS=(
    "aiplatform.googleapis.com"          # Vertex AI (para Claude Code)
    "storage.googleapis.com"             # Cloud Storage
    "cloudbuild.googleapis.com"          # Cloud Build
    "run.googleapis.com"                 # Cloud Run
    "firestore.googleapis.com"           # Firestore
    "secretmanager.googleapis.com"       # Secret Manager
    "cloudresourcemanager.googleapis.com" # Resource Manager
    "iam.googleapis.com"                 # IAM
    "compute.googleapis.com"             # Compute Engine
)

for api in "${APIS[@]}"; do
    info "  Habilitando $api ..."
    gcloud services enable "$api" --quiet 2>/dev/null || warn "  No se pudo habilitar $api (puede requerir billing)"
done

# ============================================================================
# 7. Crear bucket de almacenamiento (opcional)
# ============================================================================
BUCKET_NAME="${GCP_STORAGE_BUCKET:-}"
if [[ -z "$BUCKET_NAME" ]]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
    if [[ -n "$PROJECT_ID" ]]; then
        BUCKET_NAME="${PROJECT_ID}-claudio-storage"
    fi
fi

if [[ -n "$BUCKET_NAME" ]]; then
    read -rp "¿Crear bucket de Cloud Storage '$BUCKET_NAME'? (s/n): " CREATE_BUCKET
    if [[ "$CREATE_BUCKET" =~ ^[sS]$ ]]; then
        if gsutil ls "gs://$BUCKET_NAME" &>/dev/null; then
            info "Bucket '$BUCKET_NAME' ya existe."
        else
            gsutil mb -l "$REGION" "gs://$BUCKET_NAME" && \
                info "Bucket '$BUCKET_NAME' creado." || \
                warn "No se pudo crear el bucket."
        fi
    fi
fi

# ============================================================================
# 8. Verificación final
# ============================================================================
info ""
info "=== RESUMEN DE CONFIGURACIÓN GOOGLE CLOUD ==="
info "Cuenta:   $(gcloud config get-value account 2>/dev/null || echo 'No configurada')"
info "Proyecto: $(gcloud config get-value project 2>/dev/null || echo 'No configurado')"
info "Región:   $(gcloud config get-value compute/region 2>/dev/null || echo 'No configurada')"
info ""
info "Google Cloud SDK configurado exitosamente."
