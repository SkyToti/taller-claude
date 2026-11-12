#!/usr/bin/env bash
# Hook PreToolUse (matcher SubagentHandback): en modo auto los subagentes entregan su informe con la
# herramienta SubagentHandback (tool_input.message), no como último mensaje, así que SubagentStop no lo ve.
# Aquí se revisa ese informe con la misma regla (contrato-lib.sh) y, si no cumple, se niega la entrega
# con el motivo para que el agente lo rehaga. Solo para agent_type enrutador:*.
# Tope anti-bucle: un rechazo por agent_id; el segundo intento pasa aunque siga mal.
# Deja pasar en silencio si falta jq, si la entrada no es la esperada o si no hay agent_id.

command -v jq >/dev/null 2>&1 || exit 0
. "$(dirname "${BASH_SOURCE[0]}")/contrato-lib.sh" 2>/dev/null || exit 0
entrada="$(cat 2>/dev/null)" || exit 0
[ -n "$entrada" ] || exit 0
printf '%s' "$entrada" | jq -e 'type == "object" and .tool_name == "SubagentHandback"' >/dev/null 2>&1 || exit 0
campo() { printf '%s' "$entrada" | jq -r "$1 // \"\" | tostring" 2>/dev/null; }

tipo="$(campo .agent_type)"
case "$tipo" in enrutador:*) ;; *) exit 0 ;; esac

# Sin agent_id no se puede contar rechazos: mejor no arriesgar un bucle.
agente="$(campo .agent_id | tr -cd 'A-Za-z0-9_-')"
[ -n "$agente" ] || exit 0

mensaje="$(campo .tool_input.message)"
[ -n "${mensaje//[[:space:]]/}" ] || exit 0

dir="${TMPDIR:-/tmp}/enrutador-contrato-$(id -u 2>/dev/null || echo x)"
marca="$dir/$agente"
find "$dir" -type f -mmin +1440 -delete 2>/dev/null

if [ -e "$marca" ]; then
  # Segundo intento: ya se le rechazó una vez; pasa y se limpia para su próximo informe.
  rm -f "$marca" 2>/dev/null
  exit 0
fi

revisar_contrato "$mensaje" && exit 0

mkdir -p "$dir" 2>/dev/null && : > "$marca" 2>/dev/null || exit 0
jq -cn --arg r "$CONTRATO_RAZON Vuelve a llamar a SubagentHandback con el informe corregido." '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: $r
  }
}' 2>/dev/null
exit 0
