#!/usr/bin/env bash
# ============================================================================
# 06-fix-claude-desktop.sh
# Limpia cache, locks y arregla errores de Claude Desktop/Cowork
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
header(){ echo -e "${CYAN}=== $* ===${NC}"; }

# ============================================================================
# 1. Detectar sistema operativo
# ============================================================================
header "DETECTANDO SISTEMA OPERATIVO"

OS_TYPE=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    info "Sistema: macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
    info "Sistema: Linux"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS_TYPE="windows"
    info "Sistema: Windows (WSL/Git Bash)"
else
    warn "Sistema no reconocido: $OSTYPE"
    OS_TYPE="linux"
fi

# ============================================================================
# 2. Limpiar archivos de lock (causa principal del error)
# ============================================================================
header "LIMPIANDO ARCHIVOS DE LOCK"

# XDG directories
if [[ -d "$HOME/.local/state/claude" ]]; then
    info "Encontrado: ~/.local/state/claude"
    rm -rf "$HOME/.local/state/claude/locks/" 2>/dev/null && info "Locks eliminados" || warn "No había locks"
fi

if [[ -d "$HOME/.local/state/Claude" ]]; then
    info "Encontrado: ~/.local/state/Claude"
    rm -rf "$HOME/.local/state/Claude/locks/" 2>/dev/null && info "Locks eliminados" || warn "No había locks"
fi

# Buscar cualquier archivo de lock residual
info "Buscando locks residuales..."
find "$HOME/.local" -iname "*claude*lock*" -type f 2>/dev/null | while read -r lockfile; do
    info "Eliminando: $lockfile"
    rm -f "$lockfile"
done

# ============================================================================
# 3. Limpiar cache según sistema operativo
# ============================================================================
header "LIMPIANDO CACHE DE CLAUDE"

case "$OS_TYPE" in
    macos)
        # Claude Desktop
        [[ -d "$HOME/Library/Application Support/Claude" ]] && {
            info "Limpiando cache de Claude Desktop..."
            rm -rf "$HOME/Library/Caches/Claude" 2>/dev/null || true
            rm -rf "$HOME/Library/Logs/Claude" 2>/dev/null || true
            # NO eliminar config, solo cache
        }
        # Claude Code
        [[ -d "$HOME/Library/Application Support/claude-code" ]] && {
            info "Limpiando cache de Claude Code..."
            rm -rf "$HOME/Library/Caches/claude-code" 2>/dev/null || true
            rm -rf "$HOME/Library/Logs/claude-code" 2>/dev/null || true
        }
        ;;
    linux)
        # Claude Desktop
        [[ -d "$HOME/.config/Claude" ]] && {
            info "Limpiando cache de Claude Desktop..."
            rm -rf "$HOME/.cache/Claude" 2>/dev/null || true
        }
        # Claude Code
        [[ -d "$HOME/.config/claude-code" ]] && {
            info "Limpiando cache de Claude Code..."
            rm -rf "$HOME/.cache/claude-code" 2>/dev/null || true
            rm -rf "$HOME/.local/share/claude-code/logs" 2>/dev/null || true
        }
        # Electron cache (usado por Claude Desktop)
        rm -rf "$HOME/.config/Claude/Cache" 2>/dev/null || true
        rm -rf "$HOME/.config/Claude/Code Cache" 2>/dev/null || true
        rm -rf "$HOME/.config/Claude/GPUCache" 2>/dev/null || true
        ;;
    windows)
        info "En Windows, ejecuta estos comandos en PowerShell como administrador:"
        echo ""
        echo "Remove-Item -Path \"\$env:APPDATA\\Claude\\Cache\" -Recurse -Force -ErrorAction SilentlyContinue"
        echo "Remove-Item -Path \"\$env:APPDATA\\Claude\\Code Cache\" -Recurse -Force -ErrorAction SilentlyContinue"
        echo "Remove-Item -Path \"\$env:APPDATA\\Claude\\GPUCache\" -Recurse -Force -ErrorAction SilentlyContinue"
        echo "Remove-Item -Path \"\$env:LOCALAPPDATA\\claude-code-cache\" -Recurse -Force -ErrorAction SilentlyContinue"
        echo ""
        ;;
esac

# ============================================================================
# 4. Limpiar archivos temporales de conversaciones
# ============================================================================
header "LIMPIANDO ARCHIVOS TEMPORALES DE CONVERSACIONES"

# Claude Desktop guarda conversaciones con archivos adjuntos
CLAUDE_CONV_DIRS=(
    "$HOME/.config/Claude/conversations"
    "$HOME/.config/Claude/uploads"
    "$HOME/.config/Claude/attachments"
    "$HOME/Library/Application Support/Claude/conversations"
    "$HOME/Library/Application Support/Claude/uploads"
)

