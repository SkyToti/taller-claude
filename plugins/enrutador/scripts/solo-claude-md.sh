#!/usr/bin/env bash
# Hook PreToolUse (matcher Edit|Write): el cartógrafo (agent_type "enrutador:cartografo") solo puede
# escribir archivos llamados CLAUDE.md. A cualquier otro agente o a la sesión principal no les hace nada.
# Sale con 0 sin imprimir si falta jq o la entrada no es la esperada.

command -v jq >/dev/null 2>&1 || exit 0
entrada="$(cat 2>/dev/null)" || exit 0
[ -n "$entrada" ] || exit 0

ruta="$(printf '%s' "$entrada" | jq -r '
  select(type == "object" and .agent_type == "enrutador:cartografo")
  | (.tool_input.file_path // .tool_input.path // "") | tostring' 2>/dev/null)" || exit 0
# Vacío: no es el cartógrafo o no hay ruta que revisar.
[ -n "$ruta" ] || exit 0

[ "$(basename -- "$ruta")" = "CLAUDE.md" ] && exit 0

jq -cn --arg r "El cartógrafo solo puede escribir CLAUDE.md (bloque del mapa); intentó escribir $ruta." '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: $r
  }
}' 2>/dev/null
exit 0
