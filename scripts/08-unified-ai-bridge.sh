#!/usr/bin/env bash
# ============================================================================
# 08-unified-ai-bridge.sh
# Configura el puente unificado entre todas las IAs
# (Claude Code, Antigravity, OpenCode, ChatGPT, Jules)
# Permite conversación continua compartiendo memoria y contexto
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."

# ============================================================================
# 1. Configurar directorio de memoria compartida
# ============================================================================
header "CONFIGURANDO MEMORIA COMPARTIDA"

SHARED_MEMORY_DIR="$HOME/.ai-shared-memory"
mkdir -p "$SHARED_MEMORY_DIR"
mkdir -p "$SHARED_MEMORY_DIR/knowledge-graph"
mkdir -p "$SHARED_MEMORY_DIR/conversations"
mkdir -p "$SHARED_MEMORY_DIR/context"

info "Directorio de memoria compartida: $SHARED_MEMORY_DIR"

# ============================================================================
# 2. Crear archivo de Knowledge Graph compartido
# ============================================================================
header "INICIALIZANDO KNOWLEDGE GRAPH COMPARTIDO"

SHARED_GRAPH="$SHARED_MEMORY_DIR/knowledge-graph/shared-graph.json"

if [[ ! -f "$SHARED_GRAPH" ]]; then
    cat > "$SHARED_GRAPH" << 'GRAPHEOF'
{
  "entities": [],
  "relations": [],
  "observations": [],
  "metadata": {
    "created": "$(date -Iseconds)",
    "version": "1.0",
    "description": "Shared knowledge graph across Claude Code, Antigravity, OpenCode, and Cowork"
  }
}
GRAPHEOF
    info "Knowledge Graph compartido creado"
else
    info "Knowledge Graph compartido ya existe"
fi

# ============================================================================
# 3. Crear symlinks para unificar memoria
# ============================================================================
header "CREANDO SYMLINKS DE MEMORIA"

# Claude Code
mkdir -p "$HOME/.claude/memory"
ln -sf "$SHARED_GRAPH" "$HOME/.claude/memory/shared-graph.json" 2>/dev/null || true
info "Symlink: Claude Code -> memoria compartida"

# Claude Desktop / Cowork
mkdir -p "$HOME/.config/Claude/memory"
ln -sf "$SHARED_GRAPH" "$HOME/.config/Claude/memory/shared-graph.json" 2>/dev/null || true
info "Symlink: Claude Desktop -> memoria compartida"

# Antigravity
mkdir -p "$HOME/.antigravity/memory"
ln -sf "$SHARED_GRAPH" "$HOME/.antigravity/memory/shared-graph.json" 2>/dev/null || true
info "Symlink: Antigravity -> memoria compartida"

# OpenCode
mkdir -p "$HOME/.opencode/memory"
ln -sf "$SHARED_GRAPH" "$HOME/.opencode/memory/shared-graph.json" 2>/dev/null || true
info "Symlink: OpenCode -> memoria compartida"

# ============================================================================
# 4. Crear archivo de contexto persistente
# ============================================================================
header "CREANDO CONTEXTO PERSISTENTE"

CONTEXT_FILE="$SHARED_MEMORY_DIR/context/current-context.md"

cat > "$CONTEXT_FILE" << 'CONTEXTEOF'
# Contexto de Sesión Compartida

Este archivo es leído por todas las IAs (Claude Code, Antigravity, OpenCode, Cowork)
para mantener contexto continuo entre sesiones.

## Proyecto Actual
- Nombre: Claudio
- Ruta: /home/user/claudio
- Descripción: Configuración local con Google Cloud

## Estado Actual
- [Añadir estado actual aquí]

## Tareas Pendientes
- [Añadir tareas aquí]

## Notas Importantes
- [Añadir notas aquí]

## Decisiones Tomadas
- [Añadir decisiones aquí]

---
Última actualización: [Auto-actualizado por las IAs]
CONTEXTEOF

info "Archivo de contexto creado: $CONTEXT_FILE"

# ============================================================================
# 5. Crear CLAUDE.md que referencia el contexto compartido
# ============================================================================
header "ACTUALIZANDO CLAUDE.md CON CONTEXTO COMPARTIDO"

CLAUDE_MD="${PROJECT_DIR}/CLAUDE.md"

# Añadir sección de memoria compartida si no existe
if ! grep -q "MEMORIA COMPARTIDA" "$CLAUDE_MD" 2>/dev/null; then
    cat >> "$CLAUDE_MD" << 'CLAUDEEOF'

## Memoria Compartida
Este proyecto usa memoria compartida entre múltiples IAs:
- Archivo de contexto: ~/.ai-shared-memory/context/current-context.md
- Knowledge Graph: ~/.ai-shared-memory/knowledge-graph/shared-graph.json

Al iniciar una sesión, lee el contexto. Al terminar, actualízalo.

### IAs Integradas
- **Claude Code** (CLI): Para codificación precisa
- **Antigravity** (IDE): Para planificación con Gemini 3 Pro
- **OpenCode**: Para usar modelos alternativos
- **Cowork**: Para tareas de escritorio
- **Jules**: Para tareas asíncronas de código
- **ChatGPT/Codex**: Para capacidades adicionales

