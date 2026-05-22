# Módulo 2: Tu Primer Playbook

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Describir la anatomía de un playbook (plays, tasks, módulos)
- Escribir y ejecutar un playbook simple
- Usar `ansible-navigator` para ejecutar e inspeccionar ejecuciones de playbooks
- Explicar la idempotencia y verificarla con el modo check y el modo diff

## La Historia Hasta Ahora

Lionel ha ejecutado algunos comandos ad-hoc y ve el potencial. Pero los comandos individuales no son repetibles: si Lionel necesita instalar los mismos tres paquetes en un nuevo servidor el mes que viene, tendrá que recordar los comandos exactos de memoria o buscarlos en una wiki. Lo que se necesita es una forma de definir un conjunto de tareas una vez y ejecutarlas de manera confiable, siempre.

Es hora de escribir un playbook.

## Anatomía de un Playbook

Un **playbook** es un archivo YAML que describe el estado deseado de uno o más sistemas. Es la unidad fundamental de automatización reutilizable en Ansible.

Un playbook contiene uno o más **plays**. Cada play apunta a un conjunto de hosts y define una lista ordenada de **tasks** (tareas) para ejecutar en esos hosts. Cada task invoca un **módulo**, los mismos módulos que usaste con comandos ad-hoc en el Módulo 1.

Esta es la estructura general:

```text
Playbook (archivo YAML)
  └── Play 1
  │     ├── hosts: qué máquinas apuntar
  │     ├── become: si escalar privilegios
  │     └── tasks:
  │           ├── Task 1 → invoca un módulo
  │           ├── Task 2 → invoca un módulo
  │           └── Task 3 → invoca un módulo
  └── Play 2
        ├── hosts: un conjunto diferente de máquinas
        └── tasks:
              └── Task 1 → invoca un módulo
```

Terminología clave:

| Término | Definición |
|---------|-----------|
| **Playbook** | Un archivo YAML que contiene uno o más plays |
| **Play** | Una asociación de hosts con tasks: "en estos hosts, hacer estas cosas" |
| **Task** | Una acción individual que invoca un módulo con parámetros específicos |
| **Módulo** | Una unidad de código que realiza una operación específica (instalar un paquete, copiar un archivo, gestionar un servicio) |

!!! info "Un play vs. muchos plays"
    Los playbooks simples a menudo contienen un solo play. A medida que tu automatización crece, usarás múltiples plays para apuntar a diferentes grupos de hosts en el mismo playbook. Por ejemplo, un play para configurar el servidor de base de datos y otro para configurar los servidores web.

## Fundamentos de YAML para Ansible

