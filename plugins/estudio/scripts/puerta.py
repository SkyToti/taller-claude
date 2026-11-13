#!/usr/bin/env python3
"""Compuerta de compilación del plugin estudio.

Hook en dos eventos (como el contrato de enrutador):
  - SubagentStop (matcher ^estudio:(programador-mod|probador)$): el informe es last_assistant_message.
  - PreToolUse (matcher SubagentHandback): el informe es tool_input.message; aquí se filtra agent_type.

Antes de dejar entregar a un agente de estudio, corre ./build.sh (y ./probar.sh si el diff toca src/)
en el worktree que el agente puso en su línea GIT:. Si falla, niega la entrega con la salida para que
lo arregle. Tope: 3 rechazos por agent_id; al cuarto intento deja pasar («agotada»). El código 75
(candado de compilación ocupado) niega sin contar. Si ya aprobó el mismo worktree con el mismo HEAD y
sin cambios sin commit en los últimos 10 min, deja pasar sin correr nada.

Nunca rompe la sesión: ante cualquier error sale con 0 sin imprimir. Stdout solo lleva el JSON de negar.
Bitácora: ${CLAUDE_PLUGIN_DATA}/puerta.jsonl (una línea por decisión).
"""

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime

AGENTES = {"estudio:programador-mod", "estudio:probador"}
TOPE_RECHAZOS = 3
TIEMPO_TOTAL = 480          # segundos para build.sh + probar.sh
VIGENCIA_CACHE = 600        # 10 min
VIGENCIA_ESTADO = 24 * 3600
LINEAS_SALIDA = 35
CODIGO_CANDADO = 75


def dir_estado():
    try:
        uid = str(os.getuid())
    except Exception:
        uid = "x"
    return os.path.join(os.environ.get("TMPDIR") or "/tmp", "estudio-puerta-" + uid)


def limpiar_estado(d):
    ahora = time.time()
    try:
        for nombre in os.listdir(d):
            ruta = os.path.join(d, nombre)
            try:
                if ahora - os.path.getmtime(ruta) > VIGENCIA_ESTADO:
                    os.remove(ruta)
            except OSError:
                pass
    except OSError:
        pass


def anotar(registro):
    datos = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not datos:
        return
    try:
        os.makedirs(datos, exist_ok=True)
        registro = dict({"fecha": datetime.now().astimezone().isoformat(timespec="seconds")}, **registro)
        with open(os.path.join(datos, "puerta.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception:
        pass


def negar(evento, motivo):
    if evento == "PreToolUse":
        salida = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                         "permissionDecision": "deny",
                                         "permissionDecisionReason": motivo}}
    else:
        salida = {"decision": "block", "reason": motivo}
    sys.stdout.write(json.dumps(salida, ensure_ascii=False))
    sys.stdout.flush()


def estado_del_informe(informe):
    m = re.search(r"^[ \t]*ESTADO:[ \t]*([^\s|]+)", informe, re.M)
    return m.group(1).strip().lower() if m else ""


def worktree_del_informe(informe):
    for linea in informe.splitlines():
        if re.match(r"^[ \t]*GIT:", linea):
            m = re.search(r"worktree[ \t]+`?([~/][^\s`·|]*)", linea)
            if m:
                ruta = os.path.expanduser(m.group(1).rstrip(".,;:"))
                return ruta.rstrip("/") or "/"
    return ""


def git(wt, *args):
    try:
        r = subprocess.run(["git", "-C", wt] + list(args), capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


def correr(wt, orden, limite):
    """Corre ./orden en wt con stdout+stderr juntos. Devuelve (rc, salida); rc None = se agotó el tiempo."""
    try:
        p = subprocess.Popen(["./" + orden], cwd=wt, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, start_new_session=True)
    except Exception as e:
        return 1, "no se pudo ejecutar ./%s: %s" % (orden, e)
    try:
        salida, _ = p.communicate(timeout=max(1, limite))
        return p.returncode, salida.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGTERM)
            time.sleep(2)
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            pass
        try:
            p.communicate(timeout=5)
        except Exception:
            pass
        return None, "./%s no terminó en %d s y se detuvo." % (orden, limite)


def recortar(texto):
    lineas = texto.rstrip().splitlines()
    if len(lineas) <= LINEAS_SALIDA:
        return "\n".join(lineas)
    return "\n".join(lineas[:LINEAS_SALIDA] + ["… (%d líneas más)" % (len(lineas) - LINEAS_SALIDA)])


