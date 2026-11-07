#!/usr/bin/env python3
"""Mejora semanal de los agentes (versión en español de «improve-system», charlie947/skills-for-everyone).

Lee lo que el usuario dice a los agentes en la última semana (conversaciones de ~/.claude/projects: lo escrito en el
terminal, Telegram y lo que reenvía Recepción) y busca:
  1. correcciones que se repiten (una regla o skill debería haberlas evitado)
  2. encargos repetidos (candidatos a skill)
  3. tiempo por área
Escribe el informe en mejora/informes/AAAA-MM-DD.md (+ .json), manda un resumen por Telegram y
apunta en pendientes.md que un agente (AGENTES_REVISOR) lo revise. La primera semana de cada mes apunta también la revisión de
skills, memoria y CLAUDE.md. Solo lee las conversaciones; no usa más red que el envío a Telegram.

Uso: mejora.py [--dias 7] [--sin-avisos]   (por ejemplo, con launchd los domingos a las 21:00)
"""
import argparse, collections, datetime, glob, json, os, re, subprocess, time
from pathlib import Path

HOME = Path.home()
CONVERSACIONES = HOME / ".claude/projects"
SKILLS = HOME / ".claude/skills"
AQUI = Path(__file__).resolve().parent
INFORMES = AQUI / "informes"
PENDIENTES = AQUI.parent / "pendientes.md"
TELEGRAM = Path(os.getenv("AGENTES_TELEGRAM", HOME / ".config/agentes-telegram.env"))  # TOKEN=… y CHAT_ID=…
USUARIO = os.getenv("AGENTES_USUARIO", "Usuario")   # tu nombre, tal como lo citan Recepción y los agentes
REVISOR = os.getenv("AGENTES_REVISOR", "1")         # agente que revisa el informe

CORRECCION = re.compile(
    r"\b(no es eso|eso no|est[aá] mal|no funciona|no va\b|sigue (sin|igual|mal|fallando|saliendo|quitando)|otra vez|de nuevo"
    r"|ya te (lo )?(dije|he dicho|ped[ií])|te (lo )?(dije|he dicho)|cu[aá]ntas veces|no te (he )?ped[ií]|no quiero"
    r"|no me (gusta|expliques|des|mandes)|por qu[eé] (has|me|no|lo)|no hagas|deja de|para de|no ha cambiado|no sirve"
    r"|al rev[eé]s|te has equivocado|equivocad|no era|tampoco|mal hecho|no lo (has|hiciste))\b", re.I)
REPETIDA = re.compile(r"\b(otra vez|sigue|de nuevo|ya te|te (lo )?(dije|he dicho)|cu[aá]ntas veces|todav[ií]a|a[uú]n"
                      r"|no ha cambiado|igual que antes|tampoco)\b", re.I)
AREAS = [  # ejemplo: adapta las áreas y palabras a tus agentes
("riego", r"riego|v[aá]lvula|nodo|esp-?now|bomba|mqtt|puente"),
         ("jarvis", r"jarvis|b[oó]veda|whatsapp|gafas|obsidian"),
         ("casa y cámaras", r"home assistant|c[aá]mara|enchufe|lavadora|domótica|detecci[oó]n|saludo|tele\b"),
         ("salud y cuaderno", r"cuaderno|entreno|salud|comida|gimnasio|watch|pulso"),
         ("vídeos y juegos", r"v[ií]deo|tiktok|youtube|asmr|juego|colchoneta"),
         ("seguridad y red", r"maltrail|adguard|dns|vpn|warp|tailscale|seguridad|cortafuegos"),
         ("equipos", r"\bpc\b|mac\b|lenovo|windows|cachyos|disco|actualiz|copia|time machine|jellyfin|syncthing"),
         ("impresión 3d", r"stl|impres|k1\b|filamento|orca"),
         ("agentes y claude", r"agente|skill|recepci[oó]n|claude|pendientes|hook|memoria")]
VACIAS = set("""a al algo como con de del el ella ellos en eso esta este esto ha han has hay la las le lo los me mi mis muy
nos o para pero por que qué se si sí sin su sus te tu un una uno y ya yo es son está están era fue ser hacer hace haz pon
puedes puede quiero dime mira ok vale bien gracias también más menos todo todos cuando donde dónde ahora luego hoy mañana
usuario dice agente recepción""".split())
SECRETO = re.compile(r"[A-Za-z0-9_\-:]{28,}")


