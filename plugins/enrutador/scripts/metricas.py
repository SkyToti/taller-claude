#!/usr/bin/env python3
"""Hook SubagentStop (sin matcher: todos los subagentes, también los integrados).

Lee la transcripción del subagente (agent_transcript_path, JSONL) y anota en
${CLAUDE_PLUGIN_DATA}/metricas.jsonl los tokens REALES que gastó: entrada, escritura y lectura de
caché, salida, turnos, llamadas a herramientas, modelo, duración y un costo equivalente con la tabla
de precios.json. Corre al TERMINAR el agente, así que también sirve para los que van en segundo plano
(bitacora.sh corre al lanzarlos y ahí los tokens aún no existen).

Un mismo agent_id puede parar varias veces (se le reanuda o un hook lo bloquea): cada parada deja una
línea con los totales ACUMULADOS de toda la transcripción y el campo «parada» (1, 2, 3…); quien lea se
queda con la última. Nunca imprime nada ni bloquea; ante cualquier error sale con 0.
"""

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

CAMPOS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


def cargar_precios():
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precios.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            tabla = json.load(f)
        return {k: v for k, v in tabla.items() if not k.startswith("_") and isinstance(v, dict)}
    except Exception:
        return {}


def precio_de(modelo, tabla):
    if not modelo:
        return None
    if modelo in tabla:
        return tabla[modelo]
    prefijos = [k for k in tabla if modelo.startswith(k)]
    return tabla[max(prefijos, key=len)] if prefijos else None


def leer_fecha(texto):
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except Exception:
        return None


def resumir(ruta, tabla):
    usos = {}            # message.id -> (modelo, usage) de la última línea con ese id
    orden = []
    herramientas = set()
    sin_id = 0
    fechas = []
    informe_handback = ""
    with open(ruta, encoding="utf-8", errors="replace") as f:
        for linea in f:
            try:
                d = json.loads(linea)
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            t = leer_fecha(d.get("timestamp")) if d.get("timestamp") else None
            if t is not None:
                fechas.append(t)
            if d.get("type") != "assistant" or not isinstance(d.get("message"), dict):
                continue
            m = d["message"]
            mid = m.get("id")
            if mid:
                if mid not in usos:
                    orden.append(mid)
                usos[mid] = (m.get("model"), m.get("usage") if isinstance(m.get("usage"), dict) else {})
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    if b.get("id"):
                        herramientas.add(b["id"])
                    else:
                        sin_id += 1
                    if b.get("name") == "SubagentHandback" and isinstance(b.get("input"), dict):
                        informe_handback = str(b["input"].get("message") or "")

    totales = dict.fromkeys(CAMPOS, 0)
    modelos = Counter()
    costo = 0.0
    sin_precio = False
    for mid in orden:
        modelo, uso = usos[mid]
        if modelo and not str(modelo).startswith("<"):
            modelos[modelo] += 1
        n = {c: int(uso.get(c) or 0) for c in CAMPOS}
        for c in CAMPOS:
            totales[c] += n[c]
        if not any(n.values()):
            continue
        p = precio_de(modelo, tabla)
        if p is None:
            sin_precio = True
            continue
        costo += (n["input_tokens"] * p.get("entrada", 0) + n["output_tokens"] * p.get("salida", 0)
                  + n["cache_read_input_tokens"] * p.get("cache_lectura", 0)
                  + n["cache_creation_input_tokens"] * p.get("cache_escritura", 0)) / 1e6
    duracion = round((max(fechas) - min(fechas)).total_seconds(), 1) if len(fechas) >= 2 else 0
    return {
        "modelo": modelos.most_common(1)[0][0] if modelos else None,
        "turnos": len(orden),
        "herramientas": len(herramientas) + sin_id,
        "tokens_entrada": totales["input_tokens"],
        "tokens_cache_escritura": totales["cache_creation_input_tokens"],
        "tokens_cache_lectura": totales["cache_read_input_tokens"],
        "tokens_salida": totales["output_tokens"],
        "duracion_s": duracion,
        "costo_equiv_usd": None if (sin_precio or not modelos) else round(costo, 6),
    }, informe_handback


def contar_paradas(archivo, agente):
    n = 0
    try:
        with open(archivo, encoding="utf-8") as f:
            for linea in f:
                if agente in linea:
                    try:
                        if json.loads(linea).get("agent_id") == agente:
                            n += 1
                    except Exception:
                        pass
    except FileNotFoundError:
        pass
    return n


def principal():
    datos = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not datos:
        return
    entrada = json.loads(sys.stdin.read())
    if not isinstance(entrada, dict):
        return
    agente = entrada.get("agent_id")
    ruta = entrada.get("agent_transcript_path")
    if not agente or not isinstance(ruta, str) or not ruta:
        return
    ruta = os.path.expanduser(ruta)
    if not os.path.isfile(ruta):
        return
    agente = str(agente)
    resumen, informe_handback = resumir(ruta, cargar_precios())
    informe = entrada.get("last_assistant_message")
    informe = informe if isinstance(informe, str) and informe.strip() else informe_handback
    m = re.search(r"^[ \t]*ESTADO:[ \t]*([^\s|]+)", informe or "", re.M)

    os.makedirs(datos, exist_ok=True)
    archivo = os.path.join(datos, "metricas.jsonl")
    linea = {
        "fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sesion": entrada.get("session_id"),
        "agent_id": agente,
        "agente": entrada.get("agent_type"),
        **resumen,
        "estado": m.group(1).lower() if m else None,
        "parada": contar_paradas(archivo, agente) + 1,
    }
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        principal()
    except BaseException:
        pass
    sys.exit(0)
