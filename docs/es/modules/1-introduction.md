# Módulo 1: Introducción a Ansible

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Explicar qué es Ansible y por qué importa la automatización
- Configurar tu entorno de desarrollo (devcontainer o sandbox de Red Hat)
- Verificar tu instalación de Ansible Development Tools
- Ejecutar comandos ad-hoc contra localhost
- Navegar el índice de módulos de Ansible

## La Historia Hasta Ahora

Lionel es ingeniero de plataformas en **Parasol Tech**, la división de infraestructura de Parasol Insurance Corp. Cada semana, Lionel pasa horas repitiendo las mismas tareas: aprovisionar servidores, instalar paquetes, configurar servicios y verificar que todo sea consistente entre entornos. El trabajo es tedioso, propenso a errores e imposible de escalar.

Una tarde, un colega pasa por el escritorio de Lionel. "¿Todavía haces todo eso a mano? Deberías probar Ansible." Esa noche, Lionel abre una terminal y empieza a explorar.

Aquí es donde tu viaje también comienza.

## ¿Qué es Ansible?

Ansible es un motor de automatización de código abierto que te permite describir el estado deseado de tus sistemas y luego lo hace realidad. En lugar de escribir scripts que ejecutan comandos paso a paso, declaras *cómo* debería verse el sistema, y Ansible se encarga de *cómo* llegar ahí.

Cuatro propiedades hacen que Ansible destaque:

**Sin agentes** -- Ansible no requiere que se instale ningún software en las máquinas que administra. Se conecta por SSH estándar (o WinRM para Windows) y ejecuta tareas de forma remota. Sin demonios, sin agentes, sin infraestructura adicional.

**Declarativo** -- Describes el estado deseado ("este paquete debe estar instalado", "este servicio debe estar ejecutándose") en lugar de los pasos para llegar ahí. Los módulos de Ansible manejan los detalles de implementación.

**Idempotente** -- Ejecutar la misma automatización dos veces produce el mismo resultado. Si un paquete ya está instalado, Ansible omite el paso. Si un archivo ya tiene el contenido correcto, Ansible lo deja como está. Esto significa que puedes re-ejecutar tu automatización de forma segura sin miedo a romper cosas.

**Simple** -- Ansible usa YAML como lenguaje de configuración. Si puedes leer un archivo YAML, puedes leer un playbook de Ansible. No hay un lenguaje de programación personalizado que aprender.

!!! info "Cómo se conecta Ansible"
    Para destinos Linux/Unix, Ansible usa SSH. Copia pequeños programas en Python (llamados módulos) al host remoto, los ejecuta, recopila los resultados y limpia. El host administrado solo necesita Python y SSH -- nada más.

## ¿Por qué Automatizar?

El flujo de trabajo manual de Lionel tiene varios problemas que la automatización resuelve:

| Enfoque Manual | Con Automatización |
|----------------|-------------------|
| Los pasos viven en la cabeza de Lionel o en una wiki desactualizada | El playbook *es* la documentación -- siempre actual |
| Cada servidor está configurado ligeramente diferente | Cada servidor recibe exactamente la misma configuración |
| Toma 45 minutos por servidor | Toma segundos, se ejecuta en paralelo en docenas de servidores |
| Los errores se descubren días después en producción | El modo check detecta problemas antes de que ocurran |
| Solo Lionel sabe cómo hacerlo | Cualquier persona del equipo puede leer y ejecutar el playbook |

La automatización convierte el conocimiento tribal en código que puede ser versionado, revisado, probado y compartido. Cuando Lionel escribe un playbook, se convierte en un documento vivo que describe exactamente cómo está configurada la infraestructura de Parasol Tech.

## Ansible Development Tools (adt)

Red Hat proporciona un conjunto de herramientas de línea de comandos llamado **Ansible Development Tools** (`adt`). Piensa en `adt` como la caja de herramientas completa para desarrollar, probar y empaquetar contenido de Ansible. Usarás muchas de estas herramientas a lo largo del curso.

