# Claudio

Configuración local de desarrollo integrado con servicios de Google Cloud, combinando **Google Antigravity**, **Claude Code** y **Cowork** en un entorno unificado.

## Qué incluye

| Herramienta | Función | Backend Cloud |
|---|---|---|
| **Google Cloud SDK** | CLI y APIs de Google Cloud | GCP (Storage, Vertex AI, Firestore, Cloud Run) |
| **Claude Code CLI** | Asistente de código en terminal | Google Vertex AI |
| **Google Antigravity** | IDE agéntico (fork de VS Code) | Gemini 3 Pro + Claude Opus 4.5 |
| **Cowork** | Agente de escritorio (Claude Desktop) | Anthropic API / Vertex AI |
| **Claude in Chrome** | Extensión de navegador | Chrome + Brave |
| **Servidores MCP** | Protocolo de contexto compartido | Firebase, GCS, GitHub |

## Instalación rápida

```bash
# 1. Clona el repositorio
git clone https://github.com/israel2811/claudio.git
cd claudio

# 2. Configura tus variables de entorno
cp config/.env.example config/.env
# Edita config/.env con tu GCP_PROJECT_ID

# 3. Ejecuta el instalador
bash setup.sh
```

El script `setup.sh` ofrece un menú interactivo para instalar todo junto o componentes individuales.

## Instalación por componentes

```bash
# Solo Google Cloud SDK + APIs
bash scripts/01-install-gcloud.sh

# Solo Claude Code CLI + Vertex AI
bash scripts/02-install-claude-code.sh

# Solo Google Antigravity + Gemini CLI
bash scripts/03-install-antigravity.sh

# Solo Cowork + Navegadores (Brave/Chrome)
bash scripts/04-setup-cowork-browsers.sh

# Solo integraciones MCP
bash scripts/05-setup-mcp-integration.sh
```

## Estructura del proyecto

```
claudio/
├── setup.sh                          # Instalador maestro (menú interactivo)
├── CLAUDE.md                         # Guía para Claude Code
├── .mcp.json                         # Servidores MCP del proyecto
├── .gitignore
├── config/
│   ├── .env.example                  # Template de variables
│   └── .env                          # Variables locales (no se commitea)
└── scripts/
    ├── 01-install-gcloud.sh          # Google Cloud SDK + APIs
    ├── 02-install-claude-code.sh     # Claude Code + Vertex AI
    ├── 03-install-antigravity.sh     # Antigravity IDE + extensiones
    ├── 04-setup-cowork-browsers.sh   # Cowork + Brave + Chrome
    ├── 05-setup-mcp-integration.sh   # MCP (Antigravity <-> Claude Code)
    └── open-claude-extension.sh      # Abre extensión Claude en navegadores
```

## Arquitectura de integración

