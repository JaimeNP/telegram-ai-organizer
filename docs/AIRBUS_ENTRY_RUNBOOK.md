# Procedimiento de entrada de TAIO en el grupo Airbus

Este documento describe cómo meter TAIO en el grupo real en modo observación segura.

## Objetivo

Meter TAIO en el grupo Airbus sin que pueda ejecutar acciones reales.

Durante esta fase TAIO solo debe:

- leer mensajes;
- guardar actividad;
- detectar Topics;
- simular decisiones;
- permitir revisión por administradores.

TAIO no debe:

- borrar mensajes;
- mover mensajes;
- reenviar mensajes;
- avisar por privado;
- sancionar usuarios;
- modificar el grupo.

## Configuración obligatoria

Antes de entrar en el grupo real, el archivo `.env` debe tener:

```env
ACTION_MODE=listen
ENABLE_DELETES=false
ENABLE_REPOSTS=false
ENABLE_PRIVATE_NOTICES=false