for dir in "${CLAUDE_CONV_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        # Contar archivos
        file_count=$(find "$dir" -type f 2>/dev/null | wc -l)
        if [[ $file_count -gt 100 ]]; then
            warn "Encontrados $file_count archivos en $dir"
            info "Limpiando archivos antiguos (>7 días)..."
            find "$dir" -type f -mtime +7 -delete 2>/dev/null || true
        fi
    fi
done

# ============================================================================
# 5. Verificar y reparar permisos
# ============================================================================
header "VERIFICANDO PERMISOS"

CLAUDE_DIRS=(
    "$HOME/.claude"
    "$HOME/.config/Claude"
    "$HOME/.config/claude-code"
    "$HOME/.local/share/claude-code"
)

for dir in "${CLAUDE_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        current_owner=$(stat -c '%U' "$dir" 2>/dev/null || stat -f '%Su' "$dir" 2>/dev/null)
        if [[ "$current_owner" != "$USER" ]]; then
            warn "Permisos incorrectos en $dir (owner: $current_owner)"
            info "Corrigiendo permisos..."
            sudo chown -R "$USER" "$dir" 2>/dev/null || warn "No se pudo cambiar owner"
        else
            info "Permisos OK en $dir"
        fi
    fi
done

# ============================================================================
# 6. Limpiar base de datos SQLite corrupta (si existe)
# ============================================================================
header "VERIFICANDO BASE DE DATOS"

SQLITE_DBS=(
    "$HOME/.config/Claude/databases"
    "$HOME/.config/Claude/IndexedDB"
    "$HOME/Library/Application Support/Claude/databases"
)

for db_dir in "${SQLITE_DBS[@]}"; do
    if [[ -d "$db_dir" ]]; then
        info "Verificando integridad de DBs en $db_dir..."
        find "$db_dir" -name "*.sqlite" -o -name "*.db" 2>/dev/null | while read -r db; do
            if command -v sqlite3 &>/dev/null; then
                if ! sqlite3 "$db" "PRAGMA integrity_check;" &>/dev/null; then
                    warn "DB corrupta: $db"
                    info "Haciendo backup y eliminando..."
                    mv "$db" "${db}.corrupted.bak"
                fi
            fi
        done
    fi
done

# ============================================================================
# 7. Resetear configuración de Cowork (si está problemática)
# ============================================================================
header "VERIFICANDO CONFIGURACIÓN DE COWORK"

COWORK_CONFIG=""
if [[ "$OS_TYPE" == "macos" ]]; then
    COWORK_CONFIG="$HOME/Library/Application Support/Claude/cowork_config.json"
elif [[ "$OS_TYPE" == "linux" ]]; then
    COWORK_CONFIG="$HOME/.config/Claude/cowork_config.json"
fi

if [[ -f "$COWORK_CONFIG" ]]; then
    info "Encontrado config de Cowork: $COWORK_CONFIG"
    # Verificar si el JSON es válido
    if command -v jq &>/dev/null; then
        if ! jq empty "$COWORK_CONFIG" 2>/dev/null; then
            warn "Config de Cowork corrupto, haciendo backup..."
            mv "$COWORK_CONFIG" "${COWORK_CONFIG}.bak"
            info "Config reseteado. Cowork creará uno nuevo al iniciar."
        else
            info "Config de Cowork OK"
        fi
    fi
fi

# ============================================================================
# 8. Instrucciones finales
# ============================================================================
header "LIMPIEZA COMPLETADA"

echo ""
info "Pasos siguientes:"
echo "  1. Cierra completamente Claude Desktop (verificar en procesos)"
echo "  2. Espera 5 segundos"
echo "  3. Vuelve a abrir Claude Desktop"
echo ""
info "Si el problema persiste:"
echo "  - Desinstala Claude Desktop completamente"
echo "  - Elimina: rm -rf ~/.config/Claude ~/.local/share/Claude"
echo "  - Reinstala desde: https://claude.ai/download"
echo ""

# Verificar si Claude está corriendo
if pgrep -x "Claude" &>/dev/null || pgrep -f "claude-desktop" &>/dev/null; then
    warn "Claude Desktop está corriendo. Ciérralo para aplicar los cambios."
    echo ""
    read -p "¿Quieres cerrar Claude Desktop ahora? (s/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        pkill -x "Claude" 2>/dev/null || pkill -f "claude-desktop" 2>/dev/null || true
        info "Claude Desktop cerrado. Espera 5 segundos y ábrelo de nuevo."
    fi
fi

info "Script completado."
