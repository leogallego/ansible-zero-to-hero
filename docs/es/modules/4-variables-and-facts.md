# Modulo 4: Variables y Facts

## Objetivos de Aprendizaje

Al finalizar este modulo seras capaz de:

- Definir variables en diferentes niveles de precedencia y predecir cual gana
- Acceder a facts de Ansible usando notacion de corchetes (`ansible_facts['key']`)
- Usar variables registradas y `set_fact` para datos dinamicos
- Depurar variables con `ansible.builtin.debug` y `ansible-navigator`

## La Historia Hasta Ahora

Jordan, el companero de equipo de Alex, se une al equipo de plataforma de Parasol Tech. Juntos revisan los playbooks del Modulo 2 y el inventario del Modulo 3. Todo funciona, pero hay un problema: los valores de configuracion estan escritos directamente en el codigo. El mismo playbook necesita instalar paquetes diferentes en desarrollo y produccion, usar diferentes niveles de log y activar o desactivar el monitoreo segun el entorno.

"Necesitamos parametrizar todo," dice Jordan. "Un playbook, multiples entornos. El sistema de variables es como Ansible hace esto."

## Tipos de Variables y Donde Definirlas

Las variables en Ansible son pares clave-valor que te permiten parametrizar tu automatizacion. En lugar de escribir directamente un nombre de paquete o una ruta de archivo, referencias una variable -- y el valor proviene del contexto en el que se ejecuta el playbook.

### De Donde Vienen las Variables

Hay varios lugares donde puedes definir variables, cada uno con un alcance y proposito diferente:

| Ubicacion | Alcance | Cuando usarla |
|-----------|---------|---------------|
| `defaults/main.yml` (en un rol) | Valores por defecto del rol | Precedencia mas baja -- valores seguros que los usuarios pueden sobreescribir |
| `group_vars/*.yml` | Todos los hosts de un grupo | Valores especificos de entorno o funcion |
| `host_vars/*.yml` | Un solo host | Sobreescrituras por host (DB primaria vs. replica, etc.) |
| `vars/main.yml` (en un rol) | Internos del rol | Constantes y valores internos que los usuarios no deben cambiar |
| `vars:` en un play | Alcance del play | Valores especificos de ese play |
| `vars:` en una tarea | Alcance de la tarea | Valores especificos de esa tarea |
| `set_fact` | Alcance del host (en ejecucion) | Valores calculados o dinamicos |
| `register` | Alcance del host (en ejecucion) | Salida capturada de una tarea |
| Extra vars (`-e`) | Global | Sobreescrituras desde la linea de comandos -- precedencia mas alta |

Ya usaste varias de estas en el Modulo 3 sin pensarlo. El archivo `group_vars/all.yml` define `parasol_organization`, `parasol_ntp_server` y `parasol_dns_servers` para todos los hosts. El archivo `group_vars/dev.yml` establece `parasol_environment: "dev"` y `parasol_log_level: "debug"` para todos los hosts de desarrollo.

### Convenciones de Nombres de Variables

Buenos nombres de variables previenen colisiones y hacen evidente su origen:

- **Prefija con contexto**: `parasol_ntp_server`, no solo `ntp_server`. Si luego agregas un rol llamado `ntp`, un `ntp_server` sin prefijo colisionaria con las variables propias del rol.
- **Usa snake_case**: `parasol_backup_schedule`, no `parasolBackupSchedule` ni `parasol-backup-schedule`.
- **Sin caracteres especiales** mas alla de guiones bajos -- los guiones y puntos rompen la resolucion de variables.

Cuando trabajes dentro de un rol (Modulo 6), prefijaras cada variable con el nombre del rol. Por ahora, Parasol Tech prefija todo con `parasol_` como espacio de nombres organizacional.

## Precedencia de Variables

Cuando el mismo nombre de variable se define en multiples lugares, Ansible necesita una regla para decidir cual valor gana. Esta regla es la **cadena de precedencia**.

