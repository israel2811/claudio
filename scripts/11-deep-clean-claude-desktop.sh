#!/usr/bin/env bash
# ============================================================================
# 11-deep-clean-claude-desktop.sh
# Limpieza PROFUNDA de Claude Desktop
# BORRA: Chats, cache, locks, DBs corruptas
# PRESERVA: MCP configs, extensiones, conexiones
# ============================================================================
set -euo pipefail

YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
CYAN='\033[1;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
header(){ echo -e "\n${CYAN}=== $* ===${NC}"; }

# ============================================================================
# 0. Detectar OS y cerrar Claude
# ============================================================================
header "PREPARANDO LIMPIEZA PROFUNDA"

OS_TYPE=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    CLAUDE_CONFIG="$HOME/Library/Application Support/Claude"
    CLAUDE_CACHE="$HOME/Library/Caches/Claude"
    CLAUDE_LOGS="$HOME/Library/Logs/Claude"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
    CLAUDE_CONFIG="$HOME/.config/Claude"
    CLAUDE_CACHE="$HOME/.cache/Claude"
    CLAUDE_LOGS="$HOME/.local/share/Claude/logs"
else
    OS_TYPE="windows"
    CLAUDE_CONFIG="$APPDATA/Claude"
    CLAUDE_CACHE="$LOCALAPPDATA/Claude/Cache"
fi

info "Sistema: $OS_TYPE"
info "Config: $CLAUDE_CONFIG"

# Cerrar Claude si está corriendo
if pgrep -x "Claude" &>/dev/null || pgrep -f "claude-desktop" &>/dev/null; then
    warn "Cerrando Claude Desktop..."
    pkill -x "Claude" 2>/dev/null || pkill -f "claude-desktop" 2>/dev/null || true
    sleep 3
fi

# ============================================================================
# 1. BACKUP de configuraciones importantes
# ============================================================================
header "HACIENDO BACKUP DE CONFIGURACIONES"

BACKUP_DIR="$HOME/.claude-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup MCP config
if [[ -f "$CLAUDE_CONFIG/claude_desktop_config.json" ]]; then
    cp "$CLAUDE_CONFIG/claude_desktop_config.json" "$BACKUP_DIR/"
    info "Backup: claude_desktop_config.json"
fi

# Backup settings
if [[ -f "$CLAUDE_CONFIG/settings.json" ]]; then
    cp "$CLAUDE_CONFIG/settings.json" "$BACKUP_DIR/"
    info "Backup: settings.json"
fi

# Backup cowork config
if [[ -f "$CLAUDE_CONFIG/cowork_config.json" ]]; then
    cp "$CLAUDE_CONFIG/cowork_config.json" "$BACKUP_DIR/"
    info "Backup: cowork_config.json"
fi

info "Backups guardados en: $BACKUP_DIR"

# ============================================================================
# 2. ELIMINAR todos los chats/conversaciones
# ============================================================================
header "ELIMINANDO CONVERSACIONES Y CHATS"

# Conversaciones
CONV_DIRS=(
    "$CLAUDE_CONFIG/conversations"
    "$CLAUDE_CONFIG/chats"
    "$CLAUDE_CONFIG/chat-history"
    "$CLAUDE_CONFIG/Local Storage"
    "$CLAUDE_CONFIG/Session Storage"
    "$CLAUDE_CONFIG/IndexedDB"
)

for dir in "${CONV_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        rm -rf "$dir"
        info "Eliminado: $dir"
    fi
done

# Archivos de conversación individuales
find "$CLAUDE_CONFIG" -name "*.chat" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "*.conversation" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "*history*" -type f -delete 2>/dev/null || true

info "Conversaciones eliminadas"

# ============================================================================
# 3. ELIMINAR cache completamente
# ============================================================================
header "ELIMINANDO CACHE"

CACHE_DIRS=(
    "$CLAUDE_CACHE"
    "$CLAUDE_CONFIG/Cache"
    "$CLAUDE_CONFIG/CachedData"
    "$CLAUDE_CONFIG/Code Cache"
    "$CLAUDE_CONFIG/GPUCache"
    "$CLAUDE_CONFIG/ShaderCache"
    "$CLAUDE_CONFIG/DawnCache"
    "$CLAUDE_CONFIG/blob_storage"
    "$CLAUDE_CONFIG/Service Worker"
)

for dir in "${CACHE_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        rm -rf "$dir"
        info "Eliminado: $dir"
    fi
done

info "Cache eliminada"

