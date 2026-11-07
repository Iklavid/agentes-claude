#!/usr/bin/env python3
"""Guardia de los agentes del Mac: para antes de ejecutarse lo que el CLAUDE.md prohíbe.

- Leer o mostrar archivos de claves (tokens de los bots, telegram.env, local.env…).
  Se permite verlos enmascarados: sed 's/=.*/=…/' o cut -d= -f1 (solo nombres de variables).
- Cerrar las sesiones tmux de los agentes o el servidor tmux, o parar sus servicios launchd.
- Tocar los permisos de macOS (acceso total al disco de tmux).

PreToolUse: lee el JSON por la entrada estándar; sale con 2 y el motivo para bloquear. Sin red.
"""
import json, re, sys

# Añade aquí tus propios archivos de claves
CLAVES = re.compile(r"channels/telegram[^/\s]*/\.env|telegram\.env|\blocal\.env\b|(^|/)\.env\b"
                    r"|\.ssh/id_[^\s.]*(\s|$)")
ENMASCARADO = re.compile(r"s/=\.\*/|cut\s+-d\s*['\"]?=['\"]?\s+-f\s*1")
LEER = {"cat", "less", "more", "head", "tail", "bat", "strings", "xxd", "od", "nl", "grep", "egrep", "rg", "awk",
        "base64", "open", "pbcopy", "cp", "scp", "rsync"}
TROZOS = re.compile(r"[;&|\n]+|\$\(|`")   # cada orden simple de la línea
SESIONES = r"(claude|claude2|claude3|claude4|recepcion)"
CERRAR = [
    (re.compile(r"tmux\s+kill-server|(pkill|killall)\s+(-\w+\s+)*tmux"), "cerrar tmux corta a todos los agentes"),
    (re.compile(rf"tmux\s+kill-session\s+(-\w\s+)*-t\s*['\"]?{SESIONES}['\"]?(\s|$|;|&)"), "no se cierran las sesiones de los agentes"),
    (re.compile(r"launchctl\s+(unload|bootout|kickstart\s+-k|stop|remove|disable)\b.*com\.ejemplo\.claude-"), "no se paran los servicios de los agentes"),
    (re.compile(r"tccutil\s+reset|TCC\.db"), "no se tocan los permisos de macOS (acceso total al disco de tmux)"),
]


def motivo(herramienta, datos):
    if herramienta == "Bash":
        cmd = datos.get("command", "")
        for rx, porque in CERRAR:
            if rx.search(cmd):
                return porque
        # solo si la orden que lee es la que lleva la ruta (no un texto que la nombra)
        lee = any(t.split()[0].rsplit("/", 1)[-1] in LEER and CLAVES.search(t + " ")
                  for t in TROZOS.split(cmd) if t.split())
        if lee and not ENMASCARADO.search(cmd):
            return "no se muestran claves: usa sed 's/=.*/=…/' para ver solo los nombres de las variables"
    elif herramienta in ("Read", "Grep"):
        ruta = datos.get("file_path") or datos.get("path") or ""
        if CLAVES.search(ruta + " "):
            return "no se leen archivos de claves"
    return None


def main():
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return 0
    m = motivo(ev.get("tool_name", ""), ev.get("tool_input") or {})
    if m:
        print(f"Bloqueado por la guardia (~/.claude/hooks/guardia.py): {m}.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
