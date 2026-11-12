# Lógica compartida del contrato de entrega (skills/orquestar/contrato.md).
# La cargan contrato-stop.sh (SubagentStop) y contrato-handback.sh (PreToolUse SubagentHandback).
# No se ejecuta sola: se carga con «.» y no imprime nada.

# revisar_contrato "<informe>"
#   Devuelve 0 si cumple. Si no, devuelve 1 y deja en CONTRATO_RAZON el motivo para el agente.
revisar_contrato() {
  local mensaje="$1" primera lineas bloque_max detalle
  local -a fallas=()
  CONTRATO_RAZON=""

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

  [ "${#fallas[@]}" -eq 0 ] && return 0

  detalle="$(printf '%s; ' "${fallas[@]}")"
  detalle="${detalle%; }"
  CONTRATO_RAZON="Tu informe no cumple el contrato de entrega: ${detalle}. Reescribe SOLO el informe final con las líneas ESTADO, RESUMEN, RUTAS, GIT, PRUEBAS, NO VERIFICADO y SIGUIENTE, en ≤25 líneas, citando ruta:línea en vez de pegar archivos, diffs o logs."
  return 1
}
