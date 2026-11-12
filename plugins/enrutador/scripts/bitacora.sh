#!/usr/bin/env bash
# Hook PostToolUse (matcher Agent): agrega una línea JSON por cada subagente terminado a
# ${CLAUDE_PLUGIN_DATA}/bitacora.jsonl, para ver qué agente corrió, con qué modelo y cuánto costó.
# Nunca imprime nada ni bloquea; sale con 0 si falta jq, CLAUDE_PLUGIN_DATA o la entrada no es la esperada.

command -v jq >/dev/null 2>&1 || exit 0
[ -n "${CLAUDE_PLUGIN_DATA:-}" ] || exit 0
entrada="$(cat 2>/dev/null)" || exit 0
[ -n "$entrada" ] || exit 0

linea="$(printf '%s' "$entrada" | jq -c --arg fecha "$(date -Iseconds)" '
  select(type == "object" and (.tool_name == "Agent" or .tool_name == "Task")) |
  (.tool_input // {}) as $in |
  ((.tool_response | objects) // {}) as $out |
  {
    fecha: $fecha,
    sesion: (.session_id // null),
    agente: ($in.subagent_type // null),
    descripcion: ($in.description // null),
    modelo_pedido: ($in.model // null),
    modelo_real: ($out.resolvedModel // null),
    aislamiento: ($in.isolation // null),
    estado: ($out.status // null),
    tokens: ($out.totalTokens // null),
    duracion_ms: ($out.totalDurationMs // .duration_ms // null),
    herramientas: ($out.totalToolUseCount // null),
    informe: ([ ($out.content // empty) | if type == "array" then .[] | (.text? // empty) else tostring end
               | strings | capture("ESTADO:[ \t]*(?<e>[[:alpha:]]+)")? | .e ][0] // null)
  }' 2>/dev/null)" || exit 0
[ -n "$linea" ] || exit 0

mkdir -p "$CLAUDE_PLUGIN_DATA" 2>/dev/null || exit 0
printf '%s\n' "$linea" >> "$CLAUDE_PLUGIN_DATA/bitacora.jsonl" 2>/dev/null
exit 0
