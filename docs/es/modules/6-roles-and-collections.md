# Módulo 6: Roles y Colecciones

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Describir la estructura de directorios de un rol y las convenciones de nomenclatura
- Explicar cuándo usar `defaults/main.yml` vs `vars/main.yml`
- Crear scaffolding de roles y colecciones usando `ansible-creator`
- Gestionar entornos de desarrollo con `ade`
- Crear validación de argumentos con `meta/argument_specs.yml`
- Usar Fully Qualified Collection Names (FQCNs)

## La Historia Hasta Ahora

Lionel y Jordan han estado escribiendo playbooks, gestionando inventario entre entornos, usando variables y facts, y desplegando archivos de configuración con templates y handlers. La automatización funciona bien, pero vive en una pila creciente de playbooks dentro de un directorio, y otros equipos en Parasol Tech están empezando a pedir acceso.

"El equipo de base de datos quiere nuestra configuración de nginx," dice Lionel. "Y el equipo de monitoreo sigue copiando nuestras tareas de template en sus propios playbooks. Cada copia se desvía un poco."

Jordan asiente. "Necesitamos empaquetar esto. Una única fuente de verdad para la configuración del servidor web que cualquier equipo pueda consumir sin copiar archivos."

Esta semana, la dirección de Parasol Tech patrocina una **Comunidad de Prácticas (CoP)**, un grupo transversal dedicado a estándares de automatización. La primera decisión de la CoP: toda automatización reutilizable debe empaquetarse como **roles** dentro de **colecciones**. No más playbooks copiados y pegados.

## Qué Son los Roles?

Un rol es una unidad de automatización autocontenida con una estructura de directorios estandarizada. En lugar de poner todo en un solo playbook, divides la automatización en directorios bien definidos (tareas, variables, templates, handlers, metadatos), cada uno en su propio archivo. Ansible sabe cómo ensamblar estas piezas automáticamente.

Piensa en un rol como una función en programación. Recibe entradas (variables), realiza trabajo (tareas), y puede ser llamado desde cualquier playbook. La estructura de directorios es el contrato de interfaz: cualquiera que lea el rol sabe exactamente dónde encontrar cada pieza.

## Estructura de Directorios de un Rol

Cada rol sigue un esquema estandarizado. Esta es la estructura del rol `webserver` que construiremos en este módulo:

```text
roles/webserver/
  defaults/
    main.yml          # Variables orientadas al usuario con valores por defecto
  vars/
    main.yml          # Constantes internas (no para usuarios)
  tasks/
    main.yml          # La lista principal de tareas
  handlers/
    main.yml          # Definiciones de handlers
  templates/
    webserver.conf.j2 # Templates Jinja2
    index.html.j2
  files/              # Archivos estaticos (ninguno en este rol)
  meta/
    main.yml          # Metadatos del rol y dependencias
    argument_specs.yml # Validacion de entradas
  README.md           # Documentacion
```

No todos los directorios son obligatorios. Ansible solo usa los directorios que existen. Pero los nombres son estrictos: `tasks/main.yml`, no `tasks/install.yml`, porque Ansible busca `main.yml` por convención.

Cada directorio tiene un propósito específico:

| Directorio | Propósito |
|------------|-----------|
| `defaults/` | Variables orientadas al usuario con valores por defecto. Precedencia más baja. |
| `vars/` | Variables internas y constantes. Precedencia alta, difíciles de sobrescribir. |
| `tasks/` | La lista de tareas que ejecuta el rol. |
| `handlers/` | Handlers que las tareas pueden notificar. |
| `templates/` | Templates Jinja2 desplegados por `ansible.builtin.template`. |
| `files/` | Archivos estáticos desplegados por `ansible.builtin.copy`. |
| `meta/` | Metadatos del rol, dependencias y validación de argumentos. |

### Dividir Tareas en Componentes

Cuando un rol crece, divides `tasks/main.yml` en archivos de componentes y los incluyes:

```yaml
# tasks/main.yml
- name: Install packages
  ansible.builtin.include_tasks:
    file: "{{ role_path }}/tasks/install.yml"

- name: Configure the service
  ansible.builtin.include_tasks:
    file: "{{ role_path }}/tasks/configure.yml"

- name: Manage the service lifecycle
  ansible.builtin.include_tasks:
    file: "{{ role_path }}/tasks/service.yml"
```

Observa el prefijo `{{ role_path }}`. Esto es crítico porque asegura que la ruta se resuelva al rol correcto, incluso cuando un rol incluye a otro. Nunca uses rutas relativas como `tasks/install.yml` sin él.

!!! warning "Siempre usa `{{ role_path }}` para referencias a archivos"
    Las rutas relativas en `include_tasks`, `include_vars` y `template` se resuelven contra el rol *que incluye*, no necesariamente contra tu rol. Usa `{{ role_path }}/tasks/`, `{{ role_path }}/vars/` y `{{ role_path }}/templates/` para ser explícito.

## Convenciones de Nomenclatura

La nomenclatura es donde empiezan la mayoría de los problemas con roles. Cuando múltiples roles se ejecutan en el mismo play, sus variables comparten un único espacio de nombres. Si dos roles definen una variable llamada `packages`, una sobrescribirá a la otra.

La regla es simple: **prefija todo con el nombre del rol**.

### Prefijo de Variables

```yaml
# defaults/main.yml — CORRECTO
webserver_port: 80
webserver_document_root: /var/www/html
webserver_server_name: localhost

# defaults/main.yml — MAL (colisionara con otros roles)
port: 80
document_root: /var/www/html
server_name: localhost
```

Esto aplica a:

- Todas las variables en `defaults/main.yml`
- Todas las variables en `vars/main.yml`
- Todas las variables registradas (`register: webserver_config_result`)
- Todos los facts personalizados (`ansible.builtin.set_fact: webserver_detected_version: ...`)
- Todos los tags (`tags: webserver_install`)

### Prefijo de Variables Internas

Las variables internas del rol, no pensadas para que los usuarios las sobrescriban, llevan un prefijo de doble guión bajo:

```yaml
# vars/main.yml — constantes internas
__webserver_packages_default:
  - httpd
__webserver_service_name: httpd
__webserver_config_dir: /etc/httpd/conf
```

El doble guión bajo indica "esto es un detalle de implementación, no lo definas en tu inventario." Los usuarios configuran el rol a través de `defaults/main.yml`, no a través de estas variables internas.

### Nomenclatura de Handlers

Los handlers también necesitan el prefijo del rol para evitar colisiones. Usa una convención de nomenclatura que incluya el nombre del rol:

```yaml
# handlers/main.yml
- name: Validate webserver configuration
  ansible.builtin.command:
    cmd: "httpd -t"
  changed_when: false
  listen: "webserver_validate_config"

- name: Reload webserver
  ansible.builtin.service:
    name: "{{ __webserver_service_name }}"
    state: reloaded
  listen: "webserver_reload"
```

La directiva `listen` permite que las tareas notifiquen a los handlers por tema en lugar de por nombre exacto. Esto es especialmente útil en roles porque el nombre del handler puede ser descriptivo mientras que el valor de `listen` sigue un patrón estricto `nombrerol_acción`.

### Nombres de Roles

Los nombres de roles deben usar guiones bajos, nunca guiones:

```text
webserver     # CORRECTO
web_server    # CORRECTO
web-server    # MAL — los guiones rompen el empaquetado de colecciones
```

## defaults vs vars

Esta es una de las distinciones más importantes en el diseño de roles, y equivocarse causa problemas reales.

### `defaults/main.yml` -- La Interfaz de Usuario

Las variables en `defaults/main.yml` tienen la **precedencia más baja** en la jerarquía de variables de Ansible. Esto significa que pueden ser sobrescritas por casi cualquier cosa: variables de inventario, group vars, host vars, play vars, extra vars. Eso es exactamente lo que quieres para la configuración orientada al usuario.

Piensa en `defaults/main.yml` como la "API" de tu rol. Documenta cada parámetro que el usuario puede ajustar:

```yaml
# defaults/main.yml
webserver_port: 80
webserver_document_root: /var/www/html
webserver_server_name: localhost
webserver_service_enabled: true
webserver_max_connections: 256
# webserver_admin_email:
# webserver_packages:
```

Observa las variables comentadas al final. Son entradas que no tienen un valor por defecto seguro (como un email de administrador), así que el rol no define ninguno. Pero al listarlas aquí, los usuarios saben que estas opciones existen. Los comentarios sirven como documentación.

### `vars/main.yml` -- Constantes Internas

Las variables en `vars/main.yml` tienen **precedencia alta**: sobrescriben variables de inventario, group vars y la mayoría de otras fuentes. Solo las extra vars (`-e`) pueden sobrescribirlas.

Esto hace que `vars/main.yml` sea el lugar equivocado para valores por defecto orientados al usuario. Si pones `webserver_port: 80` en `vars/main.yml`, los usuarios no pueden sobrescribirlo desde su inventario. Necesitarían `-e webserver_port=8080` en cada ejecución, lo que derrota el propósito.

Usa `vars/main.yml` para valores que no deberían cambiar:

```yaml
# vars/main.yml — constantes internas
__webserver_packages_default:
  - httpd
__webserver_service_name: httpd
__webserver_config_dir: /etc/httpd/conf
__webserver_config_file: httpd.conf
```

Estos son detalles de implementación: el nombre del servicio, la ruta del directorio de configuración, la lista de paquetes por defecto. Los usuarios no deberían necesitar definirlos, y si los sobrescriben por accidente, suceden cosas malas.

!!! danger "Nunca pongas defaults orientados al usuario en `vars/main.yml`"
    La alta precedencia de `vars/` hace que las variables sean casi imposibles de sobrescribir desde el inventario. Siempre usa `defaults/main.yml` para cualquier cosa que los usuarios deban poder personalizar.