# ============================================================================
# 4. ELIMINAR locks y archivos temporales
# ============================================================================
header "ELIMINANDO LOCKS Y TEMPORALES"

# Locks en XDG
rm -rf "$HOME/.local/state/claude" 2>/dev/null || true
rm -rf "$HOME/.local/state/Claude" 2>/dev/null || true

# Locks en config
find "$CLAUDE_CONFIG" -name "*.lock" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "lockfile" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "SingletonLock" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "SingletonCookie" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "SingletonSocket" -delete 2>/dev/null || true

# Temporales
find "$CLAUDE_CONFIG" -name "*.tmp" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "*.temp" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name ".org.chromium*" -delete 2>/dev/null || true

info "Locks y temporales eliminados"

# ============================================================================
# 5. ELIMINAR bases de datos corruptas
# ============================================================================
header "ELIMINANDO BASES DE DATOS"

# SQLite y LevelDB
DB_DIRS=(
    "$CLAUDE_CONFIG/databases"
    "$CLAUDE_CONFIG/leveldb"
    "$CLAUDE_CONFIG/Local Storage/leveldb"
)

for dir in "${DB_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        rm -rf "$dir"
        info "Eliminado: $dir"
    fi
done

# Archivos de DB sueltos
find "$CLAUDE_CONFIG" -name "*.sqlite" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "*.sqlite-journal" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "*.db" ! -name "claude_desktop_config.json" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "*.ldb" -delete 2>/dev/null || true

info "Bases de datos eliminadas"

# ============================================================================
# 6. ELIMINAR logs
# ============================================================================
header "ELIMINANDO LOGS"

if [[ -d "$CLAUDE_LOGS" ]]; then
    rm -rf "$CLAUDE_LOGS"
    info "Eliminado: $CLAUDE_LOGS"
fi

find "$CLAUDE_CONFIG" -name "*.log" -delete 2>/dev/null || true
find "$CLAUDE_CONFIG" -name "*.log.*" -delete 2>/dev/null || true

info "Logs eliminados"

# ============================================================================
# 7. ELIMINAR uploads/attachments
# ============================================================================
header "ELIMINANDO UPLOADS Y ATTACHMENTS"

UPLOAD_DIRS=(
    "$CLAUDE_CONFIG/uploads"
    "$CLAUDE_CONFIG/attachments"
    "$CLAUDE_CONFIG/files"
    "$CLAUDE_CONFIG/temp-files"
)

for dir in "${UPLOAD_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        rm -rf "$dir"
        info "Eliminado: $dir"
    fi
done

info "Uploads eliminados"

# ============================================================================
# 8. RESTAURAR configuraciones desde backup
# ============================================================================
header "RESTAURANDO CONFIGURACIONES"

# Restaurar MCP config
if [[ -f "$BACKUP_DIR/claude_desktop_config.json" ]]; then
    mkdir -p "$CLAUDE_CONFIG"
    cp "$BACKUP_DIR/claude_desktop_config.json" "$CLAUDE_CONFIG/"
    info "Restaurado: claude_desktop_config.json (MCP intacto)"
fi

# Restaurar settings
if [[ -f "$BACKUP_DIR/settings.json" ]]; then
    cp "$BACKUP_DIR/settings.json" "$CLAUDE_CONFIG/"
    info "Restaurado: settings.json"
fi

# Restaurar cowork
if [[ -f "$BACKUP_DIR/cowork_config.json" ]]; then
    cp "$BACKUP_DIR/cowork_config.json" "$CLAUDE_CONFIG/"
    info "Restaurado: cowork_config.json"
fi

# ============================================================================
# 9. VERIFICAR espacio liberado
# ============================================================================
header "RESUMEN"

echo ""
info "LIMPIEZA COMPLETADA"
echo ""
info "Lo que se ELIMINÓ:"
echo "  - Todas las conversaciones y chats"
echo "  - Todo el cache"
echo "  - Todos los locks"
echo "  - Todas las bases de datos"
echo "  - Todos los logs"
echo "  - Todos los uploads/attachments"
echo ""
info "Lo que se PRESERVÓ:"
echo "  - claude_desktop_config.json (MCP servers)"
echo "  - settings.json (preferencias)"
echo "  - cowork_config.json (config de Cowork)"
echo ""
info "Backup guardado en: $BACKUP_DIR"
echo ""
warn "IMPORTANTE: Ahora abre Claude Desktop."
warn "Debería funcionar como nuevo, con todos los MCP intactos."
echo ""
