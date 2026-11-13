#!/usr/bin/env bash
# Comprueba que el bloque del contrato de cada agente sea idéntico a la copia maestra
# (skills/orquestar/contrato.md, entre <!-- contrato:inicio --> y <!-- contrato:fin -->).
#   sync-contrato.sh             → comprueba; sale con 1 si alguna copia difiere
#   sync-contrato.sh --arreglar  → reescribe las copias de los agentes con la maestra
#   sync-contrato.sh [--arreglar] <carpeta de agentes>…  → lo mismo con otras carpetas (otros plugins
#                                  del marketplace, p. ej. plugins/estudio/agents); por defecto, agents/
# No es un hook: se corre a mano después de tocar el contrato o de agregar un agente.
set -u

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
maestro="$raiz/skills/orquestar/contrato.md"
inicio='<!-- contrato:inicio -->'
fin='<!-- contrato:fin -->'

extraer() { awk -v i="$inicio" -v f="$fin" '$0==i{d=1;next} $0==f{d=0} d' "$1"; }

[ -f "$maestro" ] || { echo "falta la copia maestra: $maestro" >&2; exit 2; }
bloque="$(extraer "$maestro")"
[ -n "$bloque" ] || { echo "contrato.md no tiene el bloque $inicio … $fin" >&2; exit 2; }

arreglar=0
[ "${1:-}" = "--arreglar" ] && { arreglar=1; shift; }
carpetas=("$@")
[ "${#carpetas[@]}" -gt 0 ] || carpetas=("$raiz/agents")

tmpbloque="$(mktemp)"
trap 'rm -f "$tmpbloque"' EXIT
extraer "$maestro" > "$tmpbloque"

total=0 malas=0
archivos=()
for c in "${carpetas[@]}"; do for a in "$c"/*.md; do archivos+=("$a"); done; done
for agente in "${archivos[@]}"; do
  [ -f "$agente" ] || continue
  total=$((total + 1))
  nombre="$(basename "$agente")"
  if ! grep -qxF "$inicio" "$agente" || ! grep -qxF "$fin" "$agente"; then
    echo "sin marcas: $nombre (agrega las líneas $inicio y $fin)"
    malas=$((malas + 1))
    continue
  fi
  [ "$(extraer "$agente")" = "$bloque" ] && continue
  if [ "$arreglar" -eq 1 ]; then
    nuevo="$(mktemp)"
    awk -v i="$inicio" -v f="$fin" -v src="$tmpbloque" '
      $0==i { print; while ((getline l < src) > 0) print l; close(src); salta=1; next }
      $0==f { salta=0 }
      !salta { print }' "$agente" > "$nuevo" && cat "$nuevo" > "$agente"
    rm -f "$nuevo"
    echo "arreglado: $nombre"
  else
    echo "difiere: $nombre"
    malas=$((malas + 1))
  fi
done

if [ "$malas" -gt 0 ]; then
  echo "contrato: $malas de $total agentes no coinciden con skills/orquestar/contrato.md"
  exit 1
fi
echo "contrato: $total agentes coinciden con la copia maestra"