def leer_int(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0


def escribir(ruta, texto):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
    except Exception:
        pass


def toca_src(wt):
    base = ""
    for rama in ("master", "main"):
        if git(wt, "rev-parse", "--verify", "--quiet", rama)[0] == 0:
            base = rama
            break
    if not base:
        return True  # sin base no se puede saber: mejor probar
    rc, nombres = git(wt, "diff", "--name-only", base + "...HEAD")
    if rc != 0:
        return True
    rc2, porcelana = git(wt, "status", "--porcelain")
    rutas = nombres.splitlines() + [l[3:] for l in porcelana.splitlines()]
    return any(r.strip().strip('"').startswith("src/") for r in rutas)


def principal():
    crudo = sys.stdin.read()
    entrada = json.loads(crudo)
    if not isinstance(entrada, dict):
        return
    tipo = entrada.get("agent_type") or ""
    agente = re.sub(r"[^A-Za-z0-9_-]", "", str(entrada.get("agent_id") or ""))
    if tipo not in AGENTES or not agente:
        return

    if entrada.get("tool_name") is not None or entrada.get("hook_event_name") == "PreToolUse":
        if entrada.get("tool_name") != "SubagentHandback":
            return
        evento = "PreToolUse"
        informe = (entrada.get("tool_input") or {}).get("message") or ""
    else:
        evento = "SubagentStop"
        informe = entrada.get("last_assistant_message") or ""
    if not isinstance(informe, str) or not informe.strip():
        return

    base_reg = {"agent_id": agente, "agent_type": tipo, "evento": evento}
    reintento = (" Vuelve a llamar a SubagentHandback con el informe cuando esté listo."
                 if evento == "PreToolUse" else "")

    if estado_del_informe(informe) == "bloqueado":
        anotar(dict(base_reg, worktree=None, resultado="omitida", motivo="bloqueado",
                    build_rc=None, probar_rc=None, segundos=0))
        return

    d = dir_estado()
    os.makedirs(d, exist_ok=True)
    limpiar_estado(d)
    marca_rechazos = os.path.join(d, "rechazos-" + agente)
    rechazos = leer_int(marca_rechazos)

    wt = worktree_del_informe(informe)
    if rechazos >= TOPE_RECHAZOS:
        anotar(dict(base_reg, worktree=wt or None, resultado="agotada", puerta="agotada",
                    build_rc=None, probar_rc=None, segundos=0))
        return

    def rechazar(razon, **extra):
        escribir(marca_rechazos, str(rechazos + 1))
        negar(evento, "%s (rechazo %d de %d)%s" % (razon, rechazos + 1, TOPE_RECHAZOS, reintento))
        anotar(dict(base_reg, worktree=wt or None, resultado="negado", **extra))

    if not wt:
        rechazar("Tu línea GIT: no trae la ruta del worktree. Escríbela como «GIT: rama <x> · worktree "
                 "<ruta absoluta> · commit <sha7>» (la compuerta compila ahí antes de dejarte entregar).",
                 motivo="sin_worktree", build_rc=None, probar_rc=None, segundos=0)
        return

    real = os.path.realpath(wt)
    valido = (os.path.isdir(real) and "/.claude/worktrees/" in real + "/"
              and "/.claude/worktrees/" in wt + "/"
              and os.path.isfile(os.path.join(real, ".git"))
              and os.access(os.path.join(real, "build.sh"), os.X_OK))
    if not valido:
        anotar(dict(base_reg, worktree=wt, resultado="omitida", motivo="no_es_worktree_con_build",
                    build_rc=None, probar_rc=None, segundos=0))
        return

    # Caché: mismo worktree, mismo HEAD y sin cambios sin commit, aprobado hace < 10 min.
    rc_head, head = git(real, "rev-parse", "HEAD")
    head = head.strip() if rc_head == 0 else ""
    rc_st, porcelana = git(real, "status", "--porcelain")
    limpio = rc_st == 0 and not porcelana.strip()
    marca_ok = os.path.join(d, "aprobado-" + hashlib.sha1(real.encode()).hexdigest()[:16])
    if head and limpio:
        try:
            with open(marca_ok, encoding="utf-8") as f:
                previo = json.load(f)
            if previo.get("head") == head and time.time() - float(previo.get("t", 0)) < VIGENCIA_CACHE:
                anotar(dict(base_reg, worktree=real, resultado="paso", cache=True,
                            build_rc=None, probar_rc=None, segundos=0))
                return
        except Exception:
            pass

    inicio = time.monotonic()
    build_rc, salida = correr(real, "build.sh", TIEMPO_TOTAL)
    probar_rc = None

    def segundos():
        return round(time.monotonic() - inicio, 1)

    if build_rc == CODIGO_CANDADO:
        negar(evento, "El candado de compilación está ocupado (otra sesión compila); espera y vuelve a "
                      "entregar. Esto no cuenta como rechazo." + reintento)
        anotar(dict(base_reg, worktree=real, resultado="negado", motivo="candado",
                    build_rc=build_rc, probar_rc=None, segundos=segundos()))
        return
    if build_rc != 0:
        rechazar("No compila. Arregla esto y vuelve a entregar:\n" + recortar(salida),
                 motivo="build", build_rc=build_rc, probar_rc=None, segundos=segundos())
        return

    probar = os.path.join(real, "probar.sh")
    if os.path.isfile(probar) and os.access(probar, os.X_OK) and toca_src(real):
        restante = int(TIEMPO_TOTAL - (time.monotonic() - inicio))
        probar_rc, salida = correr(real, "probar.sh", restante)
        if probar_rc == CODIGO_CANDADO:
            negar(evento, "El candado de compilación está ocupado (otra sesión compila); espera y vuelve "
                          "a entregar. Esto no cuenta como rechazo." + reintento)
            anotar(dict(base_reg, worktree=real, resultado="negado", motivo="candado",
                        build_rc=build_rc, probar_rc=probar_rc, segundos=segundos()))
            return
        if probar_rc != 0:
            rechazar("Compila, pero las pruebas no pasan (./probar.sh). Arregla esto y vuelve a entregar:\n"
                     + recortar(salida),
                     motivo="probar", build_rc=build_rc, probar_rc=probar_rc, segundos=segundos())
            return

    if head:
        rc_st, porcelana = git(real, "status", "--porcelain")
        if rc_st == 0 and not porcelana.strip():
            escribir(marca_ok, json.dumps({"head": head, "t": time.time()}))
    anotar(dict(base_reg, worktree=real, resultado="paso", build_rc=build_rc, probar_rc=probar_rc,
                segundos=segundos()))


if __name__ == "__main__":
    try:
        principal()
    except BaseException:
        pass
    sys.exit(0)