Esto es lo que incluye el paquete:

| Herramienta | Propósito | Primer Uso |
|-------------|-----------|------------|
| `ansible-core` | El motor central -- `ansible-playbook`, `ansible-galaxy`, comandos ad-hoc | Este módulo |
| `ansible-navigator` | TUI para ejecutar e inspeccionar ejecuciones de playbooks | Módulo 2 |
| `ansible-creator` | Scaffolding para roles, colecciones y proyectos de playbooks | Módulo 6 |
| `ade` | Gestión de entornos de desarrollo (instalación, árboles de dependencias) | Módulo 6 |
| `ansible-lint` | Análisis estático y corrección automática de contenido Ansible | Módulo 7 |
| `molecule` | Pruebas de integración para roles y colecciones | Módulo 7 |
| `pytest-ansible` | Pruebas funcionales de módulos y plugins | Módulo 7 |
| `tox-ansible` | Orquestación de pruebas y gestión de matrices | Módulo 7 |
| `ansible-builder` | Creación de Execution Environments (imágenes de contenedor) | Módulo 8 |
| `ansible-sign` | Firma de contenido para seguridad de la cadena de suministro | Módulo 8 |

!!! tip "No necesitas memorizar esto"
    Aprenderás cada herramienta cuando sea relevante en el curso. Por ahora, solo debes saber que `adt` instala todo lo que necesitas de una sola vez.

## Configuración del Entorno

Tienes dos opciones para tu entorno de laboratorio. Ambas te dan las mismas herramientas -- elige la que se adapte a tu flujo de trabajo.

