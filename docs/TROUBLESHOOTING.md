# Solucion de Problemas - Claudio

## Error: No puedo ingresar prompts en Claude Code

### Causa 1: No estas autenticado
**Solucion:**
```bash
# Abre una terminal y ejecuta:
claude

# Sigue las instrucciones para autenticarte
# Se abrira tu navegador para iniciar sesion
```

### Causa 2: Token expirado
**Solucion:**
```bash
# Cierra sesion y vuelve a autenticarte:
claude logout
claude login
```

### Causa 3: Problema con la terminal
**Solucion:**
```bash
# Cierra la terminal actual
# Abre una nueva terminal
# Ejecuta claude de nuevo
```

### Causa 4: Permisos de teclado (Linux/Mac)
**Solucion:**
```bash
# En Linux, verifica que tu terminal tiene permisos de entrada
# Prueba con otra terminal: gnome-terminal, konsole, xterm

# En Mac, ve a:
# Preferencias del Sistema > Privacidad y Seguridad > Accesibilidad
# Asegurate de que tu terminal tiene permisos
```

---

## Usar Claude Cowork en el navegador

### Opcion 1: Claude.ai directo
1. Ve a: **https://claude.ai**
2. Inicia sesion con tu cuenta Anthropic
3. Haz clic en el icono de **llave inglesa** (arriba a la derecha)
4. Esto abre Cowork

### Opcion 2: URL directa
1. Ve a: **https://claude.ai/code**
2. Esto te lleva directamente a Cowork

### Requisitos para Cowork
- Necesitas suscripcion **Claude Max** ($100-200 USD/mes)
- Si no tienes Max, solo podras usar Claude chat normal

---

## Usar Claude Code en local

### Instalacion rapida
```bash
# Opcion 1: Usando el script de este proyecto
cd /home/user/claudio
bash scripts/quick-setup.sh

# Opcion 2: Instalacion manual
npm install -g @anthropic-ai/claude-code
```

### Primer uso
```bash
# Ejecuta claude en cualquier directorio
claude

# Primera vez: se abrira tu navegador para autenticarte
# Despues: podras escribir tus prompts directamente
```

### Verificar instalacion
```bash
claude --version
# Deberia mostrar algo como: 2.1.19 (Claude Code)
```

---

## Errores comunes de MCP

### Error: Firebase MCP no conecta
```bash
# Instala firebase-tools globalmente
npm install -g firebase-tools

# Autenticate con Firebase
firebase login
```

### Error: Filesystem MCP no funciona
```bash
# Verifica que el path en .mcp.json existe
# El path debe ser absoluto, ejemplo:
# "/home/user/claudio" (correcto)
# "./claudio" (incorrecto)
```

---

## Contacto y ayuda

- **Claude Code Issues:** https://github.com/anthropics/claude-code/issues
- **Anthropic Support:** https://support.anthropic.com
- **Este proyecto:** https://github.com/israel2811/claudio/issues
