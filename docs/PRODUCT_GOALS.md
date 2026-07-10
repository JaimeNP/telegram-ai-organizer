# Objetivos del producto - TAIO

TAIO es un bot de Telegram pensado para ayudar a gestionar grupos grandes con Topics/Foros.

El primer caso de uso es un grupo de unas 4.000 personas, donde se necesita mantener organizada la información importante sin cortar la conversación normal.

## Objetivo principal

Mantener General como un espacio principalmente para conversación y debate, mientras que la información importante queda organizada en los apartados correspondientes.

El objetivo no es censurar a nadie, sino facilitar que la información importante no se pierda entre miles de mensajes.

## Funciones principales previstas

- Clasificar automáticamente los mensajes publicados en General y trasladarlos al apartado correspondiente cuando sea evidente.
- Organizar mensajes en Topics como Propuestas, Medios, Carpooling, Archivo u otros que existan en el grupo.
- Analizar enlaces y publicarlos en el apartado adecuado según su contenido.
- Detectar mensajes prácticamente duplicados, como una noticia ya compartida o el mismo texto repetido.
- Evitar que mensajes duplicados vuelvan a publicarse innecesariamente.
- Detectar spam, flood, mensajes escritos íntegramente en mayúsculas o mensajes que incumplan normas básicas del grupo.
- Avisar siempre por privado al autor indicando el motivo de la acción.
- Evitar polémicas públicas en el chat principal.
- Aprender del funcionamiento del grupo con el tiempo.
- Mejorar la clasificación según las decisiones de los administradores.

## Principios de seguridad

TAIO debe ser prudente antes de actuar.

Antes de borrar, mover o reenviar mensajes automáticamente, debe pasar por fases seguras:

1. Escuchar.
2. Guardar mensajes.
3. Simular decisiones.
4. Mostrar decisiones a administradores.
5. Aprender de correcciones.
6. Ejecutar acciones reales solo cuando haya suficiente confianza.

## Fase actual

Actualmente TAIO está en modo seguro:

- Lee mensajes.
- Guarda mensajes en PostgreSQL.
- Detecta General y Topics.
- Detecta duplicados básicos.
- Detecta algunas reglas básicas de moderación.
- Guarda decisiones simuladas.
- No borra mensajes.
- No mueve mensajes.
- No avisa por privado.
- No ejecuta acciones reales.

## Regla fundamental

TAIO debe ayudar a ordenar el grupo, no generar sensación de censura.