### Referencia Rápida

| | `defaults/main.yml` | `vars/main.yml` |
|---|---|---|
| **Precedencia** | La más baja (fácilmente sobrescrita) | Alta (difícil de sobrescribir) |
| **Propósito** | Configuración orientada al usuario | Constantes internas |
| **Nomenclatura** | `nombrerol_variable` | `__nombrerol_variable` |
| **Pueden sobrescribir los usuarios?** | Sí, desde inventario/group_vars | Solo con `-e` extra vars |
| **Contiene** | Valores por defecto sensatos, opciones documentadas | Nombres de servicios, rutas, valores internos |

## Qué Son las Colecciones?

Una colección es un paquete de distribución para contenido Ansible. Agrupa roles, plugins, módulos y documentación en un único artefacto con un namespace, una versión y dependencias declaradas.

Antes de las colecciones, compartir contenido Ansible significaba distribuir roles independientes a través de Ansible Galaxy. Esto funcionaba, pero tenía problemas: sin namespacing (dos personas podían crear un rol llamado `nginx`), sin gestión de dependencias entre roles, y sin forma de agrupar roles con módulos o plugins personalizados.

Las colecciones resuelven todo esto. Una colección tiene un **namespace** y un **nombre** (como `parasoltech.infrastructure`) que garantiza unicidad. Incluye un manifiesto `galaxy.yml` que declara dependencias y versionado. Y puede contener cualquier combinación de roles, módulos, plugins y documentación.

### Estructura de una Colección

```text
parasoltech/infrastructure/
  galaxy.yml            # Manifiesto de la coleccion (nombre, version, deps)
  README.md             # Documentacion de la coleccion
  LICENSE               # Archivo de licencia
  meta/
    runtime.yml         # Requisito minimo de version de Ansible
  plugins/              # Modulos personalizados, filtros, etc.
  roles/
    webserver/          # Los roles van aqui
      defaults/main.yml
      tasks/main.yml
      ...
  tests/                # Tests a nivel de coleccion
  docs/                 # Documentacion adicional
```

El archivo clave es `galaxy.yml`: es la tarjeta de identidad de la colección.

## Scaffolding con ansible-creator

No necesitas crear todos estos directorios y archivos a mano. La herramienta CLI `ansible-creator` genera todo el scaffolding por ti.

### Crear una Colección

```bash
ansible-creator init collection parasoltech.infrastructure \
  ~/ansible/collections/parasoltech/infrastructure
```

Esto crea la estructura completa de directorios con archivos plantilla para `galaxy.yml`, `README.md`, `LICENSE`, `meta/runtime.yml`, y directorios placeholder para plugins, roles y tests.

La sintaxis general es:

```text
ansible-creator init collection <namespace>.<nombre> <ruta-destino>
```

!!! tip "Integración con VS Code"
    Si usas la extensión de Ansible para VS Code, también puedes crear el scaffolding de colecciones a través de un asistente gráfico. Haz clic en el icono de Ansible en la barra lateral, luego selecciona **Collection project**. El asistente llama a `ansible-creator` detrás de escena y produce el mismo resultado.

!!! note "Y `ansible-galaxy init`?"
    También puedes encontrar `ansible-galaxy collection init` y `ansible-galaxy role init` para crear el scaffolding de colecciones y roles. Estos comandos funcionan, pero `ansible-creator` es la herramienta más nueva y recomendada porque genera un scaffolding de proyecto más completo. Además de la estructura básica de directorios, `ansible-creator` incluye configuraciones de devcontainer, workflows de CI, infraestructura de testing y boilerplate adicional que `ansible-galaxy init` no proporciona. Para proyectos nuevos, prefiere `ansible-creator`.

### Crear un Rol Dentro de una Colección

Para agregar un rol a una colección existente:

```bash
cd ~/ansible/collections/parasoltech/infrastructure
ansible-creator init role webserver --path roles/webserver
```

Esto crea la estructura de directorios del rol dentro del directorio `roles/` de la colección, incluyendo `defaults/main.yml`, `tasks/main.yml`, `handlers/main.yml`, `meta/main.yml` y placeholders para templates.

### Qué Produce ansible-creator

Después del scaffolding, la colección se ve así:

```text
parasoltech/infrastructure/
  galaxy.yml
  README.md
  LICENSE
  meta/
    runtime.yml
  plugins/
  roles/
    webserver/
      defaults/
        main.yml
      handlers/
        main.yml
      meta/
        main.yml
      tasks/
        main.yml
      templates/
      vars/
        main.yml
      README.md
  tests/
  docs/
```

Todos los archivos vienen con valores por defecto sensatos que personalizas para tu caso de uso. El `galaxy.yml` necesita tu namespace y descripción; el `defaults/main.yml` del rol necesita tus variables; el `tasks/main.yml` necesita tu lógica de automatización.

## Configurar galaxy.yml

