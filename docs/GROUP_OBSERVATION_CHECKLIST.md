# Checklist para meter TAIO en un grupo grande en modo observación

Este documento describe cómo meter TAIO en un grupo real sin riesgo.

El objetivo de esta fase no es moderar ni mover mensajes automáticamente.

El objetivo es:

- leer mensajes;
- guardar actividad;
- detectar Topics;
- simular decisiones;
- revisar resultados;
- aprender del funcionamiento real del grupo.

## Estado obligatorio antes de entrar

TAIO debe estar en modo seguro:

```env
ACTION_MODE=listen
ENABLE_DELETES=false
ENABLE_REPOSTS=false
ENABLE_PRIVATE_NOTICES=false