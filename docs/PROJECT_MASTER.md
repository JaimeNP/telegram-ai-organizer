# TAIO - Telegram AI Organizer

## Estado del proyecto

Versión: 0.1.0-dev

Estado: En desarrollo

Modo actual: Arquitectura aprobada

---

# Objetivo

TAIO es una plataforma inteligente para organizar automáticamente grupos de Telegram que utilizan Topics.

No está diseñado para un grupo concreto.

Debe poder instalarse en cualquier grupo con Topics sin modificar el código.

---

# Objetivos principales

- Reducir el ruido del Topic General.
- Clasificar automáticamente mensajes.
- Aprender de los Topics existentes.
- Ayudar a los administradores.
- Nunca sustituir completamente a los administradores.
- Minimizar falsos positivos.

---

# Filosofía

La IA ayuda.

La IA propone.

La IA aprende.

Los administradores siempre tienen el control.

---

# Tecnologías

Python 3.12

aiogram 3.x

PostgreSQL

Redis

Qdrant

SQLAlchemy 2

Alembic

Docker

Docker Compose

GitHub Actions

---

# Arquitectura

Monolito modular.

No microservicios.

Todo desacoplado mediante servicios.

---

# IA

Sistema híbrido.

Prioridad:

1. Reglas

2. Embeddings

3. Base de conocimiento

4. Contexto

5. LLM

El LLM solo se utilizará cuando sea realmente necesario.

---

# Clasificación

Nunca se clasifica usando únicamente nombres de Topics.

Siempre utilizando:

- embeddings
- contexto
- mensajes históricos
- aprendizaje continuo

---

# Topics

Los Topics son dinámicos.

El bot debe detectarlos automáticamente.

No existen nombres fijos.

---

# Seguridad

Nunca eliminar mensajes automáticamente durante el modo simulación.

Todas las decisiones deben quedar auditadas.

Todas las acciones deben poder deshacerse.

---

# Modos de funcionamiento

Modo Simulación

Modo Producción

---

# Roadmap

Sprint 1

Infraestructura

Sprint 2

Telegram

Sprint 3

Base de datos

Sprint 4

Embeddings

Sprint 5

Clasificación

Sprint 6

Moderación

Sprint 7

Dashboard

Sprint 8

Despliegue Raspberry

---

# Regla de oro

Antes de implementar una funcionalidad nueva:

¿Hace el proyecto más simple?

¿Hace el proyecto más robusto?

¿Hace el proyecto más útil?

Si la respuesta no es sí en las tres preguntas, la funcionalidad debe esperar.