### Comandos Útiles
- Sincronizar memoria: `bash scripts/09-sync-memory.sh`
- Ver contexto: `cat ~/.ai-shared-memory/context/current-context.md`
CLAUDEEOF
    info "CLAUDE.md actualizado con sección de memoria compartida"
fi

# ============================================================================
# 6. Crear script de sincronización de memoria
# ============================================================================
header "CREANDO SCRIPT DE SINCRONIZACIÓN"

cat > "${SCRIPT_DIR}/09-sync-memory.sh" << 'SYNCEOF'
#!/usr/bin/env bash
# Sincroniza memoria entre todas las IAs
set -euo pipefail

SHARED_MEMORY_DIR="$HOME/.ai-shared-memory"
CONTEXT_FILE="$SHARED_MEMORY_DIR/context/current-context.md"

echo "=== Sincronizando Memoria Compartida ==="

# Actualizar timestamp
sed -i "s|Última actualización:.*|Última actualización: $(date)|" "$CONTEXT_FILE" 2>/dev/null || true

# Backup del knowledge graph
BACKUP_DIR="$SHARED_MEMORY_DIR/backups"
mkdir -p "$BACKUP_DIR"
cp "$SHARED_MEMORY_DIR/knowledge-graph/shared-graph.json" \
   "$BACKUP_DIR/shared-graph-$(date +%Y%m%d-%H%M%S).json" 2>/dev/null || true

# Limpiar backups antiguos (mantener últimos 10)
ls -t "$BACKUP_DIR"/*.json 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

echo "Memoria sincronizada: $(date)"
echo "Contexto: $CONTEXT_FILE"
SYNCEOF

chmod +x "${SCRIPT_DIR}/09-sync-memory.sh"
info "Script de sincronización creado"

# ============================================================================
# 7. Crear MCP config para memoria compartida
# ============================================================================
header "CONFIGURANDO MCP DE MEMORIA COMPARTIDA"

SHARED_MCP_CONFIG="$SHARED_MEMORY_DIR/mcp-shared.json"

cat > "$SHARED_MCP_CONFIG" << MCPEOF
{
  "description": "Configuración MCP compartida entre todas las IAs",
  "mcpServers": {
    "shared-memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": {
        "MEMORY_FILE": "$SHARED_MEMORY_DIR/knowledge-graph/shared-graph.json"
      }
    },
    "shared-filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic-ai/mcp-server-filesystem",
        "$SHARED_MEMORY_DIR",
        "/home/user/claudio"
      ]
    }
  }
}
MCPEOF

info "Configuración MCP compartida creada"

# ============================================================================
# 8. Crear alias para acceso rápido
# ============================================================================
header "CREANDO ALIASES"

SHELL_RC=""
if [[ -f "$HOME/.zshrc" ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ -f "$HOME/.bashrc" ]]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [[ -n "$SHELL_RC" ]]; then
    # Verificar si ya existen
    if ! grep -q "# Claudio AI Aliases" "$SHELL_RC" 2>/dev/null; then
        cat >> "$SHELL_RC" << 'ALIASEOF'

# Claudio AI Aliases
alias ai-context='cat ~/.ai-shared-memory/context/current-context.md'
alias ai-sync='bash ~/claudio/scripts/09-sync-memory.sh'
alias ai-memory='cat ~/.ai-shared-memory/knowledge-graph/shared-graph.json | jq .'
alias claude-start='cd ~/claudio && claude'
alias agy-start='cd ~/claudio && agy .'
ALIASEOF
        info "Aliases añadidos a $SHELL_RC"
        info "Ejecuta 'source $SHELL_RC' para activarlos"
    else
        info "Aliases ya existentes en $SHELL_RC"
    fi
fi

# ============================================================================
# 9. Resumen
# ============================================================================
header "PUENTE UNIFICADO CONFIGURADO"

echo ""
info "Estructura de memoria compartida:"
echo "  $SHARED_MEMORY_DIR/"
echo "  ├── knowledge-graph/"
echo "  │   └── shared-graph.json  <- Knowledge Graph compartido"
echo "  ├── context/"
echo "  │   └── current-context.md <- Contexto actual"
echo "  ├── conversations/"
echo "  │   └── [historiales]"
echo "  ├── backups/"
echo "  │   └── [backups automáticos]"
echo "  └── mcp-shared.json"
echo ""
info "Todas las IAs ahora comparten:"
echo "  - Knowledge Graph persistente"
echo "  - Contexto de proyecto"
echo "  - Archivos del proyecto"
echo ""
info "Comandos rápidos (después de recargar shell):"
echo "  ai-context  -> Ver contexto actual"
echo "  ai-sync     -> Sincronizar memoria"
echo "  ai-memory   -> Ver knowledge graph"
echo ""
info "Para conversación continua:"
echo "  1. Actualiza el contexto al terminar cada sesión"
echo "  2. El Knowledge Graph se actualiza automáticamente"
echo "  3. Todas las IAs leerán el mismo contexto"
