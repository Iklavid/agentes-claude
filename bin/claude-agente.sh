#!/bin/zsh
# Uso: claude-agente.sh [N|recepcion]   (sin número = agente 1; 2, 3, 4 = agentes extra; recepcion = el que reparte)
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$HOME/.bun/bin:/usr/local/bin:/usr/bin:/bin"
export LANG=es_ES.UTF-8
cd "$HOME/claude-servidor"
LOG="$HOME/claude-servidor/salidas.log"
N="$1"
if [[ -z "$N" ]]; then
  SESION=claude; NOMBRE="Agente 1"; ENTORNO=""
elif [[ "$N" == recepcion ]]; then
  SESION=recepcion; NOMBRE="Recepción"
  ENTORNO="TELEGRAM_STATE_DIR=$HOME/.claude/channels/telegram-$N "
  EXTRA=" --append-system-prompt-file $HOME/claude-servidor/recepcion.md"
else
  SESION="claude$N"; NOMBRE="Agente $N"
  ENTORNO="TELEGRAM_STATE_DIR=$HOME/.claude/channels/telegram-$N "
fi
# Telegram solo si ese agente tiene bot (si no, se maneja solo por Remote Control)
DIR_BOT="$HOME/.claude/channels/telegram${N:+-$N}"
CANALES=""
[[ -f "$DIR_BOT/.env" ]] && CANALES=" --channels plugin:telegram@claude-plugins-official"
if ! tmux has-session -t "$SESION" 2>/dev/null; then
  echo "$(date) [$SESION] arranque (no había sesión)" >> "$LOG"
  tmux new-session -d -s "$SESION" "${ENTORNO}claude --remote-control '$NOMBRE'$CANALES$EXTRA; s=\$?; echo \"\$(date) [$SESION] salida \$s\" >> $LOG; sleep 60"
fi