def textos(d):
    """Lo que dijo el usuario en una línea de conversación, o nada si es una herramienta o un aviso del sistema."""
    m = d.get("message", {}).get("content")
    if isinstance(m, list):
        m = " ".join(x.get("text", "") for x in m if x.get("type") == "text")
    if not isinstance(m, str) or m.startswith("This session is being continued"):
        return []
    trozos = re.findall(r"<channel [^>]*>(.*?)</channel>", m, re.S)
    # de lo que reenvían Recepción y los agentes, solo las palabras del usuario entre comillas
    for cuerpo in re.findall(r"<cross-session-message [^>]*>(.*?)</cross-session-message>", m, re.S):
        if USUARIO in cuerpo:
            trozos += re.findall(r"[«\"]([^«»\"]{8,})[»\"]", cuerpo)
    if not trozos and "<cross-session-message" not in m and \
            not m.lstrip().startswith(("<", "[", "Base directory", "Continue from where", "Caveat", "Another Claude")):
        trozos = [m]
    return [re.sub(r"\s+", " ", t).strip() for t in trozos if t.strip()]


def cargar(dias):
    corte = time.time() - dias * 86400
    filas, vistos = [], set()
    for f in glob.glob(str(CONVERSACIONES / "*/*.jsonl")):
        if Path(f).stat().st_mtime < corte:
            continue
        for linea in open(f, encoding="utf-8", errors="replace"):
            if '"type":"user"' not in linea:
                continue
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            ts = datetime.datetime.fromisoformat(d.get("timestamp", "1970-01-01T00:00:00").replace("Z", "+00:00")).timestamp()
            if ts < corte:
                continue
            for t in textos(d):
                if (t, int(ts // 60)) in vistos:      # la misma frase en una conversación reanudada
                    continue
                vistos.add((t, int(ts // 60)))
                filas.append({"ts": ts, "sesion": d.get("sessionId", Path(f).stem), "texto": SECRETO.sub("«…»", t)})
    return sorted(filas, key=lambda r: r["ts"])


def area(texto):
    c = collections.Counter({n: len(re.findall(rx, texto, re.I)) for n, rx in AREAS})
    n, k = c.most_common(1)[0]
    return n if k else "otros"


def palabras(t):
    return [w for w in re.findall(r"[a-záéíóúñü]{4,}", t.lower()) if w not in VACIAS]


def dia(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%d-%m")


def analizar(filas):
    corr = [r for r in filas if CORRECCION.search(r["texto"])]
    por_area = collections.defaultdict(list)
    for r in corr:
        por_area[area(r["texto"])].append(r)
    correcciones = sorted(({"area": a, "total": len(rs), "repetidas": sum(bool(REPETIDA.search(r["texto"])) for r in rs),
                            "citas": [f'{dia(r["ts"])} {"(REPETIDA) " if REPETIDA.search(r["texto"]) else ""}«{r["texto"][:200]}»'
                                      for r in rs]} for a, rs in por_area.items()),
                          key=lambda x: (-x["repetidas"], -x["total"]))
    grupos = collections.defaultdict(list)
    for r in filas:
        clave = " ".join(sorted(palabras(r["texto"])[:3]))
        if len(clave.split()) == 3:
            grupos[clave].append(r)
    skills = {p.name: set(palabras(p.name.replace("-", " ") + " " + p.read_text(errors="replace")[:1500]))
              for p in (s / "SKILL.md" for s in SKILLS.iterdir()) if p.exists()}
    repetidos = []
    for clave, rs in grupos.items():
        ses = {r["sesion"] for r in rs}
        if len(rs) >= 3:
            kw = set(clave.split())
            cerca = max(skills, key=lambda s: len(kw & skills[s]), default=None)
            repetidos.append({"encargo": clave, "veces": len(rs), "sesiones": len(ses), "ejemplo": rs[-1]["texto"][:160],
                              "skill_cercana": cerca if cerca and len(kw & skills[cerca]) >= 2 else None})
    repetidos.sort(key=lambda x: -x["veces"])
    tiempo = collections.defaultdict(lambda: {"mensajes": 0, "correcciones": 0})
    for r in filas:
        a = area(r["texto"])
        tiempo[a]["mensajes"] += 1
        tiempo[a]["correcciones"] += bool(CORRECCION.search(r["texto"]))
    return correcciones, repetidos[:12], sorted(({"area": a, **v} for a, v in tiempo.items()), key=lambda x: -x["mensajes"])


def informe(dias, filas, correcciones, repetidos, tiempo):
    total = sum(c["total"] for c in correcciones)
    L = [f"# Mejora semanal: {time.strftime('%d-%m-%Y %H:%M')}",
         f"Últimos {dias:g} días: {len(filas)} mensajes de {USUARIO}, {total} correcciones.", "",
         "## 1. Correcciones por área (REPETIDA = el fallo volvió: falta o falla una regla)"]
    for c in correcciones:
        L.append(f"### {c['area']}: {c['total']} correcciones, {c['repetidas']} repetidas")
        L += [f"- {q}" for q in c["citas"][:12]]
    L += ["", "## 2. Encargos repetidos (3 o más veces) = posibles skills"]
    L += [f"- «{r['encargo']}»: {r['veces']} veces en {r['sesiones']} conversaciones. Skill cercana: "
          f"{r['skill_cercana'] or 'NINGUNA'}. Ej.: {r['ejemplo']}" for r in repetidos] or ["- ninguno"]
    L += ["", "## 3. Mensajes por área"]
    L += [f"- {t['area']}: {t['mensajes']} mensajes, {t['correcciones']} correcciones" for t in tiempo]
    L += ["", "## Qué hacer", f"El agente {REVISOR} agrupa las correcciones por significado, busca qué regla, skill o memoria debió",
          f"evitarlas (NO HAY REGLA / LA REGLA NO FUNCIONA / LA REGLA ESTÁ MAL) y propone a {USUARIO} el cambio más pequeño."]
    return "\n".join(L) + "\n"


def telegram(texto):
    env = dict(l.split("=", 1) for l in TELEGRAM.read_text().split() if "=" in l)
    subprocess.run(["curl", "-s", "-m", "30", f"https://api.telegram.org/bot{env['TOKEN']}/sendMessage",
                    "--data-urlencode", f"chat_id={env['CHAT_ID']}", "--data-urlencode", f"text={texto}"],
                   capture_output=True)


def apuntar(tarea, notas):
    s = PENDIENTES.read_text()
    if tarea not in s:
        PENDIENTES.write_text(s.rstrip("\n") + f"\n| {tarea} | pendiente ({time.strftime('%d-%m')}) | {REVISOR} | {notas} |\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=float, default=7)
    ap.add_argument("--sin-avisos", action="store_true", help="solo escribe el informe")
    a = ap.parse_args()
    filas = cargar(a.dias)
    correcciones, repetidos, tiempo = analizar(filas)
    INFORMES.mkdir(exist_ok=True)
    fecha = time.strftime("%Y-%m-%d")
    md = INFORMES / f"{fecha}.md"
    md.write_text(informe(a.dias, filas, correcciones, repetidos, tiempo))
    (INFORMES / f"{fecha}.json").write_text(json.dumps({"correcciones": correcciones, "repetidos": repetidos,
                                                        "areas": tiempo}, ensure_ascii=False, indent=1))
    print(md)
    if a.sin_avisos:
        return
    total = sum(c["total"] for c in correcciones)
    rep = sum(c["repetidas"] for c in correcciones)
    lineas = [f"🔧 Mejora semanal de los agentes · {time.strftime('%d-%m')}",
              f"{len(filas)} mensajes tuyos, {total} correcciones ({rep} repetidas)."]
    lineas += [f"• {c['area']}: {c['total']} ({c['repetidas']} repetidas)" for c in correcciones[:5]]
    lineas.append(f"El agente {REVISOR} lo revisa y te propone los cambios.")
    apuntar(f"Mejora semanal {time.strftime('%d-%m')}: revisar el informe y proponer cambios",
            f"`mejora/informes/{fecha}.md` (mejora.py). Proponer a {USUARIO}, no cambiar sin su sí")
    if datetime.date.today().day <= 7:
        apuntar(f"Revisión mensual {time.strftime('%m-%Y')} de skills, memoria y CLAUDE.md",
                "Repasar ~/.claude/skills, memoria y CLAUDE.md: qué está desfasado o repetido. Proponer, no borrar")
        lineas.append("Toca también la revisión mensual de skills, memoria y CLAUDE.md.")
    telegram("\n".join(lineas))


if __name__ == "__main__":
    main()