### La Cadena Simplificada

La lista completa de precedencia de Ansible tiene mas de 20 niveles, pero en la practica solo necesitas pensar en estos seis niveles (de menor a mayor precedencia):

```text
1. Valores por defecto del rol  (defaults/main.yml)           -- mas baja
2. Variables de inventario      (group_vars/, host_vars/)
3. Play vars / role vars
4. Task vars / block vars
5. set_fact / variables registradas
6. Extra vars (-e)                                             -- mas alta (SIEMPRE GANAN)
```

Cada nivel sobreescribe al anterior. Si la misma variable aparece en multiples niveles, la definicion con mayor precedencia gana.

### Viendo la Precedencia en Accion

El playbook complementario `variable-precedence.yml` demuestra esto. Define `demo_message` a nivel de play y usa `set_fact` para sobreescribirla:

```yaml
- name: Demonstrate variable precedence
  hosts: localhost
  connection: local
  gather_facts: false

  vars:
    demo_message: "Defined in play vars"

  tasks:
    - name: Display the winning value of demo_message
      ansible.builtin.debug:
        msg: "demo_message = {{ demo_message }}"
        verbosity: 0
```

Ejecutalo:

```bash
cd ansible
ansible-navigator run playbooks/module-04/variable-precedence.yml --mode stdout
```

Ahora ejecutalo de nuevo, pasando una extra var:

```bash
ansible-navigator run playbooks/module-04/variable-precedence.yml \
  --mode stdout -e "demo_message='Extra vars win!'"
```

La salida cambia porque las extra vars estan en la cima de la cadena de precedencia. Por esto las extra vars se reservan para sobreescrituras y depuracion -- evitan toda otra definicion.

### Reglas de Precedencia para Recordar

!!! warning "Mantenlo simple"
    La fuente mas comun de confusion en Ansible es la precedencia de variables. Minimiza la cantidad de niveles que usas. Una buena regla general:

    - **Valores por defecto del rol** para valores seguros por defecto
    - **Variables de inventario** para el estado deseado especifico del entorno
    - **Role vars** para constantes internas
    - **Extra vars** para sobreescrituras de depuracion

    Si te encuentras usando mas de cuatro niveles para la misma variable, tu diseno necesita simplificacion.

!!! danger "Nunca pongas valores por defecto en `vars/main.yml`"
    Las variables en `vars/main.yml` (role vars) tienen mayor precedencia que las variables de inventario. Si pones un valor por defecto ahi, los usuarios no podran sobreescribirlo desde `group_vars/` o `host_vars/` -- el role var siempre gana. Los valores por defecto para usuarios van en `defaults/main.yml`.

## Facts de Ansible

Los **facts** son variables que Ansible descubre automaticamente sobre el sistema de destino. Describen lo que el sistema *es* -- su sistema operativo, direcciones IP, cantidad de CPUs, memoria, disposicion de discos y mas. Los facts representan **informacion as-is** (lo que es verdad ahora), a diferencia de las variables, que representan **informacion to-be** (lo que quieres que el sistema llegue a ser).

### Accediendo a los Facts

Los facts se almacenan en el diccionario `ansible_facts`. Se accede a ellos usando **notacion de corchetes**:

```yaml
ansible_facts['distribution']        # "Fedora", "Ubuntu", "RedHat", etc.
ansible_facts['os_family']           # "RedHat", "Debian", "Suse", etc.
ansible_facts['distribution_version'] # "42", "24.04", "9.4", etc.
ansible_facts['memtotal_mb']         # RAM total en megabytes
ansible_facts['hostname']            # Nombre de host corto
ansible_facts['default_ipv4']        # Info de direccion IPv4 por defecto (dict)
```

!!! warning "Siempre usa notacion de corchetes"
    Veras codigo antiguo y tutoriales usando `ansible_distribution` o `ansible_facts.distribution` (notacion de punto). **Siempre usa `ansible_facts['distribution']`** -- la notacion de corchetes es explicita, inequivoca y la practica recomendada.

