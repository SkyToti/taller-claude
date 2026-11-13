"""Pruebas de scripts/metricas.py y scripts/resumen-metricas.py con transcripciones sintéticas.

Se corren con: python3 -m unittest discover -s plugins/enrutador/tests
"""

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
METRICAS = os.path.join(SCRIPTS, "metricas.py")
RESUMEN = os.path.join(SCRIPTS, "resumen-metricas.py")
with open(os.path.join(SCRIPTS, "precios.json"), encoding="utf-8") as f:
    PRECIOS = json.load(f)

OPUS, HAIKU = "claude-opus-5-5", "claude-haiku-5-5"


def asistente(mid, modelo, uso, bloque, ts):
    return {"type": "assistant", "timestamp": ts,
            "message": {"id": mid, "model": modelo, "role": "assistant", "content": [bloque],
                        "usage": dict(uso, service_tier="standard")}}


def uso(i, cw, cr, o):
    return {"input_tokens": i, "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr,
            "output_tokens": o}


def costo(modelo, u):
    p = PRECIOS[modelo]
    return (u["input_tokens"] * p["entrada"] + u["output_tokens"] * p["salida"]
            + u["cache_read_input_tokens"] * p["cache_lectura"]
            + u["cache_creation_input_tokens"] * p["cache_escritura"]) / 1e6


U1, U2, U3, U4 = uso(10, 1000, 0, 50), uso(5, 200, 1000, 20), uso(100, 0, 2000, 10), uso(1, 2, 3, 4)
TEXTO = {"type": "text", "text": "voy"}


def herramienta(tid, nombre="Bash", entrada=None):
    return {"type": "tool_use", "id": tid, "name": nombre, "input": entrada or {"command": "ls"}}


PRIMERA = [
    {"type": "user", "timestamp": "2026-11-13T10:00:00.000Z", "message": {"role": "user", "content": "x"}},
    asistente("msg_1", OPUS, U1, TEXTO, "2026-11-13T10:00:05.000Z"),
    asistente("msg_1", OPUS, U1, herramienta("tu_1"), "2026-11-13T10:00:06.000Z"),  # id repetido
    {"type": "user", "timestamp": "2026-11-13T10:01:00.000Z", "message": {"role": "user", "content": []}},
    asistente("msg_2", OPUS, U2, herramienta("tu_2"), "2026-11-13T10:02:00.000Z"),
    asistente("msg_2", OPUS, U2, herramienta("tu_2"), "2026-11-13T10:02:00.500Z"),  # bloque repetido
    asistente("msg_3", HAIKU, U3, herramienta("tu_3", "SubagentHandback",
                                              {"message": "ESTADO: parcial\nRESUMEN: x"}),
              "2026-11-13T10:04:00.000Z"),
    {"type": "attachment", "timestamp": "2026-11-13T10:05:30.000Z"},
]
SEGUNDA = [
    {"type": "user", "timestamp": "2026-11-13T11:00:00.000Z", "message": {"role": "user", "content": "otra"}},
    asistente("msg_4", OPUS, U4, herramienta("tu_4"), "2026-11-13T11:00:30.000Z"),
]


