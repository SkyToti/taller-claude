# Diseño del plugin `enrutador` (marketplace local `taller`)

Especificación validada contra la documentación oficial (code.claude.com/docs) y Claude Code 2.1.322.
Quien construya el plugin sigue este documento; lo marcado «no verificado» se comprueba al construir.

## Propósito
Una sesión orquestadora (modelo caro) planea, delega e integra. Los subagentes del plugin ejecutan
con modelo fijo por tipo de tarea, devuelven resúmenes cortos y, si varios escriben a la vez,
cada uno trabaja en su worktree.

## Estructura
```
taller-claude/
├── .claude-plugin/marketplace.json     name "taller", plugins[{name:"enrutador", source:"./plugins/enrutador"}]
├── README.md                           qué es, cómo instalar, cómo agregar un agente
└── plugins/enrutador/
    ├── .claude-plugin/plugin.json      name, version, description, author
    ├── agents/{explorador,cartografo,investigador,redactor,programador,verificador}.md
    ├── skills/orquestar/{SKILL.md,contrato.md,plantilla-mapa.md}
    ├── hooks/hooks.json                SubagentStop (^enrutador:), PostToolUse (Agent), PreToolUse (Edit|Write)
    ├── scripts/{contrato-stop.sh,bitacora.sh,solo-claude-md.sh,sync-contrato.sh}
    └── evals/
```
Formato de referencia en disco: `/home/skytoti/.claude/plugins/marketplaces/impeccable/.claude-plugin/marketplace.json`,
`/home/skytoti/.claude/plugins/cache/impeccable/impeccable/4.7.1/` (plugin.json, agents, hooks) y
`/home/skytoti/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/` (skills de cómo se hace un plugin).

## Agentes
Se invocan como `enrutador:<nombre>`. Campos de frontmatter soportados en agentes de plugin:
`name, description, model, effort, maxTurns, tools, disallowedTools, skills, omitClaudeMd, isolation, color`.
Se ignoran `hooks`, `mcpServers`, `permissionMode`.

| Agente | Para qué | model / effort | tools | maxTurns |
|---|---|---|---|---|
| explorador | Localizar código y responder «dónde está X», leyendo primero el mapa de CLAUDE.md | haiku / low | Read, Grep, Glob | 15 |
| cartografo | Crear o actualizar el bloque del mapa en CLAUDE.md | haiku / medium | Read, Grep, Glob, Write, Edit | 30 |
| investigador | Web: competencia, costos, documentación. Deja notas en archivo | sonnet / medium | WebSearch, WebFetch, Read, Write | 25 |
| redactor | Textos en español de México: sitio, anuncios, plan | sonnet / medium | Read, Grep, Glob, Write, Edit | 20 |
| programador | Implementar y corregir | opus / high | Read, Grep, Glob, Edit, Write, Bash | 40 |
| verificador | Escribir y correr pruebas, revisar el diff | sonnet / medium | Read, Grep, Glob, Bash, Edit, Write | 30 |

- `isolation` NO va en el frontmatter: el orquestador lo pide en la llamada solo cuando hay dos o más
  agentes escribiendo a la vez.
- El cartógrafo solo puede escribir `CLAUDE.md`: lo impone `solo-claude-md.sh` (PreToolUse Edit|Write,
  revisa `agent_type == "enrutador:cartografo"`).
- El verificador solo edita archivos de prueba (por instrucción).
- Una lista `tools` cerrada quita los conectores MCP. Si un agente los necesita, usar `disallowedTools`.

## Contrato de entrega
Copia maestra en `skills/orquestar/contrato.md`; va repetido en el cuerpo de cada agente y
`sync-contrato.sh` comprueba que las copias coincidan.
```
ESTADO: hecho | parcial | bloqueado
RESUMEN: ≤3 líneas, qué cambió o qué se encontró
RUTAS: una por línea "- /ruta/absoluta[:línea] (creado|modificado|clave) — para qué"
GIT: rama <x> · worktree <ruta> · commit <sha7>   |  n/a
PRUEBAS: "<comando> → N ok / M fallan"  |  "no corridas: <motivo>"
NO VERIFICADO: supuestos y lo que no se pudo comprobar  |  "nada"
SIGUIENTE: 1 línea sugerida al orquestador
```
Máximo 25 líneas y 120 caracteres por línea. Prohibido pegar archivos, diffs, logs o resultados de
búsqueda: se cita `ruta:línea`; de un error, solo su primera línea. Lo largo se escribe a un archivo
y se devuelve la ruta.

