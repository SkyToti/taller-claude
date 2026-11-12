# Plantilla del mapa del proyecto

El cartógrafo copia el bloque de abajo al final del `CLAUDE.md` de la raíz (o reemplaza el que ya está)
y lo llena. Reglas:

- Todo va entre `<!-- mapa:inicio sha=<sha7> fecha=<AAAA-MM-DD> -->` y `<!-- mapa:fin -->`.
- El bloque lleno mide de 80 a 120 líneas. Lo que está fuera de las marcas no se toca.
- `sha` es el commit corto en que se hizo el mapa: el orquestador lo compara con `git rev-parse --short HEAD`
  para saber si está atrasado.
- Rutas relativas a la raíz. Variables de entorno solo por nombre, nunca su valor.
- Nada inventado: lo que no se pudo comprobar va como `PENDIENTE: …`; lo que no aplica, `— no aplica`.
- Las líneas entre `<` y `>` son instrucciones para llenar; se borran.

```markdown
<!-- mapa:inicio sha=<sha7> fecha=<AAAA-MM-DD> -->
## Mapa del proyecto

### Propósito y stack
<qué es, para quién, en 2 líneas>
<lenguaje, framework, versión de Node/Python, gestor de paquetes, hosting>

### Comandos exactos
- instalar: `<npm ci>`
- construir: `<npm run build>`
- probar: `<npm test>`
- lint/formato: `<npm run lint>`
- desarrollo (solo humanos, nunca agentes): `<npm run dev>`

### Árbol clave
<≤20 líneas, solo carpetas y archivos que importan, con un comentario corto>
src/
  pages/        <rutas del sitio>
  components/   <componentes compartidos>

### Módulos
| Ruta | Responsabilidad | Exporta | Depende de |
|---|---|---|---|
| <src/lib/x.ts> | <qué hace> | <funciones/tipos> | <módulos o servicios> |

### URL → archivo
| URL | Archivo |
|---|---|
| </> | <src/pages/index.astro> |

### Interfaces y variables de entorno
- APIs externas: <servicio — para qué — archivo que lo llama>
- Variables (solo nombres): <PUBLIC_X, API_KEY_Y> — definidas en <.env.example>

### Contenido y marketing
- Público: <a quién se le habla>
- Tono: <de tú/usted, palabras sí, palabras no>
- Dónde vive el texto: <ruta de contenidos>
- Reglas legales o de marca: <COFEPRIS, aviso de privacidad, etc. | — no aplica>

### Convenciones
- <nombres de archivos, estilo, cómo se agregan páginas o componentes>
- <ramas y mensajes de commit>

### Pruebas
- <framework, dónde viven, cómo correr solo una>
- <qué no está cubierto>

### Despliegue
- <dónde, cómo se dispara, rama que publica>
- <variables que necesita el entorno de producción (nombres)>

### Zonas frágiles
- <archivo o flujo> — <por qué hay que tocarlo con cuidado>

### Recetas repetitivas → agente
- Buscar dónde está algo → explorador
- Texto nuevo de una página o anuncio → redactor
- <tarea repetida de este proyecto> → <agente>
<!-- mapa:fin -->
```
