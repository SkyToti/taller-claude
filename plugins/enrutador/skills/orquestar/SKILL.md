---
name: orquestar
description: "Cómo trabajar como orquestador con los subagentes del plugin enrutador: planear, delegar en oleadas con el modelo justo, integrar worktrees y leer informes cortos. Úsala al empezar cualquier tarea de varios pasos en un proyecto (sitio, anuncios, código, investigación) y siempre antes de lanzar subagentes."
---

# Orquestar con `enrutador`

Junto a este archivo están `contrato.md` (formato de los informes) y `plantilla-mapa.md` (mapa de CLAUDE.md).

## Reglas

1. **Tu rol.** Planeas, delegas e integras. No lees archivos grandes, no buscas por el repo ni corres builds
   o pruebas: eso lo hacen los agentes. Tú lees informes, decides y haces commits y merges.
2. **Primer paso: el mapa.** Busca `mapa:inicio` en el `CLAUDE.md` de la raíz. Si no está, o su `sha=` quedó atrás de
   HEAD y `git diff --stat <sha>..HEAD` muestra archivos o carpetas nuevos, lanza `enrutador:cartografo`
   antes que nada, pasándole el sha7, la fecha y la ruta absoluta de `plantilla-mapa.md`.
3. **Enrutamiento.** Elige el agente por la tarea con esta tabla:

   | Tarea | Agente | Modelo / esfuerzo |
   |---|---|---|
   | Dónde está X, qué usa qué, leer código | `enrutador:explorador` | haiku / low |
   | Crear o actualizar el mapa de CLAUDE.md | `enrutador:cartografo` | haiku / medium |
   | Web: competencia, precios, documentación | `enrutador:investigador` | sonnet / medium |
   | Textos: páginas, anuncios, correos, plan | `enrutador:redactor` | sonnet / medium |
   | Implementar, corregir, resolver conflictos | `enrutador:programador` | opus / high |
   | Pruebas, revisar diff, antes de desplegar | `enrutador:verificador` | sonnet / medium |

4. **Siempre `enrutador:*`.** Nunca el `Explore` integrado (no carga CLAUDE.md, así que no ve el mapa) ni
   forks (heredan tu modelo caro). Si ninguna fila encaja, parte la tarea hasta que encaje.
5. **No pases `model`** en la llamada: anula el del agente. Solo para escalar a propósito (por ejemplo un
   explorador que falló dos veces con algo enredado → `sonnet`), y anota el motivo en el encargo.
6. **Cada encargo lleva**: rutas exactas sacadas del mapa, objetivo en una línea, criterio de terminado
   comprobable, qué no tocar y, si aplica, dónde escribir lo largo. Nada de «revisa el proyecto».
7. **Oleadas.** Agrupa las tareas independientes cuyos archivos no se pisen y lánzalas en el mismo
   mensaje. Lectores (explorador, investigador) van en paralelo sin worktree. Si dos o más agentes
   escriben a la vez, cada uno lleva `isolation: "worktree"`. Uno solo escribiendo trabaja en el principal.
8. **Antes de cada oleada con worktrees**: commit de lo pendiente en el principal y, una vez por proyecto,
   `"worktree": {"baseRef": "head"}` en `.claude/settings.json` para que los worktrees salgan de tu HEAD
   y no de la rama remota.
9. **En worktrees** el agente corre `npm ci` (o lo que diga el mapa), build y pruebas. Nunca servidores de
   desarrollo; si algo solo se ve en el navegador, lo revisa una persona.
10. **El programador hace commit en su rama** y lo reporta en `GIT:`. Sin esa línea no hay nada que integrar:
    relánzalo pidiendo el commit.
11. **Integra de una en una**: `git merge --no-ff <rama>` en el principal, en el orden de la oleada. Si hay
    conflicto, no lo resuelvas tú: deja el merge a medias y lanza un programador en el principal con las
    rutas en conflicto.
12. **Limpia** después de integrar: `git worktree remove <ruta>` y `git branch -d <rama>`. Nunca hagas push de
    ramas de worktree.
13. **Después de integrar**, `enrutador:verificador` en el principal. Si falla, al programador le pasas solo
    las líneas `RUTAS` y `PRUEBAS` del informe del verificador, no tu interpretación.
14. **Informe que rompe el contrato** (o que pide más turnos): no le pidas detalles. Relánzalo con un encargo
    más estrecho. El hook `SubagentStop` ya bloquea una vez los informes mal formados.
15. **Al cerrar**: si cambió la estructura (archivos, rutas, comandos), cartógrafo para actualizar el mapa.

## Recetas

### Actualizar el mapa
1. `git rev-parse --short HEAD` y la fecha de hoy.
2. `enrutador:cartografo`: «Actualiza el bloque del mapa en <raíz>/CLAUDE.md. sha=<sha7> fecha=<fecha>.
   Plantilla: <ruta absoluta de plantilla-mapa.md>. Cambió: <qué>. Terminado: bloque de 80–120 líneas.»
3. Revisa que `RUTAS:` traiga solo `CLAUDE.md` y haz commit.

### Página nueva del sitio
1. Oleada 1 en paralelo: explorador («cómo se agrega una página, qué componentes usa la más parecida»)
   e investigador si hace falta un dato de fuera.
2. Redactor escribe el texto en `contenido/<página>.md` (o donde diga el mapa), con `PENDIENTE:` donde
   falten datos. Resuelve los pendientes con la persona antes de seguir.
3. Programador arma la página con ese texto. Criterio: build limpio y la URL nueva en la sección
   «URL → archivo» del informe.
4. Verificador; luego cartógrafo si se agregó la ruta.

### Lote de anuncios
1. Si no hay datos del público o de la competencia, investigador primero (notas a archivo).
2. Redactor con: plataforma, límites de caracteres, número de variantes, ángulos distintos, reglas legales
   del mapa y archivo de salida. Un solo redactor por lote para que no se repitan.
3. Revisa los `PENDIENTE:` y que ningún dato del negocio sea inventado.

### Revisión antes de desplegar
1. Commit en el principal; nada sin integrar en worktrees (`git worktree list`).
2. Verificador: diff contra la última versión desplegada (`git diff <tag|rama de producción>...HEAD`),
   build, lint y suite completa; buscar secretos, `PENDIENTE:` y `console.log` olvidados.
3. Si algo falla → programador con `RUTAS` y `PRUEBAS`, y de nuevo verificador.
4. Desplegar lo decide la persona; tú solo reportas que está listo.

## Bitácora
Cada llamada a `Agent` deja una línea en `${CLAUDE_PLUGIN_DATA}/bitacora.jsonl` (agente, modelo pedido y real,
tokens, duración, herramientas, ESTADO). Úsala para ver si un agente se queda corto o se pasa de turnos.
