# taller-claude

Marketplace local `taller` con el plugin **`enrutador`**: una sesión orquestadora (modelo caro) planea,
delega e integra; seis subagentes con modelo fijo hacen el trabajo y devuelven informes cortos con un
contrato fijo. El diseño completo está en [`DISENO.md`](DISENO.md).

| Agente | Para qué | Modelo |
|---|---|---|
| `enrutador:explorador` | Dónde está X (lee primero el mapa de CLAUDE.md) | haiku |
| `enrutador:cartografo` | Crear o actualizar el mapa en CLAUDE.md (solo puede escribir ese archivo) | haiku |
| `enrutador:investigador` | Web: competencia, precios, documentación; notas a archivo | sonnet |
| `enrutador:redactor` | Textos en español de México, sin datos inventados | sonnet |
| `enrutador:programador` | Implementar y corregir; commit en su rama si va en worktree | opus |
| `enrutador:verificador` | Pruebas y revisión del diff; solo edita pruebas | sonnet |

La skill `orquestar` le dice a la sesión principal cómo enrutar, cómo armar oleadas con worktrees y cómo
integrar. Los hooks revisan el contrato de los informes (`SubagentStop`), registran cada llamada a
`Agent` en una bitácora (`PostToolUse`) y encierran al cartógrafo en `CLAUDE.md` (`PreToolUse`).

## Instalar

```bash
claude plugin marketplace add /home/skytoti/Proyectos/taller-claude
claude plugin install enrutador@taller          # alcance de usuario
claude plugin details enrutador                 # 6 agentes, 1 skill, hooks
```

Requiere `jq` para los hooks (sin `jq` no hacen nada, no fallan). Después de cambiar archivos del plugin,
sube `version` y corre `claude plugin marketplace update taller && claude plugin update enrutador@taller`;
en una sesión abierta, `/reload-plugins`.

## Agregar un agente

1. Crea `plugins/enrutador/agents/<nombre>.md` con frontmatter `name`, `description` (cuándo delegarle,
   con uno o dos ejemplos), `model`, `effort`, `maxTurns`, `tools`. Sin `isolation`: eso lo pide el
   orquestador en la llamada.
2. Al final del cuerpo pon dos líneas solas: `<!-- contrato:inicio -->` y `<!-- contrato:fin -->`, y corre
   `plugins/enrutador/scripts/sync-contrato.sh --arreglar` para copiar el contrato.
3. Agrega su fila a la tabla de enrutamiento de `plugins/enrutador/skills/orquestar/SKILL.md`.
4. `claude plugin validate plugins/enrutador --strict` y `plugins/enrutador/scripts/sync-contrato.sh`.
5. Sube `version` en `plugin.json` y en `.claude-plugin/marketplace.json` y actualiza el plugin instalado.

## Leer la bitácora

Cada subagente terminado agrega una línea JSON a `${CLAUDE_PLUGIN_DATA}/bitacora.jsonl`
(normalmente `~/.claude/plugins/data/enrutador-taller/bitacora.jsonl`): fecha, agente, modelo pedido y real,
tokens de la última petición, duración, herramientas usadas y el ESTADO del informe.

```bash
B=~/.claude/plugins/data/enrutador-taller/bitacora.jsonl
tail -n 20 "$B" | jq -c '{fecha, agente, modelo_real, tokens, duracion_ms, herramientas, informe}'
jq -s 'group_by(.agente) | map({agente: .[0].agente, veces: length,
  min_prom: ((map(.duracion_ms // 0) | add) / length / 60000)})' "$B"
```

Si `modelo_pedido` no es `null`, el orquestador forzó el modelo: debería traer su motivo en el encargo.

## Evals

`plugins/enrutador/evals/` trae tres casos de enrutamiento (`claude plugin eval`). Gastan créditos: córrelos
a propósito, no en cada cambio.