### Categorias Comunes de Facts

| Categoria | Claves de ejemplo | Que te dicen |
|-----------|------------------|--------------|
| Info del SO | `distribution`, `os_family`, `distribution_version` | Que SO esta ejecutandose |
| Hardware | `architecture`, `processor_count`, `memtotal_mb` | CPU, memoria, arquitectura |
| Red | `hostname`, `fqdn`, `default_ipv4`, `all_ipv4_addresses` | Configuracion de red |
| Almacenamiento | `mounts`, `devices` | Info de disco y sistema de archivos |
| Fecha/hora | `date_time` | Fecha y hora actual en el destino |

### El Playbook de Demostracion de Facts

El playbook complementario `facts-demo.yml` recopila facts y los muestra:

```yaml
- name: Gather and display system facts
  hosts: localhost
  connection: local

  tasks:
    - name: Display operating system information
      ansible.builtin.debug:
        msg:
          - "Distribution: {{ ansible_facts['distribution'] }}"
          - "Major version: {{ ansible_facts['distribution_major_version'] }}"
          - "Full version: {{ ansible_facts['distribution_version'] }}"
          - "OS family: {{ ansible_facts['os_family'] }}"
        verbosity: 0
```

Ejecutalo:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml --mode stdout
```

## Recopilacion de Facts

### Como Funciona la Recopilacion de Facts

Cuando un play comienza y `gather_facts` es `true` (el valor por defecto), Ansible ejecuta el modulo `ansible.builtin.setup` en cada host de destino. Este modulo recopila informacion del sistema y llena el diccionario `ansible_facts`. Esto sucede antes de que se ejecute cualquier tarea del play.

```yaml
# Comportamiento por defecto -- los facts se recopilan automaticamente
- name: Play with facts
  hosts: all
  # gather_facts: true  (esto es el valor por defecto, no necesitas escribirlo)

  tasks:
    - name: Use a fact
      ansible.builtin.debug:
        msg: "Running on {{ ansible_facts['distribution'] }}"
        verbosity: 0
```

### Desactivando la Recopilacion de Facts

Si tu play no necesita facts, puedes desactivar la recopilacion para acelerar las cosas:

```yaml
- name: Play without facts
  hosts: all
  gather_facts: false

  tasks:
    - name: Do something that does not need facts
      ansible.builtin.debug:
        msg: "No facts needed here"
        verbosity: 0
```

Esto es especialmente util cuando apuntas a muchos hosts -- la recopilacion de facts se ejecuta en cada host y puede agregar tiempo significativo a la ejecucion del playbook.

### Subconjuntos Minimos de Facts

A veces necesitas *algunos* facts pero no todos. El modulo `ansible.builtin.setup` acepta un parametro `gather_subset` que te permite elegir que categorias recopilar:

```yaml
- name: Gather only network and hardware facts
  hosts: localhost
  connection: local
  gather_facts: false

  tasks:
    - name: Gather a minimal subset
      ansible.builtin.setup:
        gather_subset:
          - "!all"
          - "!min"
          - network
          - hardware
```

El `!all` elimina el conjunto completo por defecto, `!min` elimina el conjunto minimo (que se recopila por defecto incluso cuando excluyes `all`), y luego agregas de vuelta solo lo que necesitas. Los subconjuntos comunes incluyen: `min`, `network`, `hardware`, `virtual`, `ohai` y `facter`.

El playbook complementario `facts-demo.yml` incluye un segundo play que demuestra la recopilacion de subconjuntos minimos.

## Variables Registradas y set_fact

A veces necesitas datos que no estan disponibles hasta el momento de la ejecucion -- la salida de un comando, la existencia de un archivo o un valor calculado a partir de otras variables. Ansible proporciona dos mecanismos para esto: `register` y `set_fact`.

### Registrando la Salida de Tareas

La palabra clave `register` captura el resultado completo de una tarea en una variable:

```yaml
- name: Check if a configuration file exists
  ansible.builtin.stat:
    path: /etc/myapp.conf
  register: __myapp_config

