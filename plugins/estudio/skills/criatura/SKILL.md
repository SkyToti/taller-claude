---
name: criatura
description: "Fábrica de criaturas: receta del orquestador para llevar un mob nuevo de una ficha llenada por el dueño a modelo pintado, animación e integración en el mod, con cuatro puntos de control y pocas rondas de corrección. Úsala cuando la persona describa o pida un mob, criatura, jefe menor u objeto animado nuevo para el mod."
---

# Fábrica de criaturas con `estudio`

Tú diriges; `estudio:modelador` modela y pinta, `estudio:animador` anima, los scripts del kit integran.
El dueño solo ve los **puntos de control** (PC1–PC4): una hoja por punto. Todo lo que un script puede
comprobar (medidas, caras encimadas, nombres de clips, datos del juego) se resuelve antes y nunca le llega.
Worktree, unir y prueba base: sigue `estudio:mod` (pasos 1–3, 7 y 8); aquí no se repiten.
Órdenes del kit: desde `arte/rediseno/` del worktree; las de compilar y probar, desde su raíz.

## Paso 0 · Ficha
1. Dale al dueño `${CLAUDE_PLUGIN_ROOT}/skills/criatura/ficha.md` (o llénala tú con lo que ya dijo).
2. Cópiala a `arte/rediseno/fichas/<id>.md` en el worktree y sus imágenes a
   `arte/rediseno/fichas/<id>/ref_<n>.png` (con el número que les dio el dueño).
3. Si falta un campo **(*)**, pregúntalo ANTES de modelar: todas las dudas juntas, máximo 4 preguntas.
   Nunca rellenes un obligatorio por intuición. Lo no obligatorio vacío lo deciden los agentes.
4. Si `<id>` ya existe en `src/main/resources/torre_fabrica/mobs.json`, para y pregunta.

## PC1 · Silueta (barato)
- Encarga a `estudio:modelador`: «PC1 de `<id>`», ficha y worktree en rutas absolutas.
- Sin concepto: UNA hoja con 3 siluetas claramente distintas entre sí y de las criaturas existentes, en
  bloques grises sin pintar, cada una con su alto en bloques y nº aproximado de cubos.
- Con concepto: UNA hoja de superposición concepto | silueta, en vez de 3 opciones.
- Enseña la hoja (ruta de `RUTAS:`) con la lista ✔/✘ del informe. El dueño elige, mezcla o corrige.

## PC2 · Modelo pintado
- `estudio:modelador` termina la elegida: modelo, texturas, `a_bbmodel.py <id>` y `ficha_rig.py` (`.rig.md`).
- Antes de enseñar nada: `bb.validar` y `kit/defectos.py` con 0 errores y la ficha comprobada punto por punto.
  Si su informe trae algún ✘ o errores, devuélveselo; no se lo enseñes al dueño.
- UNA hoja: 6 vistas + recortes de detalle (cara, manos o garras, lo que brilla).
- Correcciones: por texto, o el dueño mueve el modelo en Blockbench y vuelve con `kit/de_blockbench.py`.

## PC3 · Movimiento
- `estudio:animador` escribe `arte/rediseno/guiones/<id>/<clip>.anim` para `vivo`, `andar`, `morir` y cada
  `gesto.<nombre>` de la ficha; ciclo `kit/anima.py` → `kit/ojo.py` hasta LIMPIO.
- UNA hoja por clip (o un video corto con `kit/video.py`, que pasa por la cola térmica).
- Si el animador dice que el rig no permite un movimiento, vuelve al modelador con eso en una línea.

## Integración (sin modelo de lenguaje: lo corres tú)
```text
python3 kit/alta_criatura.py <id> --nombre "…" --clase <bestia|bestia_voladora|bestia_arquera|mini_jefe> \
        --ancho … --alto … --como <mob existente> [--vida … --dano … --velocidad … --vista … --conducta …]
python3 kit/a_juego.py <id>                       # geo, animación, texturas y modelos/<id>.json al juego
python3 kit/alta_criatura.py --comprobar <id>     # todo ✔; un ✘ se arregla antes de seguir
./build.sh && ./probar.sh                         # desde la raíz del worktree
```
- Conducta «nueva» o mecánica propia: encarga a `estudio:programador-mod` (y `estudio:probador` para su
  GameTest) con la receta de `estudio:mod`. Una criatura estándar no lleva Java.

## PC4 · En el juego
- Une la rama, despliega al servidor de PRUEBA (`servidor.py desplegar elegia prueba`) y saca una captura
  real con `./probar_cliente.sh`. Solo tú, nunca un agente; no si el dueño está jugando o en directo.
- Enseña la captura: es lo que el dueño aprueba de verdad.

## Cierre
- Llena el «Registro» de `arte/rediseno/fichas/<id>.md`: fechas, rondas por punto, commit (leído de
  `git log -1 --format=%h`) y tokens con `python3 <raíz de enrutador>/scripts/resumen-metricas.py --sesion <sesión>`.
- Une, borra worktree y rama, `./gradlew --stop` (como en `estudio:mod`).

## Rondas
- Objetivo: ≤2 rondas de corrección en TOTAL. Cuenta cada «no» del dueño en el Registro.
- Si un punto de control pasa de 2 rondas, PARA: no relances al agente. Revisa la ficha con el dueño
  (¿falta un «a qué NO se parece», una medida, un innegociable?), corrígela y empieza ese punto otra vez.
- Cada corrección del dueño se vuelve una línea en la ficha (campo o innegociable), no solo en el encargo.

## Costo
- Imágenes solo en los puntos de control; entre puntos, números (validadores y `ojo.py`).
- Un agente por criatura a la vez (16 GB de RAM). Renders y videos van por `kit/cola.py`.
- Encargo nuevo y corto en cada punto (ficha + punto + correcciones); no reanudes un agente viejo.
- Nunca pidas «baja la resolución para que se vea pixelado»: la calidad no se reduce con una imagen.
