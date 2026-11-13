#!/usr/bin/env bash
# Hook SubagentStop (matcher ^enrutador:): revisa que el informe final del subagente siga el contrato
# de entrega (skills/orquestar/contrato.md). Si no lo sigue, lo bloquea una sola vez con
# {"decision":"block","reason":…}; con stop_hook_active=true siempre deja pasar (evita bucles).
# Deja pasar sin decir nada si falta jq, si la entrada no es la esperada o si el informe se entregó
# por SubagentHandback (ese informe lo revisa contrato-handback.sh en PreToolUse).

command -v jq >/dev/null 2>&1 || exit 0
. "$(dirname "${BASH_SOURCE[0]}")/contrato-lib.sh" 2>/dev/null || exit 0
entrada="$(cat 2>/dev/null)" || exit 0
[ -n "$entrada" ] || exit 0

printf '%s' "$entrada" | jq -e 'type == "object"' >/dev/null 2>&1 || exit 0
campo() { printf '%s' "$entrada" | jq -r "$1 // \"\" | tostring" 2>/dev/null; }

activo="$(campo .stop_hook_active)"
[ "$activo" = "true" ] && exit 0
tipo="$(campo .agent_type)"
case "$tipo" in enrutador:*|estudio:*) ;; *) exit 0 ;; esac

# Informe entregado por SubagentHandback: no está en last_assistant_message.
transcript="$(campo .agent_transcript_path)"
transcript="${transcript/#\~/$HOME}"
if [ -n "$transcript" ] && [ -f "$transcript" ] \
   && grep -Eq '"name" *: *"SubagentHandback"' "$transcript" 2>/dev/null; then
  exit 0
fi
mensaje="$(campo .last_assistant_message)"
# Mensaje vacío: no hay nada que revisar (y casi siempre es un hand-back).
[ -n "${mensaje//[[:space:]]/}" ] || exit 0

revisar_contrato "$mensaje" && exit 0
jq -cn --arg r "$CONTRATO_RAZON" '{decision: "block", reason: $r}' 2>/dev/null
exit 0