El archivo `galaxy.yml` es el manifiesto de tu colección. Este es el de `parasoltech.infrastructure`:

```yaml
---
namespace: parasoltech
name: infrastructure
version: 1.0.0
readme: README.md
authors:
  - Parasol Tech Platform Team <platform@parasol.example>
description: Infrastructure automation collection for Parasol Tech
license_file: LICENSE
tags:
  - infrastructure
  - linux
dependencies:
  "ansible.posix": ">=1.0.0"
build_ignore:
  - .gitignore
  - .venv
  - collections
  - .tox
  - .ade
```

Cada campo tiene un propósito específico:

| Campo | Propósito |
|-------|-----------|
| `namespace` | El nombre de la organización o equipo. Inmutable después de publicar. |
| `name` | El nombre de la colección. Junto con namespace, forma el FQCN. |
| `version` | Versión semántica (ver [Versionado Semántico](#versionado-semantico) más abajo). |
| `readme` | Ruta al archivo README. |
| `authors` | Lista de autores con email opcional. |
| `description` | Descripción corta para resultados de búsqueda en Galaxy/Hub. |
| `license_file` | Ruta al archivo de licencia. |
| `tags` | Tags de descubrimiento para Galaxy/Hub. Las categorías disponibles incluyen `application`, `cloud`, `database`, `infrastructure`, `linux`, `monitoring`, `networking`, `security`, `tools`, `windows`, entre otras. |
| `dependencies` | Otras colecciones que esta necesita, con restricciones de versión. |
| `build_ignore` | Archivos y directorios a excluir al construir el artefacto de la colección. |

### Dependencias

El campo `dependencies` declara qué otras colecciones necesita la tuya. Las restricciones de versión usan sintaxis estilo pip:

```yaml
dependencies:
  "ansible.posix": ">=1.0.0"       # 1.0.0 o superior
  "ansible.utils": "*"             # cualquier version
  "community.general": ">=5.0,<7"  # 5.x o 6.x, no 7.x
```

Cuando alguien instala tu colección, `ansible-galaxy` instala automáticamente estas dependencias también.

### Build Ignore

El campo `build_ignore` mantiene los artefactos de desarrollo fuera del paquete publicado. Cuando `ade` gestiona tu colección, crea directorios `.venv`, `collections` y `.ade` dentro de la raíz de la colección. Son útiles durante el desarrollo pero nunca deben incluirse en el tarball distribuido:

```yaml
build_ignore:
  - .gitignore
  - .venv
  - collections
  - .tox
  - .ade
```

## Gestión de Dependencias con ade

La herramienta **Ansible Development Environment** (`ade`) gestiona el espacio de trabajo de desarrollo de tu colección. Maneja:

- Crear entornos virtuales Python aislados
- Instalar tu colección en **modo editable** (los cambios surten efecto inmediatamente)
- Resolver e instalar dependencias de colecciones declaradas en `galaxy.yml`
- Instalar dependencias Python desde `requirements.txt` y `test-requirements.txt`
- Rastrear requisitos de paquetes a nivel de sistema

### Instalar Tu Colección para Desarrollo

Navega a la raíz de tu colección y ejecuta:

```bash
cd ~/ansible/collections/parasoltech/infrastructure
ade install -e .
```

El flag `-e .` significa **instalación editable**: `ade` crea un symlink desde el entorno virtual hacia tu directorio de trabajo. Cuando editas archivos en la colección, los cambios son inmediatamente visibles para Ansible sin reinstalar.

La salida típica se ve así:

```text
$ ade install -e .
    Note: Created virtual environment: .venv
    Note: Installed collections include: ansible.posix and parasoltech.infrastructure
    Note: All python requirements are installed.
    Note: All required system packages are installed.
```

!!! note "Instalación editable vs regular"
    Sin `-e`, `ade install .` copia la colección al entorno virtual. Los cambios en tus archivos fuente no se reflejan hasta que reinstales. Siempre usa `-e` durante el desarrollo.

### Ver el Árbol de Dependencias

Para ver qué ha instalado `ade` y el grafo completo de dependencias:

```bash
ade tree -v
```

Esto muestra tu colección, sus dependencias y las dependencias de estas. Es útil para entender qué se incluye y para solucionar conflictos de versiones.

### Manejar Dependencias de Sistema

Algunas colecciones requieren paquetes a nivel de sistema (bibliotecas C, bindings de Python compilados desde C, etc.). Cuando `ade` detecta paquetes de sistema faltantes, te dice qué instalar:

```text
$ ade install -e .
 Warning: Required system packages are missing. Please use the system
          package manager to install them.
          - python3-cffi
          - python3-cryptography
```

Instala los paquetes listados con tu gestor de paquetes del sistema (`dnf install`, `apt install`, etc.), luego vuelve a ejecutar `ade install -e .`.

!!! warning "Entornos inmutables"
    En entornos basados en contenedores como devcontainers o Red Hat Dev Spaces, no puedes instalar paquetes del sistema en tiempo de ejecución con `dnf install`. Si `ade` reporta paquetes de sistema faltantes, el enfoque recomendado es agregarlos a la imagen del contenedor:

    - **Devcontainer**: Agrega un `postCreateCommand` o un `Dockerfile` personalizado en `.devcontainer/` para instalar los paquetes durante la construcción del contenedor.
    - **Dev Spaces**: Agrega los paquetes a la imagen del componente de contenedor en `devfile.yaml`.
    - **EE personalizado**: Inclúyelos en las dependencias de sistema de tu `execution-environment.yml`.

    La imagen base `community-ansible-dev-tools` ya incluye las dependencias de sistema más comunes.

## Validación de Argumentos

Cada rol debería validar sus entradas. Si un usuario pasa `webserver_port: "ochenta"` en lugar de un entero, el rol debería fallar inmediatamente con un mensaje claro, no a mitad de camino cuando un template renderiza `Listen ochenta` y el servidor web se niega a arrancar.

Ansible proporciona validación de argumentos a través de `meta/argument_specs.yml`. Este archivo declara el tipo, valor por defecto y restricciones para cada entrada del rol.

### Escribir argument_specs.yml

Esta es la especificación de argumentos para el rol `webserver`:

```yaml
---
argument_specs:
  main:
    short_description: Install and configure a web server
    description:
      - Install web server packages, deploy configuration from
        a template, deploy a default index page, and manage the
        service lifecycle.
    options:
      webserver_port:
        type: int
        default: 80
        description: The HTTP port the web server listens on.
      webserver_document_root:
        type: str
        default: /var/www/html
        description: >-
          The document root directory where web content is served from.
      webserver_server_name:
        type: str
        default: localhost
        description: >-
          The server name used in the virtual host configuration.
      webserver_service_enabled:
        type: bool
        default: true
        description: >-
          Whether to start and enable the web server service.
      webserver_max_connections:
        type: int
        default: 256
        description: >-
          The maximum number of simultaneous client connections.
      webserver_admin_email:
        type: str
        required: false
        description: >-
          The admin email shown in server error pages.
          If not set, the server default is used.
      webserver_packages:
        type: list
        elements: str
        required: false
        description: >-
          List of packages to install. If not provided, the role
          uses platform-specific defaults.
```

La clave `main` corresponde al punto de entrada, `tasks/main.yml`. Si tu rol tiene múltiples puntos de entrada (por ejemplo, `tasks/install.yml` y `tasks/configure.yml` llamados por separado), cada uno tiene su propia entrada bajo `argument_specs`.

### Qué Detecta la Validación

Cuando Ansible carga un rol con argument specs, verifica:

- **Tipo**: Es `webserver_port` realmente un entero? Es `webserver_service_enabled` un booleano?
- **Requerido**: Se proporcionó `webserver_port`? (Si no existe un valor por defecto y `required: true`)
- **Opciones**: Es el valor uno de un conjunto permitido? (Usa `choices: [a, b, c]`)
- **Elementos**: Para tipos lista, qué tipo debería ser cada elemento?

Si la validación falla, Ansible se detiene antes de ejecutar cualquier tarea y reporta el error. Este es un comportamiento de fallo rápido: capturando errores al inicio en lugar de a mitad del rol.

### La Conexión con defaults/main.yml

Observa que los valores por defecto en `argument_specs.yml` coinciden con `defaults/main.yml`. Siempre deben estar de acuerdo. El `argument_specs.yml` es el contrato formal; `defaults/main.yml` es donde los valores se definen realmente. Si divergen, el comportamiento se vuelve confuso.

!!! tip "Mantén defaults y argument specs sincronizados"
    Cuando agregues una nueva variable a `defaults/main.yml`, agrega la entrada correspondiente en `meta/argument_specs.yml`. Cuando cambies un valor por defecto, actualiza ambos archivos.

## Fully Qualified Collection Names (FQCNs)

Un Fully Qualified Collection Name identifica cualquier pieza de contenido dentro de una colección. El formato es:

```text
<namespace>.<coleccion>.<nombre_contenido>
```

Para módulos:

```yaml
# FQCN — siempre correcto, nunca ambiguo
- name: Install packages
  ansible.builtin.package:
    name: httpd
    state: present

# Nombre corto — funciona solo si ansible.builtin esta en la ruta de busqueda
- name: Install packages
  package:
    name: httpd
    state: present
```

Para roles:

```yaml
# Usar un rol de coleccion con FQCN
- name: Deploy web servers
  hosts: webservers

  roles:
    - role: parasoltech.infrastructure.webserver
```

### Por Qué Importan los FQCNs

Los nombres cortos como `copy`, `template` o `package` funcionan porque Ansible busca en un conjunto predeterminado de colecciones (empezando por `ansible.builtin`). Pero cuando agregas colecciones comunitarias o personalizadas, los nombres cortos se vuelven ambiguos. Si tanto `ansible.builtin` como `community.general` proporcionan un módulo con el mismo nombre, cuál se ejecuta?

Los FQCNs eliminan esta ambigüedad. `ansible.builtin.copy` siempre significa el módulo copy de `ansible.builtin`. `community.general.filesystem` siempre significa el módulo filesystem de `community.general`. Nunca hay duda.

A lo largo de este curso hemos usado FQCNs desde el principio: `ansible.builtin.template`, `ansible.builtin.service`, `ansible.builtin.debug`. Esto es intencional. Es un hábito que vale la pena construir temprano, incluso cuando los nombres cortos funcionarían.

## Versionado Semántico

Las colecciones usan **versionado semántico** (SemVer) para comunicar el impacto de los cambios. El número de versión tiene tres partes:

```text
MAJOR.MINOR.PATCH
  1  .  0  .  0
```

| Parte | Cuándo incrementar | Ejemplo |
|-------|-------------------|---------|
| **MAJOR** | Cambios incompatibles (variables eliminadas, comportamiento cambiado) | 1.0.0 -> 2.0.0 |
| **MINOR** | Nuevas características (nuevos roles, nuevas variables, nuevos módulos) | 1.0.0 -> 1.1.0 |
| **PATCH** | Corrección de errores (sin nuevas características, sin cambios incompatibles) | 1.0.0 -> 1.0.1 |

Para la colección `parasoltech.infrastructure`:

- Agregar un nuevo rol `database`? Incrementa MINOR: `1.0.0` -> `1.1.0`
- Corregir un error en un template del rol `webserver`? Incrementa PATCH: `1.0.0` -> `1.0.1`
- Renombrar `webserver_port` a `webserver_listen_port`? Eso es un cambio incompatible. Incrementa MAJOR: `1.0.0` -> `2.0.0`

El versionado semántico permite que los consumidores especifiquen restricciones de dependencia con confianza. Si tu colección está en `1.3.2`, un consumidor que declare `"parasoltech.infrastructure": ">=1.0.0,<2.0.0"` sabe que obtendrá correcciones de errores y nuevas características pero nunca cambios incompatibles.

## Ansible Galaxy y Automation Hub

**Ansible Galaxy** ([galaxy.ansible.com](https://galaxy.ansible.com)) es el registro público comunitario para colecciones Ansible. Cualquiera puede explorar, descargar y publicar colecciones.

**Automation Hub** es el equivalente empresarial: un registro curado y soportado incluido con Ansible Automation Platform. Las organizaciones usan instancias privadas de Automation Hub para distribuir colecciones internas (como `parasoltech.infrastructure`).

!!! info "Automation Hub: dos versiones"
    Red Hat ofrece dos versiones de Automation Hub:

    - **Ansible Automation Hub** (console.redhat.com): Un servicio alojado en la nube híbrida que proporciona colecciones certificadas y validadas por Red Hat. Disponible para todos los suscriptores de AAP.
    - **Private Automation Hub**: Una instancia auto-alojada que ejecutas dentro de tu organización para distribuir colecciones internas, curar contenido aprobado y alojar imágenes de contenedor para Execution Environments.

    La mayoría de las organizaciones usan ambas: el hub alojado para contenido certificado upstream y una instancia privada para automatización interna.

### Instalar Colecciones desde Galaxy

```bash
# Instalar una coleccion especifica
ansible-galaxy collection install community.general

# Instalar una version especifica
ansible-galaxy collection install community.general:9.0.0

# Instalar desde un archivo de requisitos
ansible-galaxy collection install -r requirements.yml
```

Un archivo `requirements.yml` lista múltiples colecciones con restricciones de versión:

```yaml
---
collections:
  - name: ansible.posix
    version: ">=1.0.0"
  - name: community.general
    version: ">=9.0.0"
```

### Construir una Colección para Distribución

Para construir tu colección en un tarball instalable:

```bash
cd ~/ansible/collections/parasoltech/infrastructure
ansible-galaxy collection build
```

Esto produce un archivo como `parasoltech-infrastructure-1.0.0.tar.gz` que puede instalarse con `ansible-galaxy collection install` o subirse a Galaxy o Automation Hub.

### Publicar en Galaxy

```bash
# Publicar en Galaxy (requiere una API key de galaxy.ansible.com)
ansible-galaxy collection publish parasoltech-infrastructure-1.0.0.tar.gz
```

Para distribución interna en Parasol Tech, la CoP publica en un Automation Hub privado en su lugar. El flujo de trabajo es similar: construir el tarball, luego enviarlo al Hub.

## Construyendo el Rol webserver

Ahora construyamos el rol `parasoltech.infrastructure.webserver` paso a paso. Este rol instala un servidor web, despliega un archivo de configuración desde un template, crea una página index por defecto y gestiona el ciclo de vida del servicio.

### defaults/main.yml

Las variables orientadas al usuario definen lo que los consumidores del rol pueden personalizar:

```yaml
---
# El puerto HTTP en el que escucha el servidor web
webserver_port: 80

# La raiz de documentos donde se sirve el contenido web
webserver_document_root: /var/www/html

# El nombre del servidor usado en la configuracion del virtual host
webserver_server_name: localhost

# Si iniciar y habilitar el servicio del servidor web
webserver_service_enabled: true

# El numero maximo de conexiones simultaneas de clientes
webserver_max_connections: 256

# El email de administrador mostrado en paginas de error del servidor
# webserver_admin_email:

# Paquetes a instalar (sobrescribible por plataforma via vars/)
# webserver_packages:
```

Cada variable tiene el prefijo `webserver_`. Las dos variables comentadas (`webserver_admin_email`, `webserver_packages`) no tienen un valor por defecto seguro, así que se listan pero no se definen. Los usuarios saben que estas opciones existen leyendo este archivo.

### vars/main.yml

Constantes internas que no deberían sobrescribirse:

```yaml
---
__webserver_packages_default:
  - httpd
__webserver_service_name: httpd
__webserver_config_dir: /etc/httpd/conf
__webserver_config_file: httpd.conf
```

El prefijo de doble guión bajo marca estas como internas. El nombre del servicio, el directorio de configuración y los paquetes por defecto son detalles de implementación que los usuarios no deberían necesitar cambiar.

### tasks/main.yml

La lista de tareas une todo. Observa cómo usa patrones de cada módulo anterior: gestión de paquetes (Módulo 2), templates con backup (Módulo 5), handlers (Módulo 5) y lógica basada en variables (Módulo 4):

```yaml
---
- name: Install web server packages
  ansible.builtin.package:
    name: "{{ webserver_packages | default(__webserver_packages_default) }}"
    state: present

- name: Ensure document root exists
  ansible.builtin.file:
    path: "{{ webserver_document_root }}"
    state: directory
    owner: root
    group: root
    mode: "0755"

- name: Deploy web server configuration
  ansible.builtin.template:
    src: "{{ role_path }}/templates/webserver.conf.j2"
    dest: "{{ __webserver_config_dir }}/{{ __webserver_config_file }}"
    owner: root
    group: root
    mode: "0644"
    backup: true
  notify:
    - webserver_validate_config
    - webserver_reload

- name: Deploy default index page
  ansible.builtin.template:
    src: "{{ role_path }}/templates/index.html.j2"
    dest: "{{ webserver_document_root }}/index.html"
    owner: root
    group: root
    mode: "0644"
    backup: true

- name: Ensure web server service is in the desired state
  ansible.builtin.service:
    name: "{{ __webserver_service_name }}"
    state: "{{ webserver_service_enabled | ternary('started', 'stopped') }}"
    enabled: "{{ webserver_service_enabled }}"
```

Patrones clave a observar:

- **`{{ role_path }}/templates/`** para rutas explícitas de templates
- **`backup: true`** en cada tarea de template/copy
- **FQCNs** en todo (`ansible.builtin.package`, no `package`)
- **Notificación de handlers** usa los tópicos `listen` (`webserver_validate_config`, `webserver_reload`)
- **`| default(__webserver_packages_default)`** permite a los usuarios sobrescribir paquetes mientras proporciona un respaldo integrado

### handlers/main.yml

```yaml
---
- name: Validate webserver configuration
  ansible.builtin.command:
    cmd: "httpd -t"
  changed_when: false
  listen: "webserver_validate_config"

- name: Reload webserver
  ansible.builtin.service:
    name: "{{ __webserver_service_name }}"
    state: reloaded
  listen: "webserver_reload"

- name: Restart webserver
  ansible.builtin.service:
    name: "{{ __webserver_service_name }}"
    state: restarted
  listen: "webserver_restart"
```

Observa `changed_when: false` en el comando de validación. Es una verificación de solo lectura, así que nunca debería reportar un cambio.

### Templates

El template de configuración del servidor web (`webserver.conf.j2`) usa patrones del Módulo 5:

```jinja
{{ ansible_managed | comment }}
#
# Web server configuration for {{ webserver_server_name }}

Listen {{ webserver_port }}

ServerName {{ webserver_server_name }}
DocumentRoot "{{ webserver_document_root }}"

MaxRequestWorkers {{ webserver_max_connections }}

{% if webserver_admin_email is defined %}
ServerAdmin {{ webserver_admin_email }}
{% endif %}

<Directory "{{ webserver_document_root }}">
    AllowOverride None
    Require all granted
</Directory>

ErrorLog "logs/error_log"
CustomLog "logs/access_log" combined
```

Y un simple `index.html.j2`:

```jinja
{{ ansible_managed | comment('<!--', '-->') }}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ webserver_server_name }}</title>
</head>
<body>
    <h1>Welcome to {{ webserver_server_name }}</h1>
    <p>This page is managed by Ansible.</p>
    <p>Served by the <code>parasoltech.infrastructure.webserver</code> role.</p>
</body>
</html>
```

Observa cómo `{{ ansible_managed | comment('<!--', '-->') }}` usa delimitadores de comentario personalizados para HTML. El filtro `| comment` acepta argumentos para cambiar la sintaxis de comentario del `#` predeterminado.

### Usar el Rol en un Playbook

Un playbook que usa este rol es corto porque la complejidad está dentro del rol:

```yaml
---
- name: Deploy web servers
  hosts: webservers

  roles:
    - role: parasoltech.infrastructure.webserver
      vars:
        webserver_port: 8080
        webserver_server_name: web.parasol.example
        webserver_document_root: /var/www/parasol
        webserver_admin_email: admin@parasol.example
```

El playbook es una lista de roles, no una lista de tareas. Toda la lógica -- instalar paquetes, desplegar templates, gestionar servicios -- vive dentro del rol. El playbook solo dice *qué* aplicar y *dónde*.

## Ejercicios

### Ejercicio 1: Explorar la Estructura de la Colección

Navega a la colección compañera y examina la estructura:

```bash
cd ansible/collections/parasoltech/infrastructure
find . -type f | sort
```

Abre los archivos clave y verifica:

1. `galaxy.yml` tiene el namespace, nombre y versión correctos
2. `roles/webserver/defaults/main.yml` tiene todas las variables con prefijo `webserver_`
3. `roles/webserver/vars/main.yml` tiene variables internas con prefijo `__webserver_`
4. `roles/webserver/meta/argument_specs.yml` coincide con los defaults

### Ejercicio 2: Crear una Nueva Colección con ansible-creator

Crea una segunda colección usando `ansible-creator`:

```bash
ansible-creator init collection parasoltech.monitoring \
  ~/ansible/collections/parasoltech/monitoring
```

Explora los archivos generados. Compara la estructura con la colección `parasoltech.infrastructure`. Observa cómo `ansible-creator` genera el mismo esquema cada vez. Scaffolding consistente significa colecciones consistentes.

### Ejercicio 3: Usar ade para Gestión de Dependencias

Instala la colección `parasoltech.infrastructure` en modo editable:

```bash
cd ansible/collections/parasoltech/infrastructure
ade install -e .
```

Verifica el árbol de dependencias:

```bash
ade tree -v
```

Deberías ver `ansible.posix` listado como dependencia (declarado en `galaxy.yml`).

### Ejercicio 4: Agregar Validación de Argumentos

Agrega una nueva variable al rol `webserver`:

1. Agrega `webserver_log_level` a `defaults/main.yml` con un valor por defecto de `warn`
2. Agrega la entrada correspondiente en `meta/argument_specs.yml` con `type: str` y `choices: [debug, info, notice, warn, error, crit]`
3. Usa la nueva variable en el template `webserver.conf.j2`

Prueba que la validación funciona pasando un valor inválido:

```bash
ansible-playbook -e "webserver_log_level=invalid" tu-playbook.yml
```

Ansible debería rechazar el valor antes de ejecutar cualquier tarea.

### Ejercicio 5: Construir la Colección

Construye la colección en un tarball distribuible:

```bash
cd ~/ansible/collections/parasoltech/infrastructure
ansible-galaxy collection build
```

Examina el archivo `.tar.gz` resultante. Observa que los directorios listados en `build_ignore` (`.venv`, `collections`, `.tox`, `.ade`) no están incluidos en el archivo.

## Resumen

En este módulo:

- Aprendiste la estructura de directorios de un rol y cómo Ansible ensambla tareas, defaults, vars, handlers, templates y metadatos en una unidad reutilizable
- Entendiste la diferencia crítica entre `defaults/main.yml` (orientado al usuario, baja precedencia) y `vars/main.yml` (interno, alta precedencia)
- Aplicaste convenciones de nomenclatura: prefijar todas las variables del rol con el nombre del rol, prefijar variables internas con doble guión bajo, nunca usar guiones en nombres de roles
- Creaste validación de argumentos con `meta/argument_specs.yml` para fallar rápido ante entradas incorrectas
- Creaste el scaffolding de una colección y rol con `ansible-creator` y gestionaste el entorno de desarrollo con `ade`
- Configuraste `galaxy.yml` con metadatos, dependencias, versión y reglas de build ignore
- Usaste Fully Qualified Collection Names para referenciar contenido de forma inequívoca
- Entendiste el versionado semántico y cómo comunica el impacto de los cambios

La CoP en Parasol Tech ahora tiene un estándar: toda automatización reutilizable va a la colección `parasoltech.infrastructure` con roles correctamente nombrados, validados y documentados. El equipo de base de datos instala la colección y usa el rol `webserver` sin copiar un solo archivo. Cuando el equipo de plataforma corrige un error, incrementan la versión patch y cada consumidor obtiene la corrección en su próxima instalación.

## Próximos Pasos

Siguiente: [Módulo 7 -- Testing de tu Automatización](7-testing-your-automation.md)
