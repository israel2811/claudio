#!/usr/bin/env bash
# ============================================================================
# 08-setup-connectors.sh
# Los "conectores" (Google Drive, GitHub, Notion, Linear, Replit, Slack...)
# son integraciones a NIVEL DE CUENTA de Claude (claude.ai), no paquetes que
# se instalen por máquina. Este script no puede activarlos por ti (requieren
# tu login OAuth), pero deja documentado el estado y el paso manual exacto.
# ============================================================================
set -euo pipefail

YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
CYAN='\033[1;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
header(){ echo -e "${CYAN}=== $* ===${NC}"; }

header "CONECTORES DE CUENTA (CLAUDE.AI)"

cat << 'EOF'

Estos conectores viven en tu cuenta de Claude (israel.realivazquez2811@gmail.com),
no en esta laptop ni en este repositorio. Una vez conectados en
claude.ai -> Settings -> Connectors, están disponibles en TODOS tus entornos
de Claude Code (Local, Cloud, SSH, WSL) sin reinstalar nada.

Estado típico de conectores relevantes para este proyecto:
  - Google Drive   -> conectar en claude.ai/settings/connectors
  - GitHub         -> se gestiona además por repo en claude.ai/code (Sources)
  - Notion         -> conectar en claude.ai/settings/connectors
  - Linear         -> conectar en claude.ai/settings/connectors
  - Slack          -> conectar en claude.ai/settings/connectors
  - Replit         -> no es un conector MCP nativo hoy; usa su integración de
                       GitHub (push/pull) o su propio Agent, no vía Claude.

Paso manual único (no automatizable desde un script, requiere tu login):
  1. Ve a https://claude.ai/settings/connectors
  2. Activa/il conecta el servicio que necesites
  3. En "Repository access" (claude.ai/code) añade este repo si aún no está

EOF

header "VERIFICACIÓN LOCAL DE MCP EN CLAUDE CODE"
if command -v claude &>/dev/null; then
    claude mcp list 2>/dev/null || warn "No se pudieron listar servidores MCP locales."
else
    warn "Claude Code CLI no está instalado en esta máquina (scripts/02)."
fi

info "Revisión de conectores completada."