## Hooks
- **SubagentStop**, matcher `^enrutador:` → `contrato-stop.sh`. Lee de stdin `last_assistant_message`
  y `stop_hook_active`. Comprueba: empieza con `ESTADO:`, contiene `PRUEBAS:` y `NO VERIFICADO:`,
  ≤25 líneas, sin bloques de código de más de 5 líneas. Si falla y `stop_hook_active` es false,
  responde `{"decision":"block","reason":"…"}`; si es true, deja pasar (evita bucles).
  Trampa: se dispara también para agentes internos con `agent_type` vacío; por eso el matcher anclado.
  Trampa: en modo auto el informe puede ir por `SubagentHandback` y no estar en `last_assistant_message`;
  en ese caso el script deja pasar.
- **PostToolUse**, matcher `Agent` → `bitacora.sh`. Agrega una línea a `${CLAUDE_PLUGIN_DATA}/bitacora.jsonl`
  con fecha, `tool_input.subagent_type`, `tool_input.model`, `tool_response.resolvedModel`, tokens,
  duración y número de herramientas usadas. Los nombres exactos de los campos de `tool_response`
  se confirman contra una llamada real (no verificado).
- **PreToolUse**, matcher `Edit|Write` → `solo-claude-md.sh` (ver cartógrafo).
- Los hooks corren en todas las sesiones: baratos, con `timeout` corto y sin fallar si falta `jq`.

## Skill `orquestar`
1. Rol: el orquestador planea, delega e integra; no lee archivos grandes ni ejecuta.
2. Primer paso: si CLAUDE.md no tiene el bloque `mapa:inicio` o su sha está atrasado, lanzar el cartógrafo.
3. Tabla tarea → agente → modelo.
4. Usar siempre `enrutador:*`. Nunca el `Explore` integrado (no carga CLAUDE.md) ni forks (modelo caro).
5. No pasar `model` en la llamada: anula al del agente. Solo para escalar a propósito, anotando el motivo.
6. Cada encargo lleva rutas exactas del mapa, objetivo, criterio de terminado y qué no tocar.
7. Oleadas: agrupar tareas independientes por archivos que no se pisen. Lectores e investigadores en
   paralelo sin worktree. Con dos o más que escriben, cada uno con `isolation: "worktree"`.
8. Antes de cada oleada: commit en el principal y `"worktree": {"baseRef": "head"}` en el proyecto.
9. En worktrees: `npm ci`, build y pruebas; nunca servidores de desarrollo.
10. El programador hace commit en su rama y lo reporta en `GIT:`.
11. Integrar una por una con `git merge --no-ff`; conflicto → un programador lo resuelve en el principal.
12. Después: `git worktree remove`, `git branch -d`. Nunca hacer push de ramas de worktree.
13. Tras integrar: verificador en el principal; si falla, devolver al programador solo `RUTAS` y `PRUEBAS`.
14. Informe que rompe el contrato: no pedir detalles, relanzar con encargo más estrecho.
15. Al cerrar: cartógrafo actualiza el mapa si cambió la estructura.

## Plantilla del mapa (`plantilla-mapa.md`)
Bloque entre `<!-- mapa:inicio sha=<sha7> fecha=<iso> -->` y `<!-- mapa:fin -->`, de 80 a 120 líneas.
El cartógrafo solo reescribe ese bloque. Secciones: propósito y stack · comandos exactos · árbol clave
(≤20 líneas) · módulos (ruta, responsabilidad, exporta, depende de) · URL → archivo · interfaces y
variables de entorno (solo nombres) · contenido y marketing · convenciones · pruebas · despliegue ·
zonas frágiles · recetas repetitivas → qué agente.

## Verificación
1. `claude plugin validate /home/skytoti/Proyectos/taller-claude --strict` y sobre `plugins/enrutador`.
2. `claude plugin marketplace add /home/skytoti/Proyectos/taller-claude` y
   `claude plugin install enrutador@taller` (scope user); `claude plugin details enrutador` debe
   listar 6 agentes, 1 skill y los hooks.
3. Probar cada script de hook a mano con JSON de ejemplo por stdin (caso que pasa y caso que bloquea).
4. Las tareas de humo con los agentes reales las corre el orquestador después de recargar los plugins.