class PruebaMetricas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="metricas-")
        self.datos = os.path.join(self.tmp, "datos")
        self.trans = os.path.join(self.tmp, "agent-a1.jsonl")
        self.escribir(PRIMERA)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def escribir(self, lineas, modo="w"):
        with open(self.trans, modo) as f:
            for l in lineas:
                f.write(json.dumps(l) + "\n")
            f.write("{esto no es json\n")

    def correr(self, entrada=None, datos=True):
        if entrada is None:
            entrada = {"session_id": "s1", "hook_event_name": "SubagentStop", "agent_id": "a1",
                       "agent_type": "enrutador:programador", "agent_transcript_path": self.trans,
                       "last_assistant_message": ""}
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_DATA", None)
        if datos:
            env["CLAUDE_PLUGIN_DATA"] = self.datos
        crudo = entrada if isinstance(entrada, str) else json.dumps(entrada)
        r = subprocess.run([sys.executable, METRICAS], input=crudo, capture_output=True, text=True,
                           env=env, timeout=30)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def lineas(self):
        try:
            with open(os.path.join(self.datos, "metricas.jsonl")) as f:
                return [json.loads(l) for l in f]
        except FileNotFoundError:
            return []

    def test_sumas_y_costo(self):
        self.correr()
        (d,) = self.lineas()
        self.assertEqual(d["sesion"], "s1")
        self.assertEqual(d["agent_id"], "a1")
        self.assertEqual(d["agente"], "enrutador:programador")
        self.assertEqual(d["modelo"], OPUS)
        self.assertEqual(d["turnos"], 3)
        self.assertEqual(d["herramientas"], 3)
        self.assertEqual(d["tokens_entrada"], 115)
        self.assertEqual(d["tokens_cache_escritura"], 1200)
        self.assertEqual(d["tokens_cache_lectura"], 3000)
        self.assertEqual(d["tokens_salida"], 80)
        self.assertEqual(d["duracion_s"], 330)
        esperado = costo(OPUS, U1) + costo(OPUS, U2) + costo(HAIKU, U3)
        self.assertAlmostEqual(d["costo_equiv_usd"], esperado, places=6)
        self.assertEqual(d["estado"], "parcial")  # sale del SubagentHandback de la transcripción
        self.assertEqual(d["parada"], 1)

    def test_estado_de_last_assistant_message(self):
        self.correr({"session_id": "s1", "agent_id": "a1", "agent_type": "Explore",
                     "agent_transcript_path": self.trans, "last_assistant_message": "ESTADO: hecho\nRESUMEN: y"})
        self.assertEqual(self.lineas()[0]["estado"], "hecho")

    def test_segunda_parada_acumula(self):
        self.correr()
        self.escribir(SEGUNDA, modo="a")
        self.correr()
        primera, segunda = self.lineas()
        self.assertEqual((primera["parada"], segunda["parada"]), (1, 2))
        self.assertEqual(segunda["turnos"], 4)
        self.assertEqual(segunda["herramientas"], 4)
        self.assertEqual(segunda["tokens_entrada"], 116)
        self.assertEqual(segunda["tokens_cache_escritura"], 1202)
        self.assertEqual(segunda["tokens_cache_lectura"], 3003)
        self.assertEqual(segunda["tokens_salida"], 84)
        self.assertEqual(segunda["duracion_s"], 3630)
        esperado = costo(OPUS, U1) + costo(OPUS, U2) + costo(HAIKU, U3) + costo(OPUS, U4)
        self.assertAlmostEqual(segunda["costo_equiv_usd"], esperado, places=6)

    def test_modelo_sin_precio(self):
        self.escribir([asistente("msg_9", "claude-desconocido-1", U1, TEXTO, "2026-11-13T10:00:00Z")], "a")
        self.correr()
        self.assertIsNone(self.lineas()[0]["costo_equiv_usd"])

    def test_prefijo_de_modelo(self):
        self.escribir([asistente("m", OPUS + "-20261101", U1, TEXTO, "2026-11-13T10:00:00Z")])
        self.correr()
        self.assertAlmostEqual(self.lineas()[0]["costo_equiv_usd"], costo(OPUS, U1), places=6)

    def test_entrada_basura(self):
        for basura in ("", "no es json", "[1]", "null", json.dumps({"agent_id": "a1"}),
                       json.dumps({"agent_id": "a1", "agent_transcript_path": "/no/existe.jsonl"}),
                       json.dumps({"agent_id": "a1", "agent_transcript_path": 7})):
            self.correr(basura)
        self.assertEqual(self.lineas(), [])

    def test_sin_carpeta_de_datos(self):
        self.correr(datos=False)
        self.assertFalse(os.path.exists(self.datos))

    def test_resumen_toma_la_ultima_parada(self):
        self.correr()
        self.escribir(SEGUNDA, modo="a")
        self.correr()
        r = subprocess.run([sys.executable, RESUMEN, "--csv", "--datos", self.datos],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        filas = list(csv.DictReader(io.StringIO(r.stdout)))
        self.assertEqual(len(filas), 1)
        self.assertEqual((filas[0]["parada"], filas[0]["turnos"]), ("2", "4"))
        r = subprocess.run([sys.executable, RESUMEN, "--datos", self.datos], capture_output=True,
                           text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("enrutador:programador", r.stdout)
        self.assertIn("TOTAL", r.stdout)
        r = subprocess.run([sys.executable, RESUMEN, "--sesion", "otra", "--datos", self.datos],
                           capture_output=True, text=True, timeout=30)
        self.assertIn("sin corridas", r.stdout)


if __name__ == "__main__":
    unittest.main()
