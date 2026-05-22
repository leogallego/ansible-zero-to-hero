# Módulo 4: Variables y Facts

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Definir variables en diferentes niveles de precedencia y predecir cuál gana
- Acceder a facts de Ansible usando notación de corchetes (`ansible_facts['key']`)
- Usar variables registradas y `set_fact` para datos dinámicos
- Depurar variables con `ansible.builtin.debug` y `ansible-navigator`

## La Historia Hasta Ahora

Jordan, el compañero de equipo de Lionel, se une al equipo de plataforma de Parasol Tech. Juntos revisan los playbooks del Módulo 2 y el inventario del Módulo 3. Todo funciona, pero hay un problema: los valores de configuración están escritos directamente en el código. El mismo playbook necesita instalar paquetes diferentes en desarrollo y producción, usar diferentes niveles de log y activar o desactivar el monitoreo según el entorno.

"Necesitamos parametrizar todo," dice Jordan. "Un playbook, múltiples entornos. El sistema de variables es como Ansible hace esto."

## Tipos de Variables y Dónde Definirlas

Las variables en Ansible son pares clave-valor que te permiten parametrizar tu automatización. En lugar de escribir directamente un nombre de paquete o una ruta de archivo, referencias una variable, y el valor proviene del contexto en el que se ejecuta el playbook.

### De Dónde Vienen las Variables

Hay varios lugares donde puedes definir variables, cada uno con un alcance y propósito diferente:

| Ubicación | Alcance | Cuándo usarla |
|-----------|---------|---------------|
| `defaults/main.yml` (en un rol) | Valores por defecto del rol | Precedencia más baja; valores seguros que los usuarios pueden sobreescribir |
| `group_vars/*.yml` | Todos los hosts de un grupo | Valores específicos de entorno o función |
| `host_vars/*.yml` | Un solo host | Sobreescrituras por host (DB primaria vs. réplica, etc.) |
| `vars/main.yml` (en un rol) | Internos del rol | Constantes y valores internos que los usuarios no deben cambiar |
| `vars:` en un play | Alcance del play | Valores específicos de ese play |
| `vars:` en una tarea | Alcance de la tarea | Valores específicos de esa tarea |
| `set_fact` | Alcance del host (en ejecución) | Valores calculados o dinámicos |
| `register` | Alcance del host (en ejecución) | Salida capturada de una tarea |
| Extra vars (`-e`) | Global | Sobreescrituras desde la línea de comandos; precedencia más alta |

Ya usaste varias de estas en el Módulo 3 sin pensarlo. El archivo `group_vars/all.yml` define `parasol_organization`, `parasol_ntp_server` y `parasol_dns_servers` para todos los hosts. El archivo `group_vars/dev.yml` establece `parasol_environment: "dev"` y `parasol_log_level: "debug"` para todos los hosts de desarrollo.

### Convenciones de Nombres de Variables

Buenos nombres de variables previenen colisiones y hacen evidente su origen:

- **Prefija con contexto**: `parasol_ntp_server`, no solo `ntp_server`. Si luego agregas un rol llamado `ntp`, un `ntp_server` sin prefijo colisionaría con las variables propias del rol.
- **Usa snake_case**: `parasol_backup_schedule`, no `parasolBackupSchedule` ni `parasol-backup-schedule`.
- **Sin caracteres especiales** más allá de guiones bajos; los guiones y puntos rompen la resolución de variables.

Cuando trabajes dentro de un rol (Módulo 6), prefijarás cada variable con el nombre del rol. Por ahora, Parasol Tech prefija todo con `parasol_` como espacio de nombres organizacional.

## Precedencia de Variables

Cuando el mismo nombre de variable se define en múltiples lugares, Ansible necesita una regla para decidir cuál valor gana. Esta regla es la **cadena de precedencia**.

### La Cadena Simplificada

La lista completa de precedencia de Ansible tiene más de 20 niveles, pero en la práctica solo necesitas pensar en estos seis niveles (de menor a mayor precedencia):

```text
1. Valores por defecto del rol  (defaults/main.yml)           -- mas baja
2. Variables de inventario      (group_vars/, host_vars/)
3. Play vars / role vars
4. Task vars / block vars
5. set_fact / variables registradas
6. Extra vars (-e)                                             -- mas alta (SIEMPRE GANAN)
```

Cada nivel sobreescribe al anterior. Si la misma variable aparece en múltiples niveles, la definición con mayor precedencia gana.

