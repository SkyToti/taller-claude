---
name: mod
description: "Receta del orquestador para cambiar un mod de Minecraft (Fabric) con agentes baratos en worktrees y la compuerta de compilación de estudio: comprobar memoria, crear el worktree, encargar a estudio:programador-mod o estudio:probador, revisar, unir y probar en el servidor de prueba. Úsala al empezar cualquier cambio en un mod con este flujo (repos con build.sh y probar.sh), antes de lanzar agentes."
---

# Cambiar un mod con `estudio`

Tú planeas, encargas, revisas el diff e integras. Los agentes compilan y prueban; la compuerta
(`scripts/puerta.py`) no les deja entregar hasta que `./build.sh` (y `./probar.sh` si tocaron `src/`) pasen.
Desplegar, arrancar servidores y abrir el juego (`./probar_cliente.sh`) es solo tuyo.

## Pasos

1. **Memoria y juego abierto.** `free -g`: si quedan menos de ~6 GB libres, espera o cierra algo.
   Busca clientes de Minecraft: `pgrep -x java` y para cada pid `tr '\0' ' ' < /proc/<pid>/cmdline`
   (un cliente trae `net.minecraft.client` o `KnotClient`). Nunca `pgrep -f`: se encuentra a sí mismo y
   a cualquier orden que mencione java. Con un cliente abierto, no compiles: avisa a la persona.
2. **Mapa.** Lee el `CLAUDE.md` del repo del mod (órdenes, recetas, reglas, mapa). Si no sabes dónde vive
   algo, `enrutador:explorador` para ubicarlo antes de encargar.
3. **Worktree por tarea.** Commit de lo pendiente en el principal y luego
   `git -C <repo> worktree add .claude/worktrees/<tarea> -b <tarea>`. Lo creas TÚ: no uses
   `isolation: "worktree"` (tu sesión vive en otro repo y saldría del equivocado).
4. **Encargo** (plantilla; rutas absolutas):
   ```text
   Objetivo: <una línea>.  Worktree: <repo>/.claude/worktrees/<tarea> (rama <tarea>).
   Rutas: <las exactas del mapa>.  No tocar: <qué queda fuera>.
   Terminado: <criterio comprobable: build OK, prueba X en verde, comportamiento Y>.
   GIT: rama <tarea> · worktree <ruta absoluta> · commit <sha7 leído de git log>
   ```
5. **Qué agente.**
   | Tarea | Agente |
   |---|---|
   | Código del mod (`src/main`, recursos) | `estudio:programador-mod` |
   | Pruebas GameTest (`src/gametest`) | `estudio:probador` |
   | Dónde está X, qué usa qué | `enrutador:explorador` |
   | Revisar un diff grande antes de unir | `enrutador:verificador` |
   Código y pruebas de la misma función: primero el programador, luego el probador sobre su rama (o en
   otro worktree si no se pisan). Si el probador pide un getter en `src/main`, encárgalo al programador.
6. **Revisa tú el diff de `src/main`** antes de unir: `git -C <worktree> diff <base>...HEAD -- src/main`.
   Busca cambios fuera del alcance, números de balance tocados sin pedirlo y código muerto.
7. **Unir y limpiar.** En el principal: `git merge --no-ff <tarea>`; luego
   `git worktree remove .claude/worktrees/<tarea>` y `git branch -d <tarea>`. De una rama en una.
8. **Prueba base en el principal:** `./build.sh`, `./probar.sh`, desplegar al servidor de PRUEBA con la
   receta del `CLAUDE.md` del mod, revisar errores en su registro (`grep -iE 'error|exception'`) y apagarlo.
   Lo que solo se ve dentro del juego lo revisa la persona (o tú con `./probar_cliente.sh`).
9. **Al final**, `./gradlew --stop` en el principal para soltar la memoria de los daemons de Gradle
   (es la única vez que se llama a gradlew directo, y sin compilar nada).

## Si la compuerta agotó sus intentos
Tras 3 rechazos por agente, el cuarto intento pasa y queda `"puerta": "agotada"` en la bitácora: el informe
llega aunque NO compile. No unas esa rama. Lee las últimas líneas de `puerta.jsonl` (motivo `build` o
`probar`), corre tú `./build.sh` en el worktree para ver el error y relanza un `estudio:programador-mod`
NUEVO (no reanudes el viejo) con un encargo más estrecho: el error en una línea y la ruta donde está.
Si el motivo fue `candado`, otra sesión estaba compilando: espera y pide al agente que vuelva a entregar.

## Bitácoras
- `~/.claude/plugins/data/estudio-*/puerta.jsonl`: cada decisión de la compuerta (paso, negado, agotada,
  omitida), con build_rc, probar_rc y segundos.
- Tokens reales por agente: `python3 <raíz de enrutador>/scripts/resumen-metricas.py --sesion <id>`.