- name: Display whether the config file exists
  ansible.builtin.debug:
    msg: "Config file exists: {{ __myapp_config.stat.exists }}"
    verbosity: 0
```

La variable registrada (`__myapp_config`) es un diccionario que contiene los valores de retorno del modulo. Diferentes modulos retornan diferentes estructuras -- consulta la documentacion del modulo para ver que claves estan disponibles.

!!! tip "Nombres de variables registradas"
    Prefija las variables registradas internas (no visibles para el usuario) con doble guion bajo: `__myapp_config`, no `myapp_config`. Esto indica que la variable es un detalle de implementacion, no algo que un usuario deba establecer o sobreescribir.

### Campos Comunes de Variables Registradas

La mayoria de las variables registradas comparten estos campos estandar:

| Campo | Descripcion |
|-------|------------|
| `changed` | Si la tarea hizo un cambio (`true`/`false`) |
| `failed` | Si la tarea fallo |
| `rc` | Codigo de retorno (para modulos `command`/`shell`) |
| `stdout` | Salida estandar como una sola cadena |
| `stdout_lines` | Salida estandar como una lista de lineas |
| `stderr` | Salida de error estandar |
| `skipped` | Si la tarea fue omitida |

### Usando `set_fact`

El modulo `ansible.builtin.set_fact` crea o sobreescribe una variable en tiempo de ejecucion. A diferencia de `register`, que captura la salida de una tarea, `set_fact` te permite calcular y asignar valores arbitrarios:

```yaml
- name: Set a computed variable
  ansible.builtin.set_fact:
    app_base_url: "https://{{ ansible_facts['fqdn'] }}:{{ app_port | default(8443) }}"

- name: Display the computed URL
  ansible.builtin.debug:
    msg: "Application URL: {{ app_base_url }}"
    verbosity: 0
```

Los facts establecidos con `set_fact` tienen mayor precedencia que las play vars y las variables de inventario, y persisten durante el resto del play (y entre plays si se establece `cacheable: true`).

### Cuando Usar Cada Uno

| Mecanismo | Usar cuando |
|-----------|------------|
| `register` | Necesitas la salida de una tarea (resultado de comando, estado de archivo, respuesta de API) |
| `set_fact` | Necesitas calcular un valor a partir de otras variables o facts |

## Depuracion de Variables

Cuando un playbook no se comporta como esperas, necesitas formas de inspeccionar variables y entender que valores esta usando Ansible realmente.

### El Modulo `ansible.builtin.debug`

El modulo `debug` imprime mensajes o valores de variables durante la ejecucion del playbook. Es el equivalente en Ansible de una declaracion `print()`.

```yaml
# Imprimir un mensaje
- name: Display a status message
  ansible.builtin.debug:
    msg: "Processing host {{ inventory_hostname }}"
    verbosity: 0

# Imprimir una variable completa
- name: Display the full registered result
  ansible.builtin.debug:
    var: __myapp_config
    verbosity: 1
```

### El Parametro `verbosity`

Cada tarea de debug debe incluir un parametro `verbosity:`. Esto controla el nivel minimo de verbosidad en el que se muestra el mensaje:

| Verbosidad | Cuando se muestra | Usar para |
|------------|-------------------|-----------|
| `0` | Siempre (ejecucion por defecto) | Salida que es el proposito del playbook (demos, reportes) |
| `1` | `-v` | Informacion basica de depuracion |
| `2` | `-vv` | Estado interno detallado |
| `3` | `-vvv` | Depuracion profunda (volcados completos de variables) |

```yaml
# Siempre visible -- este debug ES la salida (contexto de ensenanza/demo)
- name: Display the result
  ansible.builtin.debug:
    msg: "Environment: {{ parasol_environment }}"
    verbosity: 0

