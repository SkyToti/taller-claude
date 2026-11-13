# Contrato de entrega (copia maestra)

Este archivo es la copia maestra. El bloque entre las marcas `contrato:inicio` y `contrato:fin` va
idéntico en el cuerpo de cada agente de `agents/`. Si lo cambias aquí, corre
`scripts/sync-contrato.sh --arreglar` para copiarlo a los agentes, y `scripts/sync-contrato.sh` para comprobar.
Los agentes de `plugins/estudio` usan esta misma copia: después corre también
`plugins/estudio/scripts/sync-contrato.sh --arreglar`.

Los hooks `SubagentStop` (`scripts/contrato-stop.sh`) y `PreToolUse` sobre `SubagentHandback`
(`scripts/contrato-handback.sh`), con la regla de `scripts/contrato-lib.sh`, revisan que el informe empiece con `ESTADO:`, traiga
`PRUEBAS:` y `NO VERIFICADO:`, no pase de 25 líneas y no tenga bloques de código de más de 5 líneas.

<!-- contrato:inicio -->
## Contrato de entrega

Tu respuesta final (o el mensaje de `SubagentHandback`, si tienes esa herramienta) es SOLO este informe,
con estas siete líneas de cabecera en este orden:

```text
ESTADO: hecho | parcial | bloqueado
RESUMEN: ≤3 líneas, qué cambió o qué se encontró
RUTAS: una por línea "- /ruta/absoluta[:línea] (creado|modificado|clave) — para qué"
GIT: rama <x> · worktree <ruta> · commit <sha7>   |  n/a
PRUEBAS: "<comando> → N ok / M fallan"  |  "no corridas: <motivo>"
NO VERIFICADO: supuestos y lo que no se pudo comprobar  |  "nada"
SIGUIENTE: 1 línea sugerida al orquestador
```

- Máximo 25 líneas y 120 caracteres por línea.
- Prohibido pegar archivos, diffs, logs o resultados de búsqueda: se cita `ruta:línea`.
- De un error, solo su primera línea.
- Lo largo se escribe a un archivo y se devuelve la ruta.
- El sha del commit se copia de la salida de git; nunca se escribe de memoria.
<!-- contrato:fin -->
