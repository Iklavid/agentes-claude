# Agentes de Claude Code en un Mac (con Recepción)

[English](README.en.md)

Cómo tener varios agentes de [Claude Code](https://claude.com/claude-code) funcionando siempre en un ordenador de casa, cada uno con su área, y un agente **Recepción** que recibe los encargos y los reparte. Se manejan desde el móvil con Remote Control (app de Claude) o con un bot de Telegram.

```
  Tú (móvil) ──► Recepción ──► Agente 1 (casa)
                  │   ▲    ──► Agente 2 (asistente)
                  ▼   │    ──► Agente 3 (salud)
            pendientes.md  ──► Agente 4 (equipos)
```

## Piezas
| Archivo | Qué hace |
|---|---|
| `bin/claude-agente.sh` | Arranca cada agente en su sesión tmux, con Remote Control y Telegram si tiene bot. Si la sesión ya existe, no hace nada. |
| `launchd/com.ejemplo.claude-agente.plist` | Lo lanza al iniciar sesión y cada 5 minutos: si un agente se ha cerrado, vuelve a abrirse. |
| `plantillas/CLAUDE.md` | Reglas comunes: áreas, cómo se pasan las tareas y qué no se toca. |
| `plantillas/recepcion.md` | Papel de Recepción; se carga con `--append-system-prompt-file`. |
| `plantillas/pendientes.md` | Lista compartida de tareas: quién hace qué. |
| `hooks/guardia.py` | Hook `PreToolUse` que impide leer archivos de claves y cerrar las sesiones de los agentes. |
| `mejora/mejora.py` | Cada semana lee lo que has dicho a los agentes, busca correcciones repetidas y encargos que podrían ser skills, y te manda un resumen por Telegram. |
| `panel/` | Página que muestra cada agente (libre, ocupado o parado), su consumo de tokens y sus tareas. Va bien para una tablet. |

## Instalar (macOS)
1. Instala Claude Code y tmux (`brew install tmux`) e inicia sesión en Claude Code.
2. Crea la carpeta de trabajo con las reglas: `mkdir ~/claude-servidor` y copia ahí las tres plantillas. Adapta las áreas a lo tuyo.
3. Copia `bin/claude-agente.sh` a `~/bin/` y pruébalo: `~/bin/claude-agente.sh`, `~/bin/claude-agente.sh 2`, `~/bin/claude-agente.sh recepcion`.
4. Para cada agente, copia el plist cambiando el número, y actívalo con `launchctl bootstrap gui/$(id -u) <plist>`.
5. Guardia: copia `hooks/guardia.py` a `~/.claude/hooks/` y añade el bloque de `hooks/settings-ejemplo.json` a `~/.claude/settings.json`.
6. Telegram (opcional): crea un bot por agente con @BotFather y configura cada uno con el plugin de Telegram de Claude Code, en `~/.claude/channels/telegram-N/`.
7. Panel: `AGENTES_BASE=~/claude-servidor python3 panel/servidor.py` y abre http://127.0.0.1:8797.

Con 8 GB de RAM caben unos 3 o 4 agentes, porque cada uno gasta 350-450 MB.

**Aviso (macOS):** si cambias el «Acceso total al disco» de tmux en Ajustes, macOS cierra tmux y con él todos los agentes. launchd los vuelve a abrir en 5 minutos.

## Licencia
**Uso personal y no comercial gratuito** bajo la [PolyForm Noncommercial 1.0.0](LICENSE.md). Para usarlo en un negocio o venderlo hace falta una licencia comercial de pago: escríbeme por [GitHub](https://github.com/Iklavid).
Al limitar el uso comercial, esta licencia no es «open source» según la OSI; el código sigue siendo público.
`mejora/mejora.py` es una adaptación de *improve-system* ([charlie947/skills-for-everyone](https://github.com/charlie947/skills-for-everyone)) y conserva su licencia MIT (`mejora/LICENSE-MIT`).
