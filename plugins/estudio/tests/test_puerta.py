"""Pruebas de scripts/puerta.py con entradas sintéticas (sin Minecraft ni tokens).

Se corren con: python3 -m unittest discover -s plugins/estudio/tests
Cada prueba arma en un directorio temporal un repo git mínimo con su worktree en
<tmp>/repo/.claude/worktrees/<nombre> y un build.sh / probar.sh de mentira cuyo código de salida,
salida y número de ejecuciones se controlan con archivos en <tmp>/ctrl (fuera del repo).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PUERTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "puerta.py")

FALSO = """#!/bin/sh
# Orden de mentira: cuenta sus ejecuciones, imprime la salida pedida y sale con el código pedido.
n=$(cat "$ESTUDIO_CTRL/{0}.cuenta" 2>/dev/null || echo 0)
echo $((n + 1)) > "$ESTUDIO_CTRL/{0}.cuenta"
cat "$ESTUDIO_CTRL/{0}.salida" 2>/dev/null
exit $(cat "$ESTUDIO_CTRL/{0}.rc" 2>/dev/null || echo 0)
"""


def git(cwd, *args):
    subprocess.run(["git", "-C", cwd] + list(args), check=True, capture_output=True)


class PruebaPuerta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="puerta-")
        self.ctrl = os.path.join(self.tmp, "ctrl")
        self.datos = os.path.join(self.tmp, "datos")
        self.tmpdir = os.path.join(self.tmp, "estado")
        for d in (self.ctrl, self.datos, self.tmpdir):
            os.makedirs(d)
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q", "-b", "master")
        git(self.repo, "config", "user.email", "prueba@ejemplo.invalid")
        git(self.repo, "config", "user.name", "Prueba")
        for orden in ("build", "probar"):
            ruta = os.path.join(self.repo, orden + ".sh")
            with open(ruta, "w") as f:
                f.write(FALSO.format(orden))
            os.chmod(ruta, 0o755)
        with open(os.path.join(self.repo, "LEEME"), "w") as f:
            f.write("base\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "base")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- ayudantes ---------------------------------------------------------------------------
    def worktree(self, nombre="t1", toca_src=False):
        wt = os.path.join(self.repo, ".claude", "worktrees", nombre)
        git(self.repo, "worktree", "add", "-q", wt, "-b", nombre)
        if toca_src:
            os.makedirs(os.path.join(wt, "src"))
            with open(os.path.join(wt, "src", "A.java"), "w") as f:
                f.write("class A {}\n")
            git(wt, "add", ".")
            git(wt, "commit", "-q", "-m", "toca src")
        return wt

    def fijar(self, orden, rc=0, salida=""):
        with open(os.path.join(self.ctrl, orden + ".rc"), "w") as f:
            f.write(str(rc))
        with open(os.path.join(self.ctrl, orden + ".salida"), "w") as f:
            f.write(salida)

    def cuenta(self, orden):
        try:
            with open(os.path.join(self.ctrl, orden + ".cuenta")) as f:
                return int(f.read().strip())
        except FileNotFoundError:
            return 0

    def informe(self, wt, estado="hecho"):
        git_linea = "GIT: rama t1 · worktree %s · commit abc1234" % wt if wt else "GIT: n/a"
        return "\n".join(["ESTADO: " + estado, "RESUMEN: algo", "RUTAS:", "- /x (modificado) — y",
                          git_linea, "PRUEBAS: ./build.sh → OK", "NO VERIFICADO: nada",
                          "SIGUIENTE: unir"])

    def entrada(self, informe, evento="PreToolUse", tipo="estudio:programador-mod", agente="a1"):
        if evento == "PreToolUse":
            return {"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "SubagentHandback",
                    "tool_input": {"message": informe}, "agent_id": agente, "agent_type": tipo}
        return {"session_id": "s", "hook_event_name": "SubagentStop", "stop_hook_active": False,
                "agent_id": agente, "agent_type": tipo, "last_assistant_message": informe}

    def correr(self, datos):
        crudo = datos if isinstance(datos, str) else json.dumps(datos)
        env = dict(os.environ, ESTUDIO_CTRL=self.ctrl, TMPDIR=self.tmpdir, CLAUDE_PLUGIN_DATA=self.datos)
        r = subprocess.run([sys.executable, PUERTA], input=crudo, capture_output=True, text=True,
                           env=env, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def bitacora(self):
        try:
            with open(os.path.join(self.datos, "puerta.jsonl")) as f:
                return [json.loads(l) for l in f if l.strip()]
        except FileNotFoundError:
            return []

    def motivo(self, salida):
        if "hookSpecificOutput" in salida:
            return salida["hookSpecificOutput"]["permissionDecisionReason"]
        return salida["reason"]

    # --- casos -------------------------------------------------------------------------------
    def test_agente_ajeno_silencio(self):
        wt = self.worktree()
        self.fijar("build", rc=1)
        self.assertIsNone(self.correr(self.entrada(self.informe(wt), tipo="enrutador:programador")))
        self.assertIsNone(self.correr(self.entrada(self.informe(wt), evento="SubagentStop",
                                                   tipo="enrutador:programador")))
        self.assertEqual(self.cuenta("build"), 0)
        self.assertEqual(self.bitacora(), [])

    def test_otra_herramienta_silencio(self):
        e = self.entrada(self.informe(self.worktree()))
        e["tool_name"] = "Bash"
        self.assertIsNone(self.correr(e))
        self.assertEqual(self.cuenta("build"), 0)

    def test_bloqueado_pasa(self):
        self.fijar("build", rc=1)
        self.assertIsNone(self.correr(self.entrada(self.informe("", estado="bloqueado"))))
        self.assertEqual(self.cuenta("build"), 0)
        self.assertEqual(self.bitacora()[-1]["resultado"], "omitida")

    def test_sin_worktree_niega(self):
        salida = self.correr(self.entrada(self.informe("")))
        self.assertEqual(salida["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("worktree", self.motivo(salida))
        self.assertEqual(self.bitacora()[-1]["resultado"], "negado")

    def test_build_falla_niega_con_salida(self):
        wt = self.worktree()
        self.fijar("build", rc=1, salida="FALLO rc=1 · registro: /tmp/x.log\nA.java:3: error: falta ;\n")
        salida = self.correr(self.entrada(self.informe(wt)))
        motivo = self.motivo(salida)
        self.assertTrue(motivo.startswith("No compila. Arregla esto y vuelve a entregar:"))
        self.assertIn("A.java:3: error: falta ;", motivo)
        reg = self.bitacora()[-1]
        self.assertEqual((reg["resultado"], reg["build_rc"]), ("negado", 1))

    def test_salida_larga_se_recorta(self):
        wt = self.worktree()
        self.fijar("build", rc=1, salida="".join("linea %d\n" % i for i in range(100)))
        motivo = self.motivo(self.correr(self.entrada(self.informe(wt))))
        self.assertIn("linea 34", motivo)
        self.assertNotIn("linea 35\n", motivo)
        self.assertIn("65 líneas más", motivo)

    def test_build_pasa(self):
        wt = self.worktree()
        self.fijar("build", rc=0, salida="OK 12 s · warnings=0\n")
        self.assertIsNone(self.correr(self.entrada(self.informe(wt))))
        reg = self.bitacora()[-1]
        self.assertEqual((reg["resultado"], reg["build_rc"], reg["worktree"]), ("paso", 0, wt))
        self.assertEqual(self.cuenta("probar"), 0)  # el diff no toca src/

    def test_probar_falla_niega(self):
        wt = self.worktree(toca_src=True)
        self.fijar("build", rc=0)
        self.fijar("probar", rc=1, salida="FALLO prueba_jefe: esperaba 300, salió 250\n")
        salida = self.correr(self.entrada(self.informe(wt), evento="SubagentStop"))
        self.assertEqual(salida["decision"], "block")
        self.assertIn("esperaba 300", salida["reason"])
        self.assertEqual(self.cuenta("probar"), 1)
        self.assertEqual(self.bitacora()[-1]["probar_rc"], 1)

    def test_probar_pasa(self):
        wt = self.worktree(toca_src=True)
        self.fijar("build", rc=0)
        self.fijar("probar", rc=0, salida="OK 4 pruebas · 30 s\n")
        self.assertIsNone(self.correr(self.entrada(self.informe(wt))))
        self.assertEqual(self.cuenta("probar"), 1)

    def test_candado_no_cuenta(self):
        wt = self.worktree()
        self.fijar("build", rc=75)
        for _ in range(5):
            salida = self.correr(self.entrada(self.informe(wt)))
            self.assertIn("candado", self.motivo(salida))
        self.fijar("build", rc=1)
        salida = self.correr(self.entrada(self.informe(wt)))  # sigue negando: el candado no gastó el tope
        self.assertIn("rechazo 1 de 3", self.motivo(salida))

    def test_tope_tres_rechazos_y_agotada(self):
        wt = self.worktree()
        self.fijar("build", rc=1, salida="error\n")
        for i in range(3):
            salida = self.correr(self.entrada(self.informe(wt)))
            self.assertIn("rechazo %d de 3" % (i + 1), self.motivo(salida))
        self.assertIsNone(self.correr(self.entrada(self.informe(wt))))
        reg = self.bitacora()[-1]
        self.assertEqual((reg["resultado"], reg["puerta"]), ("agotada", "agotada"))
        self.assertEqual(self.cuenta("build"), 3)
        # otro agente tiene su propio tope
        self.assertIsNotNone(self.correr(self.entrada(self.informe(wt), agente="a2")))

    def test_cache_diez_minutos(self):
        wt = self.worktree(toca_src=True)
        self.fijar("build", rc=0)
        self.fijar("probar", rc=0)
        self.assertIsNone(self.correr(self.entrada(self.informe(wt))))
        self.assertIsNone(self.correr(self.entrada(self.informe(wt), evento="SubagentStop")))
        self.assertEqual((self.cuenta("build"), self.cuenta("probar")), (1, 1))
        self.assertTrue(self.bitacora()[-1].get("cache"))
        # un cambio sin commit invalida la caché
        with open(os.path.join(wt, "src", "A.java"), "a") as f:
            f.write("// cambio\n")
        self.correr(self.entrada(self.informe(wt)))
        self.assertEqual(self.cuenta("build"), 2)

    def test_ruta_fuera_de_worktrees_no_ejecuta(self):
        otro = os.path.join(self.tmp, "otro", "t1")
        os.makedirs(otro)
        open(os.path.join(otro, ".git"), "w").close()
        shutil.copy(os.path.join(self.repo, "build.sh"), os.path.join(otro, "build.sh"))
        self.fijar("build", rc=1)
        self.assertIsNone(self.correr(self.entrada(self.informe(otro))))
        self.assertEqual(self.cuenta("build"), 0)
        self.assertEqual(self.bitacora()[-1]["resultado"], "omitida")

    def test_worktree_falso_sin_git_real(self):
        # .git de mentira: no hay HEAD ni diff, pero build.sh sí se corre.
        wt = os.path.join(self.tmp, "falso", ".claude", "worktrees", "t1")
        os.makedirs(wt)
        with open(os.path.join(wt, ".git"), "w") as f:
            f.write("gitdir: /no/existe\n")
        shutil.copy(os.path.join(self.repo, "build.sh"), os.path.join(wt, "build.sh"))
        self.fijar("build", rc=1, salida="roto\n")
        self.assertIn("roto", self.motivo(self.correr(self.entrada(self.informe(wt)))))
        self.assertEqual(self.cuenta("build"), 1)

    def test_forma_json_por_evento(self):
        wt = self.worktree()
        self.fijar("build", rc=1)
        pre = self.correr(self.entrada(self.informe(wt)))
        self.assertEqual(set(pre), {"hookSpecificOutput"})
        self.assertEqual(pre["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertEqual(pre["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIsInstance(pre["hookSpecificOutput"]["permissionDecisionReason"], str)
        stop = self.correr(self.entrada(self.informe(wt), evento="SubagentStop"))
        self.assertEqual(set(stop), {"decision", "reason"})
        self.assertEqual(stop["decision"], "block")

    def test_entrada_basura(self):
        for basura in ("", "no es json", "[1, 2]", "null", '{"agent_type": 3}',
                       json.dumps({"agent_type": "estudio:probador", "agent_id": "a1",
                                   "tool_name": "SubagentHandback", "tool_input": "texto"})):
            self.assertIsNone(self.correr(basura))
        self.assertEqual(self.cuenta("build"), 0)

    def test_sin_datos_no_registra(self):
        wt = self.worktree()
        env = dict(os.environ, ESTUDIO_CTRL=self.ctrl, TMPDIR=self.tmpdir)
        env.pop("CLAUDE_PLUGIN_DATA", None)
        r = subprocess.run([sys.executable, PUERTA], input=json.dumps(self.entrada(self.informe(wt))),
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual(self.bitacora(), [])


if __name__ == "__main__":
    unittest.main()
