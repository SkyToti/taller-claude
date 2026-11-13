# estudio

Plugin para trabajar en un mod de Minecraft (Fabric) con agentes baratos y compuertas automáticas.
Va junto a `enrutador` en el marketplace `taller` y usa su contrato de entrega.

## Qué trae

| Pieza | Para qué |
|---|---|
| `agents/programador-mod.md` | Opus / high: código del mod en su worktree; compila con `./build.sh`, prueba con `./probar.sh`, commit en su rama |
| `agents/probador.md` | Sonnet / medium: pruebas Fabric GameTest en `src/gametest/**`, con comprobación negativa |
| `agents/modelador.md` | Opus / high: modela y pinta criaturas por código con el kit del mod; se detiene en cada punto de control |
| `agents/animador.md` | Sonnet / high: guiones `.anim` → `anima.py` → `ojo.py` hasta LIMPIO; no toca modelo ni texturas |
| `skills/mod/SKILL.md` | `estudio:mod`, la receta del orquestador: memoria, worktree, encargo, revisar, unir, probar |
| `skills/criatura/SKILL.md` | `estudio:criatura`, la fábrica de criaturas: de la ficha al juego con 4 puntos de control |
| `skills/criatura/ficha.md` | Plantilla en lenguaje llano que llena el dueño para pedir una criatura |
| `scripts/puerta.py` | Compuerta (hooks `SubagentStop` y `PreToolUse` sobre `SubagentHandback`): no deja entregar hasta que compile |
| `.mcp.json` | Servidor MCP `minecraft-rcon` (consola del servidor por RCON) |
| `scripts/sync-contrato.sh` | Copia a los agentes el contrato de `enrutador/skills/orquestar/contrato.md` (fuente única) |
| `tests/test_puerta.py` | Pruebas de la compuerta con worktrees y `build.sh` de mentira |

## Requisitos

- `python3` (solo biblioteca estándar). No hace falta `jq`.
- El comando `minecraft-rcon-mcp` en el `PATH` (lee su configuración de su ruta por defecto).
- Un repo de mod con `build.sh` ejecutable (y `probar.sh` para las pruebas) y un `CLAUDE.md` con su mapa.
  En repos sin `build.sh` la compuerta no hace nada.
- El plugin `enrutador` para el explorador, el verificador y las métricas de tokens.

## El flujo

1. El orquestador carga `estudio:mod`, comprueba memoria y que no haya un cliente de Minecraft abierto.
2. Crea `<repo>/.claude/worktrees/<tarea>` con rama propia y encarga con rutas exactas del mapa.
3. `estudio:programador-mod` o `estudio:probador` trabajan ahí y hacen commit en su rama.
4. Al entregar, la compuerta corre `./build.sh` (y `./probar.sh` si el diff toca `src/`); si falla, les
   devuelve el error. Tope: 3 rechazos por agente; el código 75 (candado ocupado) no cuenta.
5. El orquestador revisa el diff de `src/main`, hace `git merge --no-ff` y borra worktree y rama.
6. Prueba base en el principal y despliegue al servidor de prueba: solo el orquestador.

## Fábrica de criaturas

1. El dueño llena `skills/criatura/ficha.md`; el orquestador la copia a `arte/rediseno/fichas/<id>.md` del
   worktree y pregunta (máx. 4 preguntas juntas) lo obligatorio que falte antes de modelar.
2. **PC1 silueta:** `estudio:modelador` entrega UNA hoja con 3 siluetas grises distintas (o concepto | silueta).
3. **PC2 modelo pintado:** el modelador termina la elegida; `bb.validar` y `defectos.py` en 0 y la ficha
   comprobada ✔/✘ antes de la hoja de 6 vistas.
4. **PC3 movimiento:** `estudio:animador` hace `vivo`, `andar`, `morir` y los `gesto.*` hasta que `ojo.py`
   diga LIMPIO.
5. Integración por scripts (`alta_criatura.py`, `a_juego.py`, `--comprobar`, `./build.sh`, `./probar.sh`);
   Java solo si la ficha pide conducta nueva (`estudio:programador-mod`).
6. **PC4 en el juego:** captura real con `./probar_cliente.sh`, solo el orquestador.

Meta: ≤2 rondas de corrección en total; si un punto pasa de 2, se para y se revisa la ficha con el dueño.
El modelador y el animador no pasan por la compuerta de Gradle: se validan con las herramientas del kit.

## Bitácora y compuerta

- Decisiones de la compuerta: `~/.claude/plugins/data/estudio-*/puerta.jsonl`
  (`paso | negado | agotada | omitida`, `build_rc`, `probar_rc`, `segundos`, `motivo`). Por ejemplo:
  `tail -5 ~/.claude/plugins/data/estudio-*/puerta.jsonl`
- Estado de los topes: `${TMPDIR:-/tmp}/estudio-puerta-<uid>/` (se limpia solo a las 24 h).
- Tokens reales por agente: `python3 plugins/enrutador/scripts/resumen-metricas.py [--sesion <id>]`.

## Mantenimiento

- Pruebas: `python3 -m unittest discover -s plugins/estudio/tests`
- Contrato: `plugins/estudio/scripts/sync-contrato.sh` (comprueba) o `--arreglar` (copia).
- Validar: `claude plugin validate plugins/estudio`