# Solo con -v -- para depuracion
- name: Show intermediate state
  ansible.builtin.debug:
    var: __intermediate_result
    verbosity: 1

# Solo con -vv -- internos detallados
- name: Dump full variable for deep debugging
  ansible.builtin.debug:
    var: hostvars[inventory_hostname]
    verbosity: 2
```

!!! tip "Regla general para verbosity"
    En playbooks de produccion, establece `verbosity: 1` o mayor en todas las tareas de debug para que sean silenciosas durante ejecuciones normales. En playbooks de ensenanza y demostracion (como el codigo complementario de este curso), `verbosity: 0` es apropiado porque mostrar la salida *es* el proposito.

### Inspeccionando Variables en `ansible-navigator`

Cuando ejecutas un playbook en el modo interactivo de `ansible-navigator` (el predeterminado, sin `--mode stdout`), puedes profundizar en los resultados de las tareas e inspeccionar variables visualmente:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml
```

En modo interactivo:

1. La pantalla principal muestra la lista de plays -- presiona un numero para seleccionar un play
2. Cada play muestra sus tareas -- presiona un numero para seleccionar una tarea
3. La pantalla de detalle de la tarea muestra el resultado completo, incluyendo todas las variables registradas y facts
4. Presiona `0` para ver el detalle del host con todos los valores de variables

Esto es frecuentemente mas rapido que agregar tareas de debug, especialmente cuando no estas seguro de que variable necesitas inspeccionar.

### Viendo Todas las Variables de un Host

Tambien puedes usar `ansible-navigator` para inspeccionar todas las variables asignadas a un host sin ejecutar un playbook:

```bash
ansible-navigator inventory --host localhost --mode stdout
```

Esto muestra todas las variables que Ansible asignaria a ese host, incluyendo group vars, host vars y variables especiales incorporadas.

## Condicionales con `when`

Las variables y facts se vuelven verdaderamente poderosos cuando los usas para tomar decisiones. La palabra clave `when` te permite ejecutar condicionalmente una tarea basandote en el valor de una variable, un fact o un resultado registrado.

### `when` Basico con Facts

```yaml
- name: Install EPEL repository on Red Hat systems
  ansible.builtin.yum_repository:
    name: epel
    description: EPEL Repository
    baseurl: https://download.example/pub/epel/$releasever/$basearch/
    gpgcheck: true
  when: ansible_facts['os_family'] == "RedHat"
```

La tarea solo se ejecuta si el host de destino es un sistema de la familia Red Hat (RHEL, Fedora, CentOS, etc.). En sistemas basados en Debian, la tarea se omite.

### Combinando Condiciones

Se pueden combinar multiples condiciones como una lista (logica AND) o con `or`:

```yaml
# AND -- todas las condiciones deben ser verdaderas (sintaxis de lista)
- name: Configure production monitoring
  ansible.builtin.template:
    src: monitoring.conf.j2
    dest: /etc/monitoring.conf
  when:
    - ansible_facts['os_family'] == "RedHat"
    - parasol_monitoring_enabled | default(false)

# OR -- cualquier condicion es suficiente
- name: Alert on low resources
  ansible.builtin.debug:
    msg: "Resource warning on {{ inventory_hostname }}"
    verbosity: 0
  when: >-
    ansible_facts['memtotal_mb'] < 512
    or ansible_facts['processor_count'] < 2
```

### Condiciones con Variables Registradas

Un patron comun es ejecutar una verificacion, registrar el resultado y actuar condicionalmente:

```yaml
- name: Check if application config exists
  ansible.builtin.stat:
    path: /etc/myapp.conf
  register: __myapp_config

- name: Create default config if missing
  ansible.builtin.copy:
    dest: /etc/myapp.conf
    content: "# Default configuration\n"
    mode: "0644"
  when: not __myapp_config.stat.exists
```

### Condiciones en Bucles

Cuando combinas `when` con `loop`, la condicion se evalua para cada elemento:

