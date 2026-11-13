#!/usr/bin/env python3
"""Resumen de metricas.jsonl: python3 resumen-metricas.py [--sesion <id>] [--dias N] [--csv] [--datos <dir>…]

Lee ~/.claude/plugins/data/*/metricas.jsonl (o --datos), toma la última parada de cada agent_id y
muestra una tabla por agente y modelo con el total al final; --csv saca una fila por corrida.
El costo es un equivalente a precios de lista para comparar tareas; no es un cobro.
"""

import argparse
import csv
import glob
import json
import os
import sys
from datetime import datetime, timedelta

COLUMNAS = ["fecha", "sesion", "agent_id", "agente", "modelo", "turnos", "herramientas", "tokens_entrada",
            "tokens_cache_escritura", "tokens_cache_lectura", "tokens_salida", "duracion_s",
            "costo_equiv_usd", "estado", "parada"]


def leer(carpetas):
    ultimas = {}
    for carpeta in carpetas:
        for archivo in sorted(glob.glob(os.path.join(os.path.expanduser(carpeta), "metricas.jsonl"))):
            with open(archivo, encoding="utf-8", errors="replace") as f:
                for linea in f:
                    try:
                        d = json.loads(linea)
                    except Exception:
                        continue
                    if not isinstance(d, dict) or not d.get("agent_id"):
                        continue
                    previa = ultimas.get(d["agent_id"])
                    if previa is None or (d.get("parada") or 0) >= (previa.get("parada") or 0):
                        ultimas[d["agent_id"]] = d
    return list(ultimas.values())


def fecha_de(d):
    try:
        f = datetime.fromisoformat(str(d.get("fecha")))
        return f if f.tzinfo else f.astimezone()
    except Exception:
        return None


def tok(n):
    n = float(n or 0)
    for limite, sufijo in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
        if n >= limite:
            return "%.1f%s" % (n / limite, sufijo)
    return "%d" % n


def num(d, campo):
    v = d.get(campo)
    return v if isinstance(v, (int, float)) else 0


def tabla(corridas):
    grupos = {}
    for d in corridas:
        grupos.setdefault((d.get("agente") or "?", d.get("modelo") or "?"), []).append(d)
    filas = []
    def fila(nombre, modelo, ds):
        costos = [d.get("costo_equiv_usd") for d in ds]
        conocidos = [c for c in costos if isinstance(c, (int, float))]
        costo = ("$%.2f" % sum(conocidos) + ("*" if len(conocidos) < len(costos) else "")) if conocidos else "—"
        return [nombre, modelo, str(len(ds)), "%.1f" % (sum(num(d, "turnos") for d in ds) / max(1, len(ds))),
                tok(sum(num(d, "tokens_entrada") + num(d, "tokens_cache_escritura") for d in ds)),
                tok(sum(num(d, "tokens_cache_lectura") for d in ds)),
                tok(sum(num(d, "tokens_salida") for d in ds)),
                "%.1f" % (sum(num(d, "duracion_s") for d in ds) / 60), costo]
    for (agente, modelo), ds in sorted(grupos.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        filas.append(fila(agente, modelo, ds))
    filas.append(fila("TOTAL", "", corridas))
    cabecera = ["agente", "modelo", "corridas", "turnos", "entrada nueva", "caché leída", "salida",
                "min", "costo equiv"]
    anchos = [max(len(str(x)) for x in col) for col in zip(cabecera, *filas)]
    def imprimir(cols):
        print("  ".join(c.ljust(a) if i < 2 else c.rjust(a) for i, (c, a) in enumerate(zip(cols, anchos))))
    imprimir(cabecera)
    imprimir(["-" * a for a in anchos])
    for i, f in enumerate(filas):
        if i == len(filas) - 1:
            imprimir(["-" * a for a in anchos])
        imprimir(f)
    print("\nentrada nueva = entrada + escritura de caché · costo equivalente a precios de lista, no es un "
          "cobro" + (" · * = hay corridas con modelo sin precio" if any("*" in f[-1] for f in filas) else ""))


def main(argv=None):
    p = argparse.ArgumentParser(description="Resumen de tokens y costo equivalente por agente y modelo.")
    p.add_argument("--sesion", help="solo esta sesión (session_id)")
    p.add_argument("--dias", type=float, help="solo los últimos N días")
    p.add_argument("--csv", action="store_true", help="una fila por corrida en CSV")
    p.add_argument("--datos", nargs="+", help="carpetas con metricas.jsonl (por defecto, las de los plugins)")
    a = p.parse_args(argv)
    corridas = leer(a.datos or [os.path.join("~", ".claude", "plugins", "data", "*")])
    if a.sesion:
        corridas = [d for d in corridas if d.get("sesion") == a.sesion]
    if a.dias is not None:
        desde = datetime.now().astimezone() - timedelta(days=a.dias)
        corridas = [d for d in corridas if (fecha_de(d) or desde) >= desde]
    corridas.sort(key=lambda d: str(d.get("fecha")))
    if a.csv:
        w = csv.DictWriter(sys.stdout, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(corridas)
        return 0
    if not corridas:
        print("sin corridas en metricas.jsonl")
        return 0
    tabla(corridas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
