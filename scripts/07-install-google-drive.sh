#!/usr/bin/env bash
# ============================================================================
# 07-install-google-drive.sh
# Configura acceso a Google Drive vía rclone (no existe cliente de
# escritorio oficial de Google Drive para Linux). rclone permite montar
# Drive como carpeta local y sincronizar archivos por CLI.
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
# 1. Instalar rclone
# ============================================================================
header "INSTALANDO RCLONE"

if command -v rclone &>/dev/null; then
    info "rclone ya está instalado: $(rclone version | head -1)"
else
    info "Instalando rclone..."
    curl -fsSL https://rclone.org/install.sh 2>/dev/null | sudo bash && \
        info "rclone instalado." || \
        warn "No se pudo instalar rclone automáticamente. Ver: https://rclone.org/downloads/"
fi

# ============================================================================
# 2. Configurar remoto de Google Drive (requiere OAuth interactivo)
# ============================================================================
header "CONFIGURANDO REMOTO 'gdrive'"

if command -v rclone &>/dev/null; then
    if rclone listremotes 2>/dev/null | grep -q "^gdrive:"; then
        info "El remoto 'gdrive' ya existe."
    else
        info "Este paso es interactivo: abrirá tu navegador para autenticar con tu cuenta de Google."
        info "Ejecuta cuando quieras autenticar (requiere tu confirmación manual):"
        info "  rclone config create gdrive drive"
        warn "No se ejecuta automáticamente porque requiere iniciar sesión con TU cuenta de Google."
    fi

    MOUNT_POINT="$HOME/GoogleDrive"
    mkdir -p "$MOUNT_POINT"
    info "Punto de montaje preparado en: $MOUNT_POINT"
    info "Para montar una vez configurado el remoto:"
    info "  rclone mount gdrive: $MOUNT_POINT --daemon"
    info "Para sincronizar sin montar:"
    info "  rclone sync gdrive:/ruta ./destino-local"
fi

# ============================================================================
# 3. Alternativa: MCP de Google Drive (recomendado para Claude Code/Cowork)
# ============================================================================
header "ALTERNATIVA RECOMENDADA: CONECTOR DE GOOGLE DRIVE EN CLAUDE"

info ""
info "Si lo que necesitas es que Claude lea/escriba en Drive (no montarlo como"
info "disco), usa el conector nativo de Google Drive en tu cuenta de Claude:"
info "  claude.ai -> Settings -> Connectors -> Google Drive -> Connect"
info "Este conector queda disponible automáticamente en CUALQUIER entorno"
info "(local, cloud, SSH, WSL) donde inicies sesión con tu cuenta, sin volver"
info "a instalar nada por máquina."
info ""

header "VERIFICACIÓN"
info "rclone: $(command -v rclone 2>/dev/null || echo 'No instalado')"
info "Montaje: $MOUNT_POINT"
echo ""
info "Configuración de Google Drive completada."