=== "Devcontainer Local"

    El repositorio incluye una configuración de devcontainer que prepara un entorno de desarrollo completo dentro de un contenedor.

    **Prerequisitos:**

    - [VS Code](https://code.visualstudio.com/) con la [extensión Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
    - [Docker](https://www.docker.com/) o [Podman](https://podman.io/) instalado y ejecutándose

    **Pasos:**

    1. Clona el repositorio del curso:

        ```bash
        git clone https://github.com/leogallego/ansible-zero-to-hero.git
        cd ansible-zero-to-hero
        ```

    2. Abre la carpeta en VS Code:

        ```bash
        code .
        ```

    3. Cuando VS Code detecte el directorio `.devcontainer/`, te preguntará si deseas reabrir en el contenedor. Haz clic en **Reopen in Container**.

        Alternativamente, abre la paleta de comandos (++ctrl+shift+p++) y selecciona **Dev Containers: Reopen in Container**.

    4. Espera a que el contenedor se construya. Esto toma unos minutos la primera vez -- descarga una imagen base UBI9 con Python 3.12 e instala todas las herramientas.

    5. Una vez que el contenedor esté listo, tendrás una terminal dentro de VS Code con `adt` y todas las herramientas de Ansible disponibles.

    !!! note "Qué incluye el devcontainer"
        El contenedor está construido sobre Red Hat UBI9 con Python 3.12 e incluye: `ansible-dev-tools` (el paquete completo de `adt`), `podman` (para construir Execution Environments más adelante), y MkDocs Material (para ver el sitio del curso localmente en el puerto 8000).

=== "Red Hat Devtools Sandbox"

    El [Red Hat Developer Sandbox](https://developers.redhat.com/products/ansible/getting-started) proporciona un entorno de desarrollo basado en navegador con `adt` preinstalado. No se necesita configuración local.

    **Pasos:**

    1. Ve a [developers.redhat.com/products/ansible/getting-started](https://developers.redhat.com/products/ansible/getting-started).

    2. Inicia sesión con tu cuenta de Red Hat (gratuita para crear).

    3. Lanza el entorno sandbox. Obtendrás un IDE basado en navegador con una terminal.

    4. Clona el repositorio del curso dentro del sandbox:

        ```bash
        git clone https://github.com/leogallego/ansible-zero-to-hero.git
        cd ansible-zero-to-hero
        ```

    5. Todas las herramientas de `adt` están preinstaladas -- puedes empezar a trabajar de inmediato.

    !!! note "Sesiones del sandbox"
        Las sesiones del sandbox pueden tener límites de tiempo. Guarda tu trabajo haciendo commit y push a tu propio fork si necesitas continuar después.

### Verificación del Entorno

Sin importar qué opción hayas elegido, verifica que todo funcione. Abre una terminal y ejecuta:

```bash
adt --version
```

Deberías ver una salida listando todas las herramientas y sus versiones:

```text
ansible-builder                 24.12.1
ansible-core                    2.18.2
ansible-creator                 25.1.0
ansible-dev-environment         25.1.0
ansible-dev-tools               25.2.1
ansible-lint                    25.2.1
ansible-navigator               25.2.0
ansible-sign                    0.1.1
molecule                        25.2.1
pytest-ansible                  25.2.0
tox-ansible                     25.2.0
```

!!! tip "Los números de versión pueden variar"
    Los números de versión exactos dependen de cuándo configuraste tu entorno. Lo importante es que todas las herramientas aparezcan sin errores.

Ahora verifica las herramientas principales individualmente:

```bash
ansible --version
```

```text
ansible [core 2.18.2]
  config file = None
  configured module search path = ['/home/default/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /opt/app-root/lib64/python3.12/site-packages/ansible
  ansible collection location = /home/default/.ansible/collections:/usr/share/ansible/collections
  executable location = /opt/app-root/bin/ansible
  python version = 3.12.8 (main, Jan 17 2025, 00:00:00) [GCC 11.5.0 20240719 (Red Hat 11.5.0-2)]
  jinja version = 3.1.5
  libyaml = True
```

```bash
python3 --version
```

```text
Python 3.12.8
```

Si los tres comandos se ejecutan sin errores, tu entorno está listo.

## Tus Primeros Comandos Ad-Hoc

Un **comando ad-hoc** es una línea única que ejecuta un solo módulo de Ansible contra uno o más hosts. Es la forma más rápida de hacer algo con Ansible -- no se necesita un playbook.

La sintaxis general es:

```bash
ansible <patrón-de-hosts> -m <módulo> -a "<argumentos-del-módulo>"
```

Probemos algunos comandos contra `localhost` -- la máquina en la que estás trabajando.

### Ping

El módulo `ansible.builtin.ping` no es un ping ICMP. Verifica que Ansible puede conectarse al destino y que Python está disponible:

```bash
ansible localhost -m ansible.builtin.ping
```

```text
localhost | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

Dos cosas a notar:

- **`changed: false`** -- el módulo ping no modifica nada, así que reporta cero cambios. Esto es la idempotencia en acción.
- **`ping: pong`** -- el módulo se ejecutó exitosamente y devolvió un resultado.

### Recopilar Facts

El módulo `ansible.builtin.setup` recopila información detallada (llamada **facts**) sobre el sistema destino -- SO, red, memoria, CPU y mucho más:

```bash
ansible localhost -m ansible.builtin.setup
```

La salida es extensa. Aquí hay un pequeño extracto:

```json
localhost | SUCCESS => {
    "ansible_facts": {
        "ansible_distribution": "RedHat",
        "ansible_distribution_version": "9.5",
        "ansible_hostname": "toolbox",
        "ansible_kernel": "6.19.14-100.fc42.x86_64",
        "ansible_memtotal_mb": 15736,
        "ansible_os_family": "RedHat",
        "ansible_python_version": "3.12.8",
        ...
    }
}
```

!!! tip "Filtrar facts"
    Puedes filtrar la salida para mostrar solo facts específicos: `ansible localhost -m ansible.builtin.setup -a "filter=ansible_distribution*"`. Esto es útil cuando solo necesitas un dato específico.

### Ejecutar un Comando

El módulo `ansible.builtin.command` ejecuta un comando en el destino:

```bash
ansible localhost -m ansible.builtin.command -a "hostname"
```

```text
localhost | CHANGED => {
    "changed": true,
    "cmd": ["hostname"],
    "rc": 0,
    "stdout": "toolbox",
    "stdout_lines": ["toolbox"]
}
```

Observa que `changed` es `true` aquí. El módulo `command` siempre reporta changed porque no puede saber si el comando realmente modificó el sistema. En un playbook, agregarías una cláusula `changed_when:` para hacer esto preciso -- pero ese es un tema para módulos posteriores.

!!! warning "command vs shell"
    El módulo `ansible.builtin.command` no procesa el comando a través de un shell, por lo que pipes (`|`), redirecciones (`>`) y variables de entorno no funcionan. Si necesitas funcionalidades del shell, usa `ansible.builtin.shell` en su lugar -- pero prefiere `command` cuando puedas, porque es más seguro.

## Entendiendo los Módulos

Cada comando ad-hoc y tarea de playbook en Ansible usa un **módulo**. Un módulo es una unidad de código que Ansible ejecuta en el host destino para realizar una acción específica: instalar un paquete, copiar un archivo, iniciar un servicio, crear un usuario.

Ansible incluye cientos de módulos integrados (la colección `ansible.builtin`), y miles más están disponibles a través de colecciones de la comunidad y proveedores en [Ansible Galaxy](https://galaxy.ansible.com/).

### Fully Qualified Collection Names (FQCNs)

Cada módulo tiene un **Fully Qualified Collection Name** que lo identifica de forma única:

```text
namespace.collection.module_name
```

Por ejemplo:

| FQCN | Qué Hace |
|------|----------|
| `ansible.builtin.copy` | Copia archivos a hosts remotos |
| `ansible.builtin.yum` | Gestiona paquetes con yum |
| `ansible.builtin.service` | Gestiona servicios del sistema |
| `ansible.builtin.user` | Gestiona cuentas de usuario |
| `ansible.builtin.file` | Gestiona archivos y directorios |

!!! info "Siempre usa FQCNs"
    Puede que veas tutoriales antiguos usando nombres cortos como `copy` o `yum`. Aunque esto todavía funciona para módulos integrados, es ambiguo cuando múltiples colecciones proporcionan módulos con el mismo nombre. A lo largo de este curso, siempre usaremos el nombre completamente cualificado.

### Encontrar Módulos

Puedes explorar la lista completa de módulos integrados en la [documentación de Ansible](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/index.html). Para buscar desde la línea de comandos:

```bash
ansible-doc -l | grep -i file
```

Esto lista todos los módulos con "file" en su nombre o descripción. Para ver la documentación detallada de un módulo específico:

```bash
ansible-doc ansible.builtin.copy
```

Esto muestra los parámetros del módulo, ejemplos y valores de retorno -- todo sin salir de tu terminal.

## Resumen

En este módulo:

- Aprendiste que Ansible es sin agentes, declarativo, idempotente y simple
- Configuraste tu entorno de desarrollo con la caja de herramientas completa de `adt`
- Verificaste que todas las Ansible Development Tools están instaladas
- Ejecutaste comandos ad-hoc para hacer ping, recopilar facts y ejecutar comandos en localhost
- Exploraste los módulos y los Fully Qualified Collection Names (FQCNs)

Lionel está enganchado. Ejecutar comandos ad-hoc es útil, pero hacer las cosas un comando a la vez no es mucho mejor que hacerlas manualmente. Lo que Lionel necesita es una forma de definir una secuencia de tareas y ejecutarlas repetidamente. Eso es exactamente para lo que sirven los playbooks.

## Próximos Pasos

Siguiente: [Módulo 2 -- Tu Primer Playbook](2-your-first-playbook.md)