### Viendo la Precedencia en Acción

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

Ejecútalo:

```bash
cd ansible
ansible-navigator run playbooks/module-04/variable-precedence.yml --mode stdout
```

Ahora ejecútalo de nuevo, pasando una extra var:

```bash
ansible-navigator run playbooks/module-04/variable-precedence.yml \
  --mode stdout -e "demo_message='Extra vars win!'"
```

La salida cambia porque las extra vars están en la cima de la cadena de precedencia. Por esto las extra vars se reservan para sobreescrituras y depuración: evitan toda otra definición.

### Reglas de Precedencia para Recordar

!!! warning "Mantenlo simple"
    La fuente más común de confusión en Ansible es la precedencia de variables. Minimiza la cantidad de niveles que usas. Una buena regla general:

    - **Valores por defecto del rol** para valores seguros por defecto
    - **Variables de inventario** para el estado deseado específico del entorno
    - **Role vars** para constantes internas
    - **Extra vars** para sobreescrituras de depuración

    Si te encuentras usando más de cuatro niveles para la misma variable, tu diseño necesita simplificación.

!!! danger "Nunca pongas valores por defecto en `vars/main.yml`"
    Las variables en `vars/main.yml` (role vars) tienen mayor precedencia que las variables de inventario. Si pones un valor por defecto ahí, los usuarios no podrán sobreescribirlo desde `group_vars/` o `host_vars/` porque el role var siempre gana. Los valores por defecto para usuarios van en `defaults/main.yml`.

## Facts de Ansible

Los **facts** son variables que Ansible descubre automáticamente sobre el sistema de destino. Describen lo que el sistema *es*: su sistema operativo, direcciones IP, cantidad de CPUs, memoria, disposición de discos y más. Los facts representan **información as-is** (lo que es verdad ahora), a diferencia de las variables, que representan **información to-be** (lo que quieres que el sistema llegue a ser).

### Accediendo a los Facts

Los facts se almacenan en el diccionario `ansible_facts`. Se accede a ellos usando **notación de corchetes**:

```yaml
ansible_facts['distribution']        # "Fedora", "Ubuntu", "RedHat", etc.
ansible_facts['os_family']           # "RedHat", "Debian", "Suse", etc.
ansible_facts['distribution_version'] # "42", "24.04", "9.4", etc.
ansible_facts['memtotal_mb']         # RAM total en megabytes
ansible_facts['hostname']            # Nombre de host corto
ansible_facts['default_ipv4']        # Info de direccion IPv4 por defecto (dict)
```

!!! warning "Siempre usa notación de corchetes"
    Verás código antiguo y tutoriales usando `ansible_distribution` o `ansible_facts.distribution` (notación de punto). **Siempre usa `ansible_facts['distribution']`**. La notación de corchetes es explícita, inequívoca y la práctica recomendada.

### Categorías Comunes de Facts

| Categoría | Claves de ejemplo | Qué te dicen |
|-----------|------------------|--------------|
| Info del SO | `distribution`, `os_family`, `distribution_version` | Qué SO está ejecutándose |
| Hardware | `architecture`, `processor_count`, `memtotal_mb` | CPU, memoria, arquitectura |
| Red | `hostname`, `fqdn`, `default_ipv4`, `all_ipv4_addresses` | Configuración de red |
| Almacenamiento | `mounts`, `devices` | Info de disco y sistema de archivos |
| Fecha/hora | `date_time` | Fecha y hora actual en el destino |

### El Playbook de Demostración de Facts

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

Ejecútalo:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml --mode stdout
```

## Recopilación de Facts

### Cómo Funciona la Recopilación de Facts

Cuando un play comienza y `gather_facts` es `true` (el valor por defecto), Ansible ejecuta el módulo `ansible.builtin.setup` en cada host de destino. Este módulo recopila información del sistema y llena el diccionario `ansible_facts`. Esto sucede antes de que se ejecute cualquier tarea del play.

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

### Desactivando la Recopilación de Facts

Si tu play no necesita facts, puedes desactivar la recopilación para acelerar las cosas:

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

Esto es especialmente útil cuando apuntas a muchos hosts, ya que la recopilación de facts se ejecuta en cada host y puede agregar tiempo significativo a la ejecución del playbook.

### Subconjuntos Mínimos de Facts

A veces necesitas *algunos* facts pero no todos. El módulo `ansible.builtin.setup` acepta un parámetro `gather_subset` que te permite elegir qué categorías recopilar:

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

El `!all` elimina el conjunto completo por defecto, `!min` elimina el conjunto mínimo (que se recopila por defecto incluso cuando excluyes `all`), y luego agregas de vuelta solo lo que necesitas. Los subconjuntos comunes incluyen: `min`, `network`, `hardware`, `virtual`, `ohai` y `facter`.

El playbook complementario `facts-demo.yml` incluye un segundo play que demuestra la recopilación de subconjuntos mínimos.

## Variables Registradas y set_fact

A veces necesitas datos que no están disponibles hasta el momento de la ejecución: la salida de un comando, la existencia de un archivo o un valor calculado a partir de otras variables. Ansible proporciona dos mecanismos para esto: `register` y `set_fact`.

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

La variable registrada (`__myapp_config`) es un diccionario que contiene los valores de retorno del módulo. Diferentes módulos retornan diferentes estructuras; consulta la documentación del módulo para ver qué claves están disponibles.

!!! tip "Nombres de variables registradas"
    Prefija las variables registradas internas (no visibles para el usuario) con doble guion bajo: `__myapp_config`, no `myapp_config`. Esto indica que la variable es un detalle de implementación, no algo que un usuario deba establecer o sobreescribir.

### Campos Comunes de Variables Registradas

La mayoría de las variables registradas comparten estos campos estándar:

| Campo | Descripción |
|-------|------------|
| `changed` | Si la tarea hizo un cambio (`true`/`false`) |
| `failed` | Si la tarea falló |
| `rc` | Código de retorno (para módulos `command`/`shell`) |
| `stdout` | Salida estándar como una sola cadena |
| `stdout_lines` | Salida estándar como una lista de líneas |
| `stderr` | Salida de error estándar |
| `skipped` | Si la tarea fue omitida |

### Usando `set_fact`

El módulo `ansible.builtin.set_fact` crea o sobreescribe una variable en tiempo de ejecución. A diferencia de `register`, que captura la salida de una tarea, `set_fact` te permite calcular y asignar valores arbitrarios:

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

### Cuándo Usar Cada Uno

| Mecanismo | Usar cuando |
|-----------|------------|
| `register` | Necesitas la salida de una tarea (resultado de comando, estado de archivo, respuesta de API) |
| `set_fact` | Necesitas calcular un valor a partir de otras variables o facts |

## Depuración de Variables

Cuando un playbook no se comporta como esperas, necesitas formas de inspeccionar variables y entender qué valores está usando Ansible realmente.

### El Módulo `ansible.builtin.debug`

El módulo `debug` imprime mensajes o valores de variables durante la ejecución del playbook. Es el equivalente en Ansible de una declaración `print()`.

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

### El Parámetro `verbosity`

Cada tarea de debug debe incluir un parámetro `verbosity:`. Esto controla el nivel mínimo de verbosidad en el que se muestra el mensaje:

| Verbosidad | Cuándo se muestra | Usar para |
|------------|-------------------|-----------|
| `0` | Siempre (ejecución por defecto) | Salida que es el propósito del playbook (demos, reportes) |
| `1` | `-v` | Información básica de depuración |
| `2` | `-vv` | Estado interno detallado |
| `3` | `-vvv` | Depuración profunda (volcados completos de variables) |

```yaml
# Siempre visible -- este debug ES la salida (contexto de enseñanza/demo)
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
    En playbooks de producción, establece `verbosity: 1` o mayor en todas las tareas de debug para que sean silenciosas durante ejecuciones normales. En playbooks de enseñanza y demostración (como el código complementario de este curso), `verbosity: 0` es apropiado porque mostrar la salida *es* el propósito.

### Inspeccionando Variables en `ansible-navigator`

Cuando ejecutas un playbook en el modo interactivo de `ansible-navigator` (el predeterminado, sin `--mode stdout`), puedes profundizar en los resultados de las tareas e inspeccionar variables visualmente:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml
```

En modo interactivo:

1. La pantalla principal muestra la lista de plays; presiona un número para seleccionar un play
2. Cada play muestra sus tareas; presiona un número para seleccionar una tarea
3. La pantalla de detalle de la tarea muestra el resultado completo, incluyendo todas las variables registradas y facts
4. Presiona `0` para ver el detalle del host con todos los valores de variables

Esto es frecuentemente más rápido que agregar tareas de debug, especialmente cuando no estás seguro de qué variable necesitas inspeccionar.

### Viendo Todas las Variables de un Host

También puedes usar `ansible-navigator` para inspeccionar todas las variables asignadas a un host sin ejecutar un playbook:

```bash
ansible-navigator inventory --host localhost --mode stdout
```

Esto muestra todas las variables que Ansible asignaría a ese host, incluyendo group vars, host vars y variables especiales incorporadas.

## Condicionales con `when`

Las variables y facts se vuelven verdaderamente poderosos cuando los usas para tomar decisiones. La palabra clave `when` te permite ejecutar condicionalmente una tarea basándote en el valor de una variable, un fact o un resultado registrado.

### `when` Básico con Facts

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

Se pueden combinar múltiples condiciones como una lista (lógica AND) o con `or`:

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

Un patrón común es ejecutar una verificación, registrar el resultado y actuar condicionalmente:

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

Cuando combinas `when` con `loop`, la condición se evalúa para cada elemento:

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

Luego ejecútalo de nuevo con una sobreescritura de extra var:

```bash
ansible-navigator run playbooks/module-04/variable-precedence.yml \
  --mode stdout -e "demo_message='I am from extra vars'"
```

Responde: ¿Qué valor tiene `demo_message` en cada ejecución? ¿Por qué?

### Ejercicio 2: Explora los Facts

Ejecuta el playbook de demostración de facts:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml --mode stdout
```

Luego ejecútalo de nuevo en modo interactivo para profundizar en el conjunto completo de facts:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml
```

Navega a la primera tarea del primer play y explora el diccionario `ansible_facts`. ¿Puedes encontrar la versión de Python? ¿La versión del kernel? ¿La lista de sistemas de archivos montados?

### Ejercicio 3: Ejecuta los Condicionales

Ejecuta el playbook de condicionales:

```bash
ansible-navigator run playbooks/module-04/conditionals.yml --mode stdout
```

Observa cuáles tareas se ejecutan y cuáles se omiten. La salida depende de tu sistema. En un sistema Fedora, las tareas de la familia Red Hat se ejecutarán y las tareas de Debian se omitirán (y viceversa en Ubuntu).

### Ejercicio 4: Agrega Tus Propias Variables

Crea un archivo `ansible/inventory/group_vars/webservers.yml` (si no lo hiciste ya en los ejercicios del Módulo 3) con variables específicas de servidores web:

```yaml
---
parasol_http_port: 8080
parasol_max_connections: 1000
parasol_document_root: "/var/www/html"
```

Luego crea un playbook corto que muestre estas variables para un host de servidor web. Usa `--limit` para apuntar a un host específico y ver el conjunto de variables fusionadas.

### Ejercicio 5: Combina Facts y Variables

Escribe un playbook que:

1. Recopile facts
2. Use `set_fact` para calcular una variable (por ejemplo, `parasol_app_memory_limit` como el 50% de `ansible_facts['memtotal_mb']`)
3. Muestre el valor calculado con `ansible.builtin.debug`
4. Use `when` para imprimir una advertencia si el valor calculado está por debajo de un umbral

Este ejercicio combina todo lo de este módulo: facts, `set_fact`, `debug` con `verbosity` y `when`.

## Resumen

En este módulo:

- Aprendiste dónde definir variables (valores por defecto del rol, inventario, play vars, extra vars) y por qué importa el alcance
- Exploraste la cadena de precedencia de variables y comprobaste que las extra vars siempre ganan
- Accediste a facts del sistema usando notación de corchetes `ansible_facts['key']`
- Usaste `gather_subset` para recopilar solo los facts que necesitas
- Capturaste la salida de tareas con `register` y calculaste valores con `set_fact`
- Depuraste variables usando `ansible.builtin.debug` con `verbosity` y el modo interactivo de `ansible-navigator`
- Usaste `when` para ejecutar tareas condicionalmente basándote en facts, variables y resultados registrados

Lionel y Jordan ahora tienen las herramientas para escribir playbooks que se adaptan a cualquier entorno. El mismo playbook lee diferentes valores de `group_vars/dev.yml` y `group_vars/production.yml`, toma decisiones basadas en facts del sistema y calcula valores en tiempo de ejecución. No más configuración escrita directamente en el código.

## Próximos Pasos

Siguiente: [Módulo 5 -- Templates y Handlers](5-templates-and-handlers.md)
