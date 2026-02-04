# CLAUDE.md - Guía de Proyecto para Claude Code

## Proyecto
Claudio: Configuración local de desarrollo con Google Cloud, integrando Antigravity (Google) y Claude Code (Anthropic) con Cowork.

## Estructura
```
claudio/
├── setup.sh                          # Script maestro de instalación
├── config/
│   ├── .env                          # Variables de entorno (local, no commitear con secretos)
│   ├── .env.example                  # Template de variables de entorno
│   └── mcp/                          # Configs MCP adicionales
├── scripts/
│   ├── 01-install-gcloud.sh          # Google Cloud SDK + APIs
│   ├── 02-install-claude-code.sh     # Claude Code CLI + Vertex AI
│   ├── 03-install-antigravity.sh     # Antigravity IDE + Gemini CLI
│   ├── 04-setup-cowork-browsers.sh   # Cowork + Brave + Chrome
│   ├── 05-setup-mcp-integration.sh   # Servidores MCP compartidos
│   └── open-claude-extension.sh      # Helper para abrir extensión Claude
├── .mcp.json                         # MCP config a nivel de proyecto
├── .gitignore                        # Archivos ignorados
├── LICENSE                           # Apache 2.0
└── README.md                         # Documentación completa
```

## Comandos Importantes
- `bash setup.sh` - Instalación completa interactiva
- `bash scripts/01-install-gcloud.sh` - Solo Google Cloud
- `bash scripts/02-install-claude-code.sh` - Solo Claude Code
- `claude /status` - Verificar estado de Claude Code
- `agy .` - Abrir proyecto en Antigravity
- `gcloud config list` - Ver config de GCP

## Servicios Google Cloud Usados
- Vertex AI (backend para Claude Code)
- Cloud Storage (almacenamiento)
- Firebase/Firestore (base de datos)
- Cloud Run (deploy)
- Secret Manager (secretos)

## Integración MCP
Los servidores MCP están configurados para ser compartidos entre:
- Claude Code CLI (~/.claude/mcp.json)
- Claude Desktop/Cowork (~/.config/Claude/claude_desktop_config.json)
- Antigravity (~/.config/Antigravity/User/mcp.json)
- Proyecto local (.mcp.json)
