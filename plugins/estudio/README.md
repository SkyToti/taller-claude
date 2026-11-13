# estudio

Plugin para trabajar en un mod de Minecraft (Fabric) con agentes baratos y compuertas automáticas.
Va junto a `enrutador` en el marketplace `taller` y usa su contrato de entrega.

## Qué trae

| Pieza | Para qué |
|---|---|
| `agents/programador-mod.md` | Opus / high: código del mod en su worktree; compila con `./build.sh`, prueba con `./probar.sh`, commit en su rama |
| `agents/probador.md` | Sonnet / medium: pruebas Fabric GameTest en `src/gametest/**`, con comprobación negativa |
| `skills/mod/SKILL.md` | `estudio:mod`, la receta del orquestador: memoria, worktree, encargo, revisar, unir, probar |
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