Los playbooks de Ansible están escritos en YAML (YAML Ain't Markup Language). Si nunca has trabajado con YAML, aquí están los conceptos esenciales que necesitas para Ansible.

### Indentación

YAML usa indentación para representar estructura, como Python, pero con **solo espacios, nunca tabulaciones**. Ansible usa **indentación de 2 espacios** por convención.

```yaml
# Correcto: indentación de 2 espacios
- name: Install packages
  ansible.builtin.package:
    name: curl
    state: present
```

```yaml
# Incorrecto: indentación inconsistente causará un error de sintaxis
- name: Install packages
   ansible.builtin.package:
      name: curl
```

### Listas

Las listas usan un guion seguido de un espacio (`- `). Los elementos de la lista se indentan bajo su clave padre:

```yaml
# Una lista de paquetes
name:
  - tree
  - curl
  - jq
```

### Cadenas de texto

La mayoría de las cadenas en YAML no necesitan comillas. Usa comillas cuando un valor contiene caracteres especiales o podría malinterpretarse:

```yaml
# No necesita comillas
name: Install packages

# Necesita comillas: los dos puntos confundirían al parser
message: "Status: completed"
```

### Booleanos

YAML soporta varias formas de booleanos, pero en Ansible siempre usamos `true` y `false` en minúsculas:

```yaml
# Correcto
become: true
enabled: false

# Incorrecto -- no uses estas formas
become: yes
enabled: No
become: True
```

!!! warning "Siempre usa `true`/`false`"
    YAML acepta `yes`, `no`, `True`, `False` y otras variantes como booleanos. Ansible los entenderá, pero `ansible-lint` marcará cualquier cosa que no sea `true`/`false`. Sé consistente desde el principio.

### Documentos

Un archivo YAML comienza con tres guiones (`---`). Esto marca el inicio de un documento YAML:

```yaml
---
- name: My first play
  hosts: localhost
  tasks: []
```

Los `---` son opcionales pero se consideran buena práctica. Los verás al inicio de cada playbook en este curso.

## Escribiendo Tu Primer Playbook

Recorramos un playbook real línea por línea. Abre el archivo `ansible/playbooks/module-02/install-packages.yml`:

```yaml
---
# Module 2 - Install common packages on localhost
# This playbook demonstrates the ansible.builtin.package module
# to install packages in a distribution-agnostic way.

- name: Install common utility packages
  hosts: localhost
  connection: local
  become: true

  tasks:
    - name: Install utility packages
      ansible.builtin.package:
        name:
          - tree
          - curl
          - jq
        state: present
```

Esto es lo que hace cada parte:

**`---`**: marca el inicio del documento YAML.

**`# Module 2 - ...`**: comentarios. Los comentarios en YAML comienzan con `#` y son ignorados por Ansible.

**`- name: Install common utility packages`**: el inicio de un **play**. El guion indica que este es el primer elemento de una lista (un playbook es una lista de plays). El `name` le da al play una descripción legible que aparece en la salida cuando lo ejecutas.

**`hosts: localhost`**: indica a Ansible qué hosts apunta este play. Aquí apuntamos solo a `localhost`, la máquina en la que estamos trabajando.

**`connection: local`**: indica a Ansible que ejecute las tareas directamente en la máquina local en lugar de conectarse por SSH. Esto es lo que quieres cuando apuntas a localhost.

**`become: true`**: indica a Ansible que escale privilegios (equivalente a `sudo`). Instalar paquetes requiere acceso root, así que lo necesitamos.

**`tasks:`**: comienza la lista de tareas para este play.

**`- name: Install utility packages`**: el inicio de una **task**. Cada task debería tener un nombre descriptivo en forma imperativa; te dice qué hace la task cuando lees la salida.

**`ansible.builtin.package:`**: el **módulo** que usa esta task. `ansible.builtin.package` es un módulo genérico de gestión de paquetes que funciona en diferentes distribuciones de Linux (llama a `dnf` en Fedora/RHEL, `apt` en Debian/Ubuntu, etc.). Nota que usamos el Fully Qualified Collection Name.

**`name:` (bajo el módulo)**: un parámetro del módulo `package` que especifica qué paquetes instalar. Pasamos una lista de tres paquetes.

**`state: present`**: otro parámetro del módulo. `present` significa "asegúrate de que estos paquetes estén instalados". Si ya están instalados, Ansible no hace nada. Si faltan, Ansible los instala.

!!! tip "Por qué `ansible.builtin.package` en lugar de `ansible.builtin.dnf`?"
    El módulo `package` detecta automáticamente el gestor de paquetes del sistema y llama al correcto. Esto hace tu playbook portable entre distribuciones. Usa módulos específicos de distribución (`dnf`, `apt`) solo cuando necesites funcionalidades específicas de ese gestor de paquetes.

### El Otro Playbook de Acompañamiento

El directorio `ansible/playbooks/module-02/` también contiene el playbook `create-files.yml` para practicar.

**`create-files.yml`** demuestra la creación de directorios y archivos:

```yaml
---
- name: Create directories and files
  hosts: localhost
  connection: local

  tasks:
    - name: Create project directory
      ansible.builtin.file:
        path: ~/ansible-demo
        state: directory
        mode: "0755"

    - name: Create logs subdirectory
      ansible.builtin.file:
        path: ~/ansible-demo/logs
        state: directory
        mode: "0755"

    - name: Create a welcome file
      ansible.builtin.copy:
        dest: ~/ansible-demo/README.txt
        content: |
          Welcome to Ansible!
          This file was created by an Ansible playbook.
        mode: "0644"

    - name: Create an application config file
      ansible.builtin.copy:
        dest: ~/ansible-demo/app.conf
        content: |
          # Application configuration
          app_name=demo
          log_level=info
          log_dir=~/ansible-demo/logs
        mode: "0644"
```

Nota que este playbook no usa `become: true` porque estamos escribiendo en el directorio home del usuario, lo cual no requiere privilegios de root.

El módulo `ansible.builtin.file` gestiona archivos y directorios. Con `state: directory`, crea un directorio. El módulo `ansible.builtin.copy` crea archivos con contenido específico usando el parámetro `content`.

!!! info "Gestión de servicios"
    La gestión de servicios con `ansible.builtin.service` funciona en sistemas con un sistema de inicio (systemd). En un entorno de contenedor como el devcontainer, los servicios no están disponibles. Usarás la gestión de servicios en módulos posteriores cuando trabajes con hosts reales o máquinas virtuales.

## Ejecutando Playbooks con ansible-navigator

En el Módulo 1 ejecutaste comandos ad-hoc con `ansible`. Para playbooks, usaremos **`ansible-navigator`**, una herramienta que proporciona una interfaz de usuario de texto enriquecida (TUI) para ejecutar e inspeccionar contenido de Ansible.

### Por qué ansible-navigator?

`ansible-navigator` reemplaza al antiguo comando `ansible-playbook` y añade:

- Una TUI interactiva para explorar resultados de plays y tasks
- La capacidad de ejecutar playbooks dentro de Execution Environments (imágenes de contenedor con todas las dependencias incluidas)
- Una forma estándar de inspeccionar contenido de automatización

Todavía puedes usar `ansible-playbook` directamente, y `ansible-navigator` lo llama internamente, pero la TUI facilita mucho la exploración de resultados.

### Ejecutando un Playbook

Navega al directorio `ansible/` (donde vive `ansible.cfg`) y ejecuta:

```bash
cd ansible
ansible-navigator run playbooks/module-02/install-packages.yml --mode stdout
```

La opción `--mode stdout` ejecuta el playbook en modo de salida estándar: la salida va directamente a tu terminal, similar a `ansible-playbook`. Esta es la forma más simple de ejecutar un playbook.

Deberías ver una salida como esta:

```text
PLAY [Install common utility packages] ****************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [Install utility packages] ************************************************
changed: [localhost]

PLAY RECAP *********************************************************************
localhost                  : ok=2    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Desglosemos la salida:

- **PLAY**: muestra el nombre del play de tu playbook
- **TASK [Gathering Facts]**: Ansible recopila automáticamente información del sistema antes de ejecutar tus tareas (viste esto con `ansible.builtin.setup` en el Módulo 1). Este es un comportamiento por defecto que puede desactivarse.
- **TASK [Install utility packages]**: tu tarea se ejecutó y reporta `changed`, lo que significa que los paquetes fueron instalados
- **PLAY RECAP**: un resumen mostrando cuántas tareas tuvieron éxito (`ok`), cuántas realizaron cambios (`changed`), y si alguna falló

### Modo TUI Interactivo

Ahora prueba ejecutar un playbook en modo interactivo:

```bash
ansible-navigator run playbooks/module-02/create-files.yml
```

Sin `--mode stdout`, `ansible-navigator` abre su TUI. Verás una pantalla mostrando los resultados del play. Desde aquí puedes:

- Presionar una tecla numérica para profundizar en un play o task específico
- Presionar ++esc++ para volver a la pantalla anterior
- Presionar ++d++ para ver la documentación de la task
- Presionar ++0++ para inspeccionar el primer (y único) play

!!! tip "Navegando la TUI"
    La TUI es una herramienta de exploración poderosa. Profundiza en una task para ver sus parámetros de entrada exactos, la salida del módulo, y si realizó cambios. Úsala para depurar cuando algo no se comporta como esperabas.

Cuando termines de explorar, presiona ++esc++ hasta salir de vuelta a tu terminal, o presiona ++colon++ y escribe `quit`.

### stdout vs. modo interactivo

| Modo | Comando | Mejor Para |
|------|---------|-----------|
| stdout | `--mode stdout` | Pipelines CI/CD, ejecuciones rápidas, scripting |
| interactivo | (por defecto) | Explorar resultados, depurar, aprender |

A lo largo de este curso usaremos ambos modos. Cuando mostremos salida en el texto del módulo, usamos `--mode stdout` por claridad. Cuando ejecutes ejercicios por tu cuenta, prueba el modo interactivo para explorar.

!!! tip "Configurar valores por defecto de navigator"
    Puedes crear un archivo `ansible-navigator.yml` en el directorio de tu proyecto para establecer valores por defecto y evitar escribir opciones cada vez:

    ```yaml
    ---
    ansible-navigator:
      mode: stdout
      playbook-artifact:
        enable: false
    ```

    Con esta configuración, `ansible-navigator run` usa el modo stdout por defecto sin generar archivos de artefactos. Consulta la [documentación de ansible-navigator](https://ansible.readthedocs.io/projects/navigator/) para ver todas las opciones disponibles.

## Modo Check y Modo Diff

Antes de ejecutar un playbook en un sistema real, a menudo quieres previsualizar qué *haría* sin realmente aplicar cambios. Ansible proporciona dos opciones para esto.

### Modo Check (`--check`)

El modo check es una ejecución simulada. Ansible recorre todas las tasks y reporta qué *cambiaría*, pero no aplica ningún cambio:

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout --check
```

```text
PLAY [Create directories and files] ********************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [Create project directory] ************************************************
changed: [localhost]

TASK [Create logs subdirectory] ************************************************
changed: [localhost]

TASK [Create a welcome file] ***************************************************
changed: [localhost]

TASK [Create an application config file] ***************************************
changed: [localhost]

PLAY RECAP *********************************************************************
localhost                  : ok=5    changed=4    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

La salida muestra `changed` para cada task, pero nada cambió realmente en el sistema. El modo check te dice "estas tasks *harían* cambios si las ejecutaras de verdad."

!!! info "No todos los módulos soportan el modo check"
    La mayoría de los módulos de Ansible soportan el modo check, pero algunos (particularmente `ansible.builtin.command` y `ansible.builtin.shell`) no lo hacen por defecto porque Ansible no puede predecir qué haría un comando arbitrario. Los módulos bien diseñados reportan con precisión en modo check.

### Modo Diff (`--diff`)

El modo diff muestra las diferencias exactas que serían (o fueron) aplicadas. Es más útil con módulos relacionados con archivos:

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout --diff
```

Cuando un archivo se crea o modifica, la salida incluye un diff mostrando el antes y después:

```text
TASK [Create a welcome file] ***************************************************
--- before
+++ after: ~/ansible-demo/README.txt
@@ -0,0 +1,2 @@
+Welcome to Ansible!
+This file was created by an Ansible playbook.

changed: [localhost]
```

### Combinando Check y Diff

La previsualización más poderosa combina ambas opciones:

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout --check --diff
```

Esto te muestra exactamente qué *cambiaría* sin hacer ningún cambio. Es la forma más segura de previsualizar tu automatización antes de aplicarla a sistemas en producción.

## Entendiendo la Idempotencia

La **idempotencia** es el concepto más importante en Ansible. Una operación es idempotente si ejecutarla múltiples veces produce el mismo resultado que ejecutarla una vez.

### Viendo la Idempotencia en Acción

Ejecuta el playbook `create-files.yml` dos veces:

**Primera ejecución:**

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout
```

```text
PLAY RECAP *********************************************************************
localhost                  : ok=5    changed=4    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Cuatro tasks reportaron `changed`: los directorios y archivos fueron creados.

**Segunda ejecución (mismo comando):**

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout
```

```text
PLAY RECAP *********************************************************************
localhost                  : ok=5    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Cero cambios la segunda vez. Los directorios y archivos ya existen con el contenido y permisos correctos, así que Ansible no tiene nada que hacer. Cada task reporta `ok` en lugar de `changed`.

### Por Qué Importa la Idempotencia

La idempotencia significa:

- **Re-ejecuciones seguras**: puedes ejecutar un playbook tantas veces como quieras sin romper nada. Si una ejecución de playbook se interrumpe a mitad de camino, simplemente ejecútalo de nuevo.
- **Detección de desviaciones**: si alguien cambia manualmente un archivo que Ansible gestiona, la siguiente ejecución del playbook lo devolverá al estado deseado y reportará `changed`.
- **Confianza**: sabes exactamente en qué estado están tus sistemas porque el playbook define el estado deseado y Ansible lo aplica.

Esto es fundamentalmente diferente de los scripts de shell. Un script que ejecuta `mkdir ~/ansible-demo` fallará en la segunda ejecución porque el directorio ya existe. El módulo `ansible.builtin.file` con `state: directory` verifica si el directorio existe primero y solo lo crea si es necesario.

!!! tip "changed=0 es el objetivo"
    Cuando ejecutas un playbook contra un sistema que ya está en el estado deseado, el resultado ideal es `changed=0`. Esto confirma que tu automatización es precisa y el sistema coincide con el estado declarado. Si ves cambios inesperados en una re-ejecución, investiga: algo está cambiando el sistema fuera de Ansible, o una task no es verdaderamente idempotente.

## Ejercicios

### Ejercicio 1: Ejecutar el playbook install-packages

Navega al directorio `ansible/` y ejecuta:

```bash
ansible-navigator run playbooks/module-02/install-packages.yml --mode stdout
```

Observa la salida. Luego ejecútalo de nuevo y confirma que la segunda ejecución muestra `changed=0`.

### Ejercicio 2: Explorar con la TUI

Ejecuta el playbook `create-files.yml` en modo interactivo:

```bash
ansible-navigator run playbooks/module-02/create-files.yml
```

Navega la TUI: profundiza en una task, examina los parámetros del módulo y los resultados, luego sal.

### Ejercicio 3: Previsualizar con check y diff

Ejecuta el playbook `create-files.yml` con `--check` y `--diff`:

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout --check --diff
```

Si ya has ejecutado el playbook una vez, la salida debería mostrar `changed=0` en modo check porque los archivos ya existen. Elimina el directorio `~/ansible-demo` (`rm -rf ~/ansible-demo`) y ejecuta el comando check+diff de nuevo para ver qué *crearía* Ansible.

### Ejercicio 4: Escribe tu propio playbook

Crea un nuevo playbook llamado `ansible/playbooks/module-02/my-playbook.yml` que:

1. Cree un directorio en `~/my-project`
2. Cree un archivo en `~/my-project/hello.txt` con el contenido que quieras
3. Cree un subdirectorio en `~/my-project/data`

Ejecútalo, verifica que los archivos fueron creados, luego ejecútalo de nuevo para confirmar la idempotencia.

## Resumen

En este módulo:

- Aprendiste la anatomía de un playbook: los plays contienen tasks, y las tasks invocan módulos
- Cubriste los fundamentos de YAML necesarios para escribir playbooks (indentación, listas, booleanos, cadenas)
- Recorriste un playbook completo línea por línea
- Ejecutaste playbooks con `ansible-navigator` tanto en modo stdout como en modo TUI interactivo
- Usaste el modo check (`--check`) y el modo diff (`--diff`) para previsualizar cambios de forma segura
- Observaste la idempotencia en acción: ejecutar un playbook dos veces produce cero cambios la segunda vez

Lionel ahora tiene dos playbooks que pueden ejecutarse repetidamente para lograr un estado del sistema consistente. Pero todos apuntan a `localhost`. ¿Qué pasa cuando Lionel necesita gestionar múltiples servidores en diferentes entornos?

## Próximos Pasos

Siguiente: [Módulo 3 -- Gestión del Inventario](3-managing-inventory.md)
