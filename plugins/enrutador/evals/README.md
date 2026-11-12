# Evals de enrutamiento

Tres casos del tipo «dado este pedido, ¿a qué agente delega el orquestador?». Cada caso tiene `prompt.md`
y graders deterministas (`tool_used`, sin costo de juez):

- `agente-correcto`: llamó a `Agent` con el `subagent_type` esperado (solo cuenta con el plugin cargado).
- `sin-explore`: no delegó en `Explore` ni `general-purpose` (se puntúa en ambos brazos, da el Δ).
- `skill-orquestar`: indicador de que se cargó la skill `orquestar` (no puntúa cuando hay brazo sin plugin).

Correr (gasta créditos; cada corrida es una sesión completa):
`claude plugin eval plugins/enrutador --runs 1 --ablation none` desde la raíz del repo.
