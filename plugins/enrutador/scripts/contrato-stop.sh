#!/usr/bin/env bash
# Hook SubagentStop (matcher ^enrutador:): revisa que el informe final del subagente siga el contrato
# de entrega (skills/orquestar/contrato.md). Si no lo sigue, lo bloquea una sola vez con
# {"decision":"block","reason":…}; con stop_hook_active=true siempre deja pasar (evita bucles).
# Deja pasar sin decir nada si falta jq, si la entrada no es la esperada o si el informe se entregó
# por SubagentHandback (entonces last_assistant_message no es el informe).

command -v jq >/dev/null 2>&1 || exit 0
entrada="$(cat 2>/dev/null)" || exit 0
[ -n "$entrada" ] || exit 0

printf '%s' "$entrada" | jq -e 'type == "object"' >/dev/null 2>&1 || exit 0
campo() { printf '%s' "$entrada" | jq -r "$1 // \"\" | tostring" 2>/dev/null; }

activo="$(campo .stop_hook_active)"
[ "$activo" = "true" ] && exit 0
tipo="$(campo .agent_type)"
case "$tipo" in enrutador:*) ;; *) exit 0 ;; esac

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

fallas=()

primera="$(printf '%s\n' "$mensaje" | awk 'NF { sub(/^[ \t]+/, ""); print; exit }')"
case "$primera" in ESTADO:*) ;; *) fallas+=("no empieza con «ESTADO:»") ;; esac

printf '%s\n' "$mensaje" | grep -Eq '^[[:space:]]*PRUEBAS:' || fallas+=("falta la línea «PRUEBAS:»")
printf '%s\n' "$mensaje" | grep -Eq '^[[:space:]]*NO VERIFICADO:' || fallas+=("falta la línea «NO VERIFICADO:»")

lineas="$(printf '%s\n' "$mensaje" | awk 'END { print NR }')"
[ "${lineas:-0}" -le 25 ] || fallas+=("tiene $lineas líneas (máximo 25)")

bloque_max="$(printf '%s\n' "$mensaje" | awk '
  /^[ \t]*(```|~~~)/ { if (dentro) { if (n > max) max = n; dentro = 0 } else { dentro = 1; n = 0 }; next }
  dentro { n++ }
  END { if (dentro && n > max) max = n; print max + 0 }')"
[ "${bloque_max:-0}" -le 5 ] || fallas+=("trae un bloque de código de $bloque_max líneas (máximo 5)")

[ "${#fallas[@]}" -eq 0 ] && exit 0

detalle="$(printf '%s; ' "${fallas[@]}")"
detalle="${detalle%; }"
razon="Tu informe no cumple el contrato de entrega: ${detalle}. Reescribe SOLO el informe final con las líneas ESTADO, RESUMEN, RUTAS, GIT, PRUEBAS, NO VERIFICADO y SIGUIENTE, en ≤25 líneas, citando ruta:línea en vez de pegar archivos, diffs o logs."

jq -cn --arg r "$razon" '{decision: "block", reason: $r}' 2>/dev/null
exit 0
