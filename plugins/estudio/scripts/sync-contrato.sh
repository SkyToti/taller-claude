#!/usr/bin/env bash
# Sincroniza el bloque del contrato de los agentes de estudio con la copia maestra ÚNICA, la de enrutador
# (plugins/enrutador/skills/orquestar/contrato.md), usando el mismo script de enrutador.
#   sync-contrato.sh             → comprueba; sale con 1 si alguna copia difiere
#   sync-contrato.sh --arreglar  → reescribe las copias de agents/ con la maestra
# No es un hook: se corre a mano desde el repo del marketplace (necesita plugins/enrutador al lado).
set -u
raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sync="$raiz/../enrutador/scripts/sync-contrato.sh"
[ -f "$sync" ] || { echo "no encuentro $sync (¿plugins/enrutador está al lado?)" >&2; exit 2; }
if [ "${1:-}" = "--arreglar" ]; then
  exec bash "$sync" --arreglar "$raiz/agents"
fi
exec bash "$sync" "$raiz/agents"