```
┌─────────────────────────────────────────────────────────────┐
│                    ENTORNO LOCAL                             │
│                                                             │
│  ┌──────────────┐     MCP      ┌──────────────────┐       │
│  │  Antigravity  │◄───────────►│   Claude Code     │       │
│  │  (IDE/Agente) │             │   (CLI/Terminal)   │       │
│  │  Gemini 3 Pro │             │   Claude Opus 4.5  │       │
│  └──────┬───────┘             └────────┬───────────┘       │
│         │                              │                    │
│  ┌──────┴───────┐             ┌────────┴───────────┐       │
│  │    Browser    │             │      Cowork         │       │
│  │ (Chrome/Brave)│             │  (Claude Desktop)   │       │
│  │ Ext. Claude   │             │  Agente escritorio   │       │
│  └──────────────┘             └────────────────────┘       │
│                                                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                    ┌─────┴─────┐
                    │  MCP Layer │
                    └─────┬─────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                    GOOGLE CLOUD                              │
│                                                             │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ │
│  │  Vertex AI   │ │  Cloud   │ │ Firebase  │ │ Cloud Run │ │
│  │  (Claude +   │ │ Storage  │ │ Firestore │ │  (Deploy) │ │
│  │   Gemini)    │ │  (GCS)   │ │   (DB)    │ │           │ │
│  └─────────────┘ └──────────┘ └───────────┘ └───────────┘ │
│                                                             │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐               │
│  │   Secret    │ │   IAM    │ │  Cloud    │               │
│  │   Manager   │ │          │ │  Build    │               │
│  └─────────────┘ └──────────┘ └───────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Configuración de Google Cloud

### Requisitos previos
- Cuenta de Google Cloud con billing habilitado
- Proyecto creado en Google Cloud Console

### APIs habilitadas automáticamente
- `aiplatform.googleapis.com` - Vertex AI (backend de Claude Code)
- `storage.googleapis.com` - Cloud Storage
- `firestore.googleapis.com` - Firestore
- `run.googleapis.com` - Cloud Run
- `cloudbuild.googleapis.com` - Cloud Build
- `secretmanager.googleapis.com` - Secret Manager
- `iam.googleapis.com` - IAM
- `compute.googleapis.com` - Compute Engine

## Claude Code + Vertex AI

Claude Code se configura para usar Google Vertex AI como backend, lo que significa:
- La autenticación es via `gcloud auth application-default login`
- Los comandos `/login` y `/logout` se desactivan
- El modelo se ejecuta en la infraestructura de Google Cloud
- Las variables clave son:

```bash
CLAUDE_CODE_USE_VERTEX=1
CLOUD_ML_REGION=global
ANTHROPIC_VERTEX_PROJECT_ID=tu-proyecto
```

Verifica con: `claude` luego `/status` (debe mostrar "API provider: Google Vertex AI").

## Integración MCP (Model Context Protocol)

MCP es el "USB-C de los LLMs" - permite que Antigravity, Claude Code y Cowork compartan acceso a los mismos servicios. Los servidores MCP configurados son:

| Servidor | Función | Herramientas conectadas |
|---|---|---|
| Firebase | Base de datos, hosting | Antigravity, Claude Code, Cowork |
| Google Cloud Storage | Archivos en la nube | Antigravity, Claude Code, Cowork |
| GitHub | Repos, PRs, issues | Antigravity, Claude Code |
| Filesystem | Archivos locales | Claude Code, Cowork |
| Claude Code Bridge | Claude como MCP server | Antigravity |

### Archivos de configuración MCP generados

| Archivo | Para qué |
|---|---|
| `~/.claude/mcp.json` | Claude Code CLI |
| `~/.config/Claude/claude_desktop_config.json` | Claude Desktop / Cowork |
| `~/.config/Antigravity/User/mcp.json` | Antigravity IDE |
| `.mcp.json` (raíz del proyecto) | Configuración por proyecto |

## Navegadores: Brave y Chrome

La extensión **Claude in Chrome** funciona en ambos navegadores ya que Brave está basado en Chromium.

### Instalación
1. Abre la [extensión en Chrome Web Store](https://chromewebstore.google.com/detail/claude/hbpcjcmaepkknjiakjhmmpdkbjdcacoj)
2. Haz clic en "Añadir a Chrome" / "Añadir a Brave"
3. Inicia sesión con tu cuenta Claude

### Cowork + Chrome
Cuando Cowork está activo y la extensión Claude in Chrome está instalada, Claude puede realizar tareas que requieren acceso al navegador.

## Workflow recomendado (Antigravity + Claude Code)

1. **Planificación**: Usa Antigravity Manager con Gemini 3 Pro para planear
2. **Codificación**: Claude Code en terminal para implementación precisa
3. **Testing**: Agentes de Antigravity con browser integrado
4. **Deploy**: Cloud Run / Firebase via MCP
5. **Documentación**: Cowork para generar docs y presentaciones

## Requisitos del sistema

- **OS**: Linux (Ubuntu/Debian recomendado), macOS, o Windows (WSL2)
- **Node.js**: 18+ (recomendado 20 LTS)
- **Python**: 3.8+
- **Cuenta Google Cloud**: Con billing habilitado
- **Cuenta Anthropic**: Para Claude Code (o usar Vertex AI)
- **Suscripción Claude Max**: Requerida para Cowork ($100-200/mes)

## Solución de problemas

### `agy` no se encuentra en Linux
```bash
# Crear symlink si se instaló como 'antigravity'
sudo ln -sf /usr/bin/antigravity /usr/local/bin/agy
```

### Claude Code no conecta a Vertex AI
```bash
# Verificar autenticación
gcloud auth application-default print-access-token
# Re-autenticar si es necesario
gcloud auth application-default login
# Verificar API habilitada
gcloud services list --filter="name:aiplatform.googleapis.com"
```

### Extensión Claude no aparece en Brave
Brave soporta extensiones del Chrome Web Store, pero debes habilitarlo:
1. Ve a `brave://extensions/`
2. Activa "Allow extensions from other stores" si está desactivado
3. Instala desde Chrome Web Store

### Errores 429 (rate limit) en Claude Code
Configura presupuestos y alertas en Google Cloud Console para evitar sorpresas con cuotas de Vertex AI.

## Licencia

Apache 2.0 - Ver [LICENSE](LICENSE)
