#!/bin/bash
# ============================================================================
# CLAUDIO - Quick Setup
# Script rapido para configurar Claude Code local y Cowork
# ============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     CLAUDIO - Quick Setup             ║"
echo "  ║  Claude Code Local + Cowork Browser   ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# Verificar Node.js
echo -e "${YELLOW}[1/5] Verificando Node.js...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v)
    echo -e "${GREEN}  ✓ Node.js instalado: $NODE_VERSION${NC}"
else
    echo -e "${RED}  ✗ Node.js no encontrado. Instalando...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Verificar/Instalar Claude Code CLI
echo -e "${YELLOW}[2/5] Verificando Claude Code CLI...${NC}"
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "instalado")
    echo -e "${GREEN}  ✓ Claude Code CLI: $CLAUDE_VERSION${NC}"
else
    echo -e "${BLUE}  → Instalando Claude Code CLI...${NC}"
    npm install -g @anthropic-ai/claude-code
fi

# Crear directorio de configuracion
echo -e "${YELLOW}[3/5] Configurando directorios...${NC}"
mkdir -p ~/.claude
mkdir -p ~/.config/Claude

# Crear configuracion MCP para Claude Code
echo -e "${YELLOW}[4/5] Configurando MCP servers...${NC}"
cat > ~/.claude/mcp.json << 'MCPEOF'
{
    "mcpServers": {
        "firebase": {
            "command": "npx",
            "args": ["-y", "firebase-tools@latest", "experimental:mcp"]
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@anthropic-ai/mcp-server-filesystem", "/home/user"]
        }
    }
}
MCPEOF
echo -e "${GREEN}  ✓ ~/.claude/mcp.json creado${NC}"

# Crear configuracion para Claude Desktop (Cowork)
cat > ~/.config/Claude/claude_desktop_config.json << 'DESKTOPEOF'
{
    "mcpServers": {
        "firebase": {
            "command": "npx",
            "args": ["-y", "firebase-tools@latest", "experimental:mcp"]
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@anthropic-ai/mcp-server-filesystem", "/home/user"]
        }
    },
    "globalShortcut": "Ctrl+Shift+Space"
}
DESKTOPEOF
echo -e "${GREEN}  ✓ ~/.config/Claude/claude_desktop_config.json creado${NC}"

# Instrucciones finales
echo -e "${YELLOW}[5/5] Configuracion completada!${NC}"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}SIGUIENTE PASO:${NC}"
echo ""
echo -e "${YELLOW}Para usar Claude Code en local:${NC}"
echo "  1. Abre una terminal nueva"
echo "  2. Ejecuta: claude"
echo "  3. Sigue las instrucciones para autenticarte"
echo ""
echo -e "${YELLOW}Para usar Claude Cowork en el navegador:${NC}"
echo "  1. Ve a: https://claude.ai"
echo "  2. Inicia sesion con tu cuenta"
echo "  3. Haz clic en el icono de llave inglesa (Cowork)"
echo "  4. O visita directamente: https://claude.ai/code"
echo ""
echo -e "${YELLOW}Nota sobre suscripcion:${NC}"
echo "  - Claude Code CLI: Gratis con limites / Pro para mas uso"
echo "  - Cowork (claude.ai/code): Requiere suscripcion Claude Max"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
