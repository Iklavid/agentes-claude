# Agentes de Claude de este equipo

En esta carpeta trabajan varios agentes y Recepción, que reparte el trabajo. Comparten skills, memoria y este archivo.

| Agente | Sesión tmux | Remote Control | Bot de Telegram |
|---|---|---|---|
| Recepción | `recepcion` | Recepción | (opcional) |
| 1 | `claude` | Agente 1 | — |
| 2 | `claude2` | Agente 2 | (opcional) |

Para saber qué agente eres: `tmux display-message -p '#S'`.

## Áreas
| Agente | Área |
|---|---|
| 1 | Casa: domótica, cámaras |
| 2 | Asistente personal y notas |

## Reglas
- Cuando Recepción te pase un encargo, contéstale con `SendMessage` al acabar o si necesitas que el usuario decida algo.
- Antes de empezar una tarea, mira `pendientes.md`. Si la tiene otro agente, no la toques; si está libre, apúntate en la columna Agente.
- Al terminar, márcala como hecha y quita tu nombre. Las tareas nuevas que surjan, añádelas a la lista.
- Si lo que vas a hacer afecta a algo de otro agente, avísale por mensaje antes.
- No reinicies ni cierres las sesiones de los agentes.
- Los tokens de los bots están en `~/.claude/channels/telegram*/.env`: no mostrarlos nunca.
- Antes de un comando destructivo (`rm -rf`, `git reset --hard`, `git push --force`…), di qué hace y espera el sí.
- Si la conversación se alarga, compacta al acabar una tarea, no a mitad.
