# Mensaje para el admin principal antes de meter TAIO

Hola,

quiero probar TAIO en el grupo en modo observación.

TAIO es un bot pensado para ayudar a ordenar la información del grupo por Topics, detectar duplicados, flood, enlaces y posibles mensajes que deberían estar en otro apartado.

## Importante

En esta fase TAIO NO va a moderar automáticamente.

No va a:

- borrar mensajes;
- mover mensajes;
- reenviar mensajes;
- avisar por privado a usuarios;
- sancionar a nadie;
- cambiar nada del grupo.

Solo va a:

- leer mensajes;
- guardar actividad;
- detectar Topics;
- simular qué habría hecho;
- permitir que los admins revisemos esas decisiones.

## Configuración de seguridad

El bot estará configurado así:

```env
ACTION_MODE=listen
ENABLE_DELETES=false
ENABLE_REPOSTS=false
ENABLE_PRIVATE_NOTICES=false