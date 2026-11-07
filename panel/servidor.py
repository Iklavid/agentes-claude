"""Estado de los agentes de Claude en el puerto 8797.

/            página para la tablet (index.html)
/estado.json por agente: libre, ocupado o parado; velocidad; tokens de hoy; contexto; tareas de pendientes.md

Datos: ~/.claude/sessions/<pid>.json (estado y conversación de cada proceso de Claude),
el registro de cada conversación (~/.claude/projects/.../<id>.jsonl) y AGENTES_BASE/pendientes.md.
Del límite de uso de la suscripción no hay datos en el Mac: no se muestra.
"""
import datetime as dt
import http.server
import json
import os
import re
import threading
import time
from pathlib import Path

PUERTO = 8797
CLAUDE = Path.home() / ".claude"
SESIONES = CLAUDE / "sessions"
BASE = Path(os.getenv("AGENTES_BASE", Path.home() / "claude-servidor")).expanduser().resolve()
REGISTROS = CLAUDE / "projects" / str(BASE).replace("/", "-")   # así nombra Claude Code la carpeta de cada proyecto
PENDIENTES = BASE / "pendientes.md"
INDEX = Path(__file__).with_name("index.html")
CADA = 30                               # segundos entre lecturas
AGENTES = [  # (sesión tmux, nombre, clave): adáptalo a tus agentes
           ("recepcion", "Recepción", "R"), ("claude", "Agente 1", "1"), ("claude2", "Agente 2", "2"),
           ("claude3", "Agente 3", "3"), ("claude4", "Agente 4", "4")]
AREAS = {"R": "Reparte el trabajo", "1": "Casa y seguridad", "2": "Jarvis y conocimiento",
         "3": "Salud y contenido", "4": "Multimedia y equipos"}


class Registro:
    """Lee un .jsonl de conversación poco a poco (solo lo nuevo) y guarda lo que hace falta."""

    def __init__(self, ruta):
        self.ruta, self.pos = ruta, 0
        self.respuestas = {}       # id -> (epoch, fecha, entrada, salida, cache); la última línea de cada id manda
        self.contexto = 0
        self.modelo = ""
        self.ultimo = ""           # última frase o herramienta

    def leer(self):
        try:
            tam = self.ruta.stat().st_size
        except OSError:
            return
        if tam < self.pos:
            self.__init__(self.ruta)
        with self.ruta.open("rb") as f:
            f.seek(self.pos)
            datos = f.read()
        corte = datos.rfind(b"\n") + 1
        self.pos += corte
        for linea in datos[:corte].splitlines():
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            if d.get("type") == "assistant" and not d.get("isSidechain"):
                self._respuesta(d)

    def _respuesta(self, d):
        m = d.get("message") or {}
        for b in m.get("content") or []:
            if b.get("type") == "text" and b.get("text", "").strip():
                self.ultimo = b["text"].strip().splitlines()[0]
            elif b.get("type") == "tool_use":
                entrada = b.get("input") or {}
                que = entrada.get("description") or entrada.get("summary") or Path(entrada.get("file_path", "")).name
                self.ultimo = f"{b.get('name')}: {que}".rstrip(": ")
        u, clave = m.get("usage"), m.get("id") or d.get("requestId")
        if not u:
            return
        t = dt.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).astimezone()
        cache = u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
        previo = self.respuestas.get(clave)
        self.respuestas[clave] = (previo[0] if previo else t.timestamp(), t.date().isoformat(),
                                  u.get("input_tokens", 0), u.get("output_tokens", 0), cache)
        self.contexto = u.get("input_tokens", 0) + cache + u.get("output_tokens", 0)
        self.modelo = m.get("model", self.modelo)


registros = {}


def _sesiones():
    """{tmux: datos de ~/.claude/sessions} de los procesos vivos."""
    vivas = {}
    for f in SESIONES.glob("*.json"):
        try:
            s = json.loads(f.read_text())
            os.kill(s["pid"], 0)
        except (ValueError, KeyError, OSError):
            continue
        tmux = (s.get("tmux") or "").split(":")[0]
        if tmux and s.get("updatedAt", 0) >= vivas.get(tmux, {}).get("updatedAt", 0):
            vivas[tmux] = s
    return vivas


def _tareas():
    """{agente: [tareas abiertas]} según la columna Agente de pendientes.md."""
    tareas = {}
    for linea in PENDIENTES.read_text().splitlines():
        c = [x.strip() for x in linea.strip().strip("|").split("|")]
        if len(c) < 3 or c[0] in ("Tarea", "---") or set(c[0]) <= {"-"}:
            continue
        if c[1].lower().startswith("hecha"):
            continue
        for a in re.findall(r"\b[1-4R]\b", c[2]):
            tareas.setdefault(a, []).append({"tarea": c[0], "estado": c[1] if len(c[1]) <= 70 else c[1][:68] + "…"})
    return tareas


def recoger():
    ahora = time.time()
    hoy = dt.date.today().isoformat()
    vivas, tareas = _sesiones(), _tareas()
    agentes = []
    for tmux, nombre, clave in AGENTES:
        s = vivas.get(tmux)
        a = {"clave": clave, "nombre": nombre, "area": AREAS[clave], "tareas": tareas.get(clave, []),
             "estado": "parado"}
        if s:
            a["estado"] = "ocupado" if s.get("status") == "busy" else "libre"
            a["desde"] = s.get("statusUpdatedAt", 0) / 1000
            ruta = REGISTROS / f"{s['sessionId']}.jsonl"
            r = registros.get(ruta) or registros.setdefault(ruta, Registro(ruta))
            r.leer()
            resp = r.respuestas.values()
            hoy_ = [x for x in resp if x[1] == hoy]
            a.update(tokens_min=round(sum(x[3] for x in resp if x[0] > ahora - 300) / 5),
                     respuestas_hora=sum(1 for x in resp if x[0] > ahora - 3600),
                     hoy={"entrada": sum(x[2] for x in hoy_), "salida": sum(x[3] for x in hoy_),
                          "cache": sum(x[4] for x in hoy_)}, contexto=r.contexto,
                     modelo=r.modelo, ultimo=r.ultimo[:140])
        agentes.append(a)
    return {"actualizado": ahora, "agentes": agentes}


estado = {"actualizado": 0, "agentes": []}


def bucle():
    global estado
    while True:
        try:
            estado = recoger()
        except Exception as e:
            print(f"{dt.datetime.now():%F %T} {e!r}", flush=True)
        time.sleep(CADA)


class Manejador(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta == "/estado.json":
            datos, tipo = json.dumps(estado, ensure_ascii=False).encode(), "application/json; charset=utf-8"
        elif ruta in ("/", "/index.html"):
            datos, tipo = INDEX.read_bytes(), "text/html; charset=utf-8"
        else:
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(datos)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=bucle, daemon=True).start()
    http.server.ThreadingHTTPServer((os.getenv("AGENTES_HOST", "127.0.0.1"), PUERTO), Manejador).serve_forever()