```yaml
- name: Install only required packages
  ansible.builtin.dnf:
    name: "{{ item.name }}"
    state: present
  loop:
    - name: httpd
      required: true
    - name: debug-tools
      required: false
  when: item.required
```

El playbook complementario `conditionals.yml` demuestra todos estos patrones.

## Ejercicios

### Ejercicio 1: Ejecuta la Demo de Precedencia de Variables

Ejecuta el playbook de precedencia y observa la salida:

```bash
cd ansible
ansible-navigator run playbooks/module-04/variable-precedence.yml --mode stdout
```

Luego ejecutalo de nuevo con una sobreescritura de extra var:

```bash
ansible-navigator run playbooks/module-04/variable-precedence.yml \
  --mode stdout -e "demo_message='I am from extra vars'"
```

Responde: Que valor tiene `demo_message` en cada ejecucion? Por que?

### Ejercicio 2: Explora los Facts

Ejecuta el playbook de demostracion de facts:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml --mode stdout
```

Luego ejecutalo de nuevo en modo interactivo para profundizar en el conjunto completo de facts:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml
```

Navega a la primera tarea del primer play y explora el diccionario `ansible_facts`. Puedes encontrar la version de Python? La version del kernel? La lista de sistemas de archivos montados?

### Ejercicio 3: Ejecuta los Condicionales

Ejecuta el playbook de condicionales:

```bash
ansible-navigator run playbooks/module-04/conditionals.yml --mode stdout
```

Observa cuales tareas se ejecutan y cuales se omiten. La salida depende de tu sistema -- en un sistema Fedora, las tareas de la familia Red Hat se ejecutaran y las tareas de Debian se omitiran (y viceversa en Ubuntu).

### Ejercicio 4: Agrega Tus Propias Variables

Crea un archivo `ansible/inventory/group_vars/webservers.yml` (si no lo hiciste ya en los ejercicios del Modulo 3) con variables especificas de servidores web:

```yaml
---
parasol_http_port: 8080
parasol_max_connections: 1000
parasol_document_root: "/var/www/html"
```

Luego crea un playbook corto que muestre estas variables para un host de servidor web. Usa `--limit` para apuntar a un host especifico y ver el conjunto de variables fusionadas.

### Ejercicio 5: Combina Facts y Variables

Escribe un playbook que:

1. Recopile facts
2. Use `set_fact` para calcular una variable (por ejemplo, `parasol_app_memory_limit` como el 50% de `ansible_facts['memtotal_mb']`)
3. Muestre el valor calculado con `ansible.builtin.debug`
4. Use `when` para imprimir una advertencia si el valor calculado esta por debajo de un umbral

Este ejercicio combina todo lo de este modulo: facts, `set_fact`, `debug` con `verbosity` y `when`.

## Resumen

En este modulo:

- Aprendiste donde definir variables (valores por defecto del rol, inventario, play vars, extra vars) y por que importa el alcance
- Exploraste la cadena de precedencia de variables y comprobaste que las extra vars siempre ganan
- Accediste a facts del sistema usando notacion de corchetes `ansible_facts['key']`
- Usaste `gather_subset` para recopilar solo los facts que necesitas
- Capturaste la salida de tareas con `register` y calculaste valores con `set_fact`
- Depuraste variables usando `ansible.builtin.debug` con `verbosity` y el modo interactivo de `ansible-navigator`
- Usaste `when` para ejecutar tareas condicionalmente basandote en facts, variables y resultados registrados

Alex y Jordan ahora tienen las herramientas para escribir playbooks que se adaptan a cualquier entorno. El mismo playbook lee diferentes valores de `group_vars/dev.yml` y `group_vars/production.yml`, toma decisiones basadas en facts del sistema y calcula valores en tiempo de ejecucion. No mas configuracion escrita directamente en el codigo.

## Proximos Pasos

Siguiente: [Modulo 5 -- Templates y Handlers](5-templates-and-handlers.md)
