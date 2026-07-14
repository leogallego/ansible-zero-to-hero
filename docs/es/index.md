# Ansible de Cero a Héroe

Bienvenido al curso Ansible de Cero a Héroe. Este curso progresivo enseña Ansible desde los principios básicos hasta la automatización de nivel de producción.

## La Historia

Seguirás a **Lionel**, un ingeniero de plataformas en **Parasol Tech**, mientras descubre Ansible para automatizar tareas repetitivas de infraestructura y luego escala gradualmente la práctica en toda la división.

## Módulos

| # | Módulo | Lo que Aprenderás |
|---|--------|-------------------|
| 1 | [Introducción a Ansible](modules/1-introduction.md) | Configuración del entorno, comandos ad-hoc |
| 2 | [Tu Primer Playbook](modules/2-your-first-playbook.md) | Anatomía de un playbook, idempotencia |
| 3 | [Gestión del Inventario](modules/3-managing-inventory.md) | Inventario estructurado, grupos |
| 4 | [Variables y Facts](modules/4-variables-and-facts.md) | Precedencia, facts, condicionales |
| 5 | [Templates y Handlers](modules/5-templates-and-handlers.md) | Templates Jinja2, handlers |
| 8 | [Roles y Colecciones](modules/8-roles-and-collections.md) | Reutilización de código, Galaxy, `ansible-creator` |
| 9 | [Testing de tu Automatización](modules/9-testing-your-automation.md) | Molecule, linting, pytest |
| 10 | [Empaquetado y Despliegue](modules/10-packaging-and-deployment.md) | Execution Environments, firma |
| 12 | [Escalando con AAP](modules/12-scaling-with-aap.md) | Controller, workflows, RBAC |

## Prerrequisitos

- Familiaridad con la línea de comandos de Linux (navegar directorios, editar archivos, ejecutar comandos)
- No se requiere experiencia previa con Ansible

## Entorno de Laboratorio

Elige tu entorno:

=== "Devcontainer Local"

    Requiere VS Code y Docker o Podman. Clona el repositorio y ábrelo en el devcontainer — todo está preinstalado.

=== "Red Hat Devtools Sandbox"

    Entorno en el navegador con todas las herramientas preinstaladas. No requiere configuración local.

Consulta el [Módulo 1](modules/1-introduction.md) para instrucciones detalladas de configuración.
