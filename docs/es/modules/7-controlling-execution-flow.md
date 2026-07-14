# Módulo 7: Controlando el Flujo de Ejecución

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Usar `block`, `rescue` y `always` para manejar errores de tareas de forma elegante e implementar lógica de rollback
- Controlar el reporte de estado de tareas con `changed_when` y `failed_when`, y entender cuándo `ignore_errors` es apropiado versus cuándo no lo es
- Organizar tareas de playbooks con tags y aplicar la regla de seguridad: cada tag debe ser seguro de ejecutar de forma independiente
- Delegar tareas a otros hosts con `delegate_to` y `run_once` para coordinación entre hosts
- Distinguir entre `include_tasks` (dinámico) e `import_tasks` (estático), y elegir el correcto para cada situación
- Usar `ansible.builtin.assert` para validar precondiciones antes de proceder con operaciones riesgosas

## La Historia Hasta Ahora

Lionel y Jordan ejecutan su playbook de despliegue de servidores web contra el entorno de staging. El playbook instala paquetes, despliega archivos de configuración, ejecuta una migración de base de datos y reinicia servicios. La migración de base de datos falla en el segundo de cuatro servidores. Ansible se detiene en ese host pero continúa en los demás. El resultado: dos servidores tienen el nuevo esquema, uno está atascado a mitad de la migración y uno nunca comenzó. El equipo pasa las siguientes dos horas arreglando la inconsistencia manualmente.

"Necesitamos manejar errores," dice Jordan. "Si la migración falla, el playbook debería revertir los cambios de configuración y dejar el servidor en un estado conocido -- no en un estado intermedio. Y necesitamos una forma de ejecutar solo el paso de migración para depuración, sin re-ejecutar todo el playbook."

Lionel está de acuerdo: "También quiero ejecutar una verificación de salud en el balanceador de carga desde el nodo de control durante el despliegue, no desde los servidores web mismos."

En este módulo, Lionel y Jordan aprenden manejo estructurado de errores con bloques, control fino de tareas, tags para ejecución selectiva, delegación para tareas entre hosts, y cómo dividir sus playbooks crecientes en archivos de tareas reutilizables. Estas técnicas transforman sus playbooks frágiles de todo-o-nada en automatización resiliente y quirúrgica -- y preparan el terreno para extraer roles reutilizables en el Módulo 8.

## Bloques, Rescue y Always

Un **bloque** agrupa múltiples tareas bajo una directiva única. Los bloques sirven dos propósitos: aplicar atributos compartidos (como `when`, `become` o `tags`) a un conjunto de tareas, y manejar errores con `rescue` y `always`.

### Agrupando Tareas

En su forma más simple, un bloque te permite aplicar una condición o escalación de privilegios a varias tareas a la vez en lugar de repetirla en cada una:

```yaml
- name: Install and configure the application
  block:
    - name: Install application packages
      ansible.builtin.package:
        name: "{{ parasol_app_packages }}"
        state: present

    - name: Deploy application configuration
      ansible.builtin.template:
        src: app.conf.j2
        dest: /etc/myapp/app.conf
        mode: "0644"
        backup: true
  when: parasol_app_enabled | default(true)
  become: true
```

Ambas tareas heredan la condición `when` y `become: true` del bloque. Sin el bloque, necesitarías repetir ambas directivas en cada tarea.

### Manejo de Errores: El Patrón Try/Catch/Finally

El verdadero poder de los bloques es el manejo de errores. Un bloque con `rescue` y `always` funciona como try/catch/finally en lenguajes de programación:

- **block** -- las tareas a intentar (el "try")
- **rescue** -- se ejecuta solo si una tarea en el bloque falla (el "catch")
- **always** -- se ejecuta sin importar si hubo éxito o fallo (el "finally")

```yaml
- name: Deploy application with error handling
  block:
    - name: Deploy configuration file
      ansible.builtin.copy:
        content: "version={{ parasol_app_version | default('1.0') }}\n"
        dest: "{{ parasol_demo_dir }}/app/config.ini"
        mode: "0644"

    - name: Run database migration
      ansible.builtin.command:
        cmd: /bin/false
      changed_when: false
      when: parasol_simulate_failure | default(true)

  rescue:
    - name: Report the failure
      ansible.builtin.debug:
        msg: >-
          Deployment failed at task '{{ ansible_failed_task.name }}'.
          Rolling back.
        verbosity: 0

    - name: Roll back configuration
      ansible.builtin.file:
        path: "{{ parasol_demo_dir }}/app/config.ini"
        state: absent

  always:
    - name: Record deployment attempt
      ansible.builtin.lineinfile:
        path: "{{ parasol_demo_dir }}/deploy.log"
        line: "{{ ansible_date_time.iso8601 }} - Deployment attempt completed"
        create: true
        mode: "0644"
```

Cuando la tarea de migración falla, Ansible salta las tareas restantes del bloque y pasa a `rescue`. Dentro de rescue, dos variables especiales están disponibles:

| Variable | Contiene |
|----------|----------|
| `ansible_failed_task` | El objeto completo de la tarea que falló (usa `.name` para obtener su nombre) |
| `ansible_failed_result` | El objeto resultado de la tarea fallida (usa `.rc`, `.msg`, `.stderr`) |

La sección `always` se ejecuta después tanto del bloque como del rescue (o después del bloque solo si nada falló). Úsala para tareas de limpieza como registro de logs, cierre de conexiones o eliminación de archivos temporales.

### Ejecutando Handlers en Rescue

En el Módulo 5 aprendiste que los handlers se ejecutan al final del play. Pero ¿qué pasa si un handler fue notificado antes de un fallo, y necesitas que se ejecute durante rescue? Usa `meta: flush_handlers` para forzar la ejecución inmediata de handlers pendientes:

```yaml
rescue:
  - name: Flush pending handlers before rollback
    ansible.builtin.meta: flush_handlers

  - name: Roll back configuration
    ansible.builtin.file:
      path: /etc/myapp/app.conf
      state: absent
```

### Salida Anticipada con `meta`

A veces un error es irrecuperable y quieres detener el play completo o remover un host del procesamiento posterior:

- **`meta: end_play`** -- detiene el play actual para todos los hosts. Úsalo en rescue cuando el fallo afecta todo el despliegue.
- **`meta: end_host`** -- remueve solo el host actual del play. Los demás hosts continúan.
- **`meta: clear_host_errors`** -- restablece el estado de error de un host para que participe en plays posteriores.

```yaml
rescue:
  - name: This host cannot continue
    ansible.builtin.meta: end_host
```

!!! tip "Los bloques no son bucles"
    Los bloques agrupan tareas para directivas compartidas y manejo de errores. Cada tarea en un bloque se ejecuta en secuencia. No se puede iterar sobre un bloque. Si necesitas repetir un conjunto de tareas, usa `ansible.builtin.include_tasks` con un `loop` -- cubierto más adelante en este módulo.

## Control Fino de Tareas

Una vez que puedes capturar errores con bloques, la siguiente pregunta es: ¿qué cuenta como error? ¿Y qué cuenta como un cambio? Ansible proporciona varias directivas para controlar el reporte de estado de las tareas.

### `changed_when` -- Controlando el Reporte de Cambios

Los módulos `ansible.builtin.command` y `ansible.builtin.shell` siempre reportan `changed`, incluso cuando realizan una operación de solo lectura. Esto es engañoso y dispara handlers innecesariamente. Usa `changed_when` para decirle a Ansible cuándo una tarea realmente cambió algo:

```yaml
- name: Check application version
  ansible.builtin.command:
    cmd: cat {{ parasol_demo_dir }}/app/config.ini
  register: parasol_version_check
  changed_when: false
```

Establecer `changed_when: false` significa "esta tarea nunca cambia nada." También puedes usar expresiones:

```yaml
- name: Initialize the database
  ansible.builtin.command:
    cmd: myapp-cli db init
  register: parasol_db_init
  changed_when: "'Created' in parasol_db_init.stdout"
```

Ahora la tarea solo reporta `changed` cuando la salida contiene "Created." En ejecuciones posteriores donde la base de datos ya existe, reporta `ok`.

!!! danger "Siempre agrega `changed_when` a tareas command y shell"
    Esto no es opcional. Sin `changed_when`, las tareas command y shell siempre se muestran como changed, haciendo tu playbook no idempotente. La regla de ansible-lint `no-changed-when` lo impone -- lo verás en el Módulo 9.

### `failed_when` -- Redefiniendo el Fallo

Algunos comandos usan códigos de salida distintos de cero para condiciones que no son errores. `grep` devuelve código de salida 1 cuando no encuentra coincidencias -- eso no es un fallo, es un resultado esperado. Usa `failed_when` para definir qué constituye realmente un fallo:

```yaml
- name: Check for deprecated configuration entries
  ansible.builtin.command:
    cmd: grep -c "deprecated" {{ parasol_demo_dir }}/app/config.ini
  register: parasol_deprecated_check
  failed_when: parasol_deprecated_check.rc > 1
  changed_when: false
```

Aquí la tarea solo falla si `grep` mismo tiene un error (código de salida 2+), no cuando simplemente no encuentra coincidencias (código de salida 1).

### `ansible.builtin.assert` -- Verificaciones de Precondiciones

Antes de ejecutar una operación riesgosa, valida que los prerequisitos se cumplan. El módulo `assert` falla con un mensaje claro si las condiciones no se satisfacen:

```yaml
- name: Validate deployment preconditions
  ansible.builtin.assert:
    that:
      - parasol_app_version is defined
      - parasol_app_version is version('1.0', '>=')
    fail_msg: >-
      parasol_app_version must be defined and >= 1.0.
      Got: '{{ parasol_app_version | default('undefined') }}'.
    success_msg: "Preconditions met: deploying version {{ parasol_app_version }}"
```

Assert es una alternativa mucho mejor que saltar tareas silenciosamente con `when`. Si una variable falta, quieres saberlo inmediatamente -- no descubrir después que la mitad del playbook fue saltada.

### `ignore_errors` -- Usar con Precaución

La directiva `ignore_errors: true` hace que una tarea continúe sin importar el fallo. Tiene su lugar, pero se usa en exceso:

```yaml
- name: Remove optional cache directory
  ansible.builtin.file:
    path: "{{ parasol_demo_dir }}/cache"
    state: absent
  ignore_errors: true
```

!!! warning "`ignore_errors` es un indicador de problemas"
    `ignore_errors: true` silencia **todos** los errores en una tarea, incluyendo los inesperados. Prefiere `failed_when` para definir exactamente qué constituye un fallo, o usa `block`/`rescue` para manejar errores explícitamente. Reserva `ignore_errors` para tareas donde genuinamente no te importa el resultado -- como eliminar un archivo opcional que puede no existir. Si te encuentras usándolo frecuentemente, tu playbook probablemente tiene un problema de diseño.

### Control de Fallos por Lote

Para despliegues a través de muchos hosts, puede que no quieras detenerte completamente cuando un host falla. Dos configuraciones a nivel de play controlan esto:

- **`any_errors_fatal: true`** -- si cualquier host falla, todos los hosts se detienen. Usa esto para cambios que deben ser todo-o-nada (como migraciones de base de datos).
- **`max_fail_percentage: 25`** -- el play continúa mientras menos del 25% de los hosts hayan fallado. Útil para actualizaciones progresivas donde algunos fallos son aceptables.

## Tags

Los tags te permiten ejecutar un subconjunto de tu playbook sin ejecutar todo. Son etiquetas que adjuntas a tareas, bloques, plays o roles, y luego seleccionas en la línea de comandos.

### Agregando Tags

```yaml
- name: Install application packages
  ansible.builtin.package:
    name: "{{ parasol_app_packages }}"
    state: present
  tags:
    - install

- name: Deploy configuration
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/myapp/app.conf
    mode: "0644"
  tags:
    - configure
```

Ejecuta solo las tareas de instalación:

```bash
ansible-navigator run deploy.yml --mode stdout --tags install
```

### Tags Especiales

Ansible proporciona dos tags especiales integrados:

- **`always`** -- las tareas etiquetadas con `always` se ejecutan sin importar qué tags selecciones. Usa esto para verificaciones de estado o logging que siempre deben ocurrir.
- **`never`** -- las tareas etiquetadas con `never` solo se ejecutan cuando solicitas explícitamente el tag. Usa esto para volcados de depuración u operaciones destructivas.

```yaml
- name: Show deployment status
  ansible.builtin.debug:
    msg: "Deployment in progress"
    verbosity: 0
  tags:
    - always

- name: Dump all variables for debugging
  ansible.builtin.debug:
    var: vars
    verbosity: 0
  tags:
    - never
    - debug
```

El volcado de depuración solo se ejecuta con `--tags debug`. Nunca se ejecuta en operación normal.

### Previsualizando Tags

Antes de ejecutar con tags, previsualiza lo que sucederá:

```bash
# Listar todos los tags disponibles
ansible-navigator run deploy.yml --mode stdout --list-tags

# Listar tareas que se ejecutarían con tags específicos
ansible-navigator run deploy.yml --mode stdout --list-tasks --tags configure
```

### Herencia de Tags

Los tags en `ansible.builtin.import_tasks` fluyen hacia abajo a cada tarea dentro del archivo importado. Los tags en `ansible.builtin.include_tasks` aplican solo a la declaración de include misma -- las tareas internas no los heredan. Esta distinción importa y se cubre en la sección Include vs Import a continuación.

!!! danger "La regla de seguridad de tags"
    Cada tag **debe** ser seguro de ejecutar de forma independiente. Si ejecutar `--tags deploy` sin ejecutar también `--tags install` rompería algo, tu diseño de tags está mal. Los tags son para seleccionar subconjuntos de un playbook bien estructurado, no para imponer orden de ejecución.

### Tags y Bloques

Cuando etiquetas un bloque, el tag aplica a todas las tareas en `block`, `rescue` y `always`. Pero ten cuidado: si ejecutas con `--tags` y el bloque está etiquetado pero `rescue`/`always` no, el manejo de errores podría no ejecutarse. Siempre asegúrate de que si un bloque tiene tags, las secciones rescue y always compartan esos tags o usen el tag especial `always`.

## Delegación y Run Once

A veces una tarea necesita ejecutarse en un host diferente al que se está configurando. Por ejemplo, remover un servidor web de un balanceador de carga antes de desplegarlo -- esa acción se ejecuta en el balanceador de carga (o el nodo de control), no en el servidor web.

### `delegate_to`

La directiva `delegate_to` ejecuta una tarea en un host especificado mientras sigue operando en el contexto del host actual:

```yaml
- name: Remove host from load balancer
  ansible.builtin.debug:
    msg: "Removing {{ inventory_hostname }} from load balancer pool"
    verbosity: 0
  delegate_to: localhost

- name: Deploy application
  ansible.builtin.copy:
    content: "version={{ parasol_app_version }}\n"
    dest: "{{ parasol_demo_dir }}/app/release.txt"
    mode: "0644"

- name: Add host back to load balancer
  ansible.builtin.debug:
    msg: "Adding {{ inventory_hostname }} back to load balancer pool"
    verbosity: 0
  delegate_to: localhost
```

La clave: `delegate_to: localhost` ejecuta la tarea en el nodo de control, pero `inventory_hostname` sigue refiriéndose al host objetivo. Así es como interactúas con sistemas externos (balanceadores de carga, monitoreo, DNS) durante un despliegue por host.

!!! tip "Prefiere `delegate_to: localhost` sobre `local_action`"
    La directiva más antigua `local_action` hace lo mismo pero está deprecada por ansible-lint (regla `deprecated-local-action`). Siempre usa `delegate_to: localhost` en su lugar.

### `run_once`

Cuando una tarea debe ejecutarse solo una vez sin importar cuántos hosts estén en el play, usa `run_once: true`:

```yaml
- name: Send deployment notification
  ansible.builtin.debug:
    msg: "Deployment notification sent for {{ ansible_play_hosts | length }} hosts"
    verbosity: 0
  run_once: true
  delegate_to: localhost
```

Sin `run_once`, esta notificación se dispararía una vez por host. Con él, la tarea se ejecuta en el primer host del lote y salta todos los demás.

### `delegate_facts`

Por defecto, los facts recopilados durante una tarea delegada se asignan al host que delega, no al host objetivo de la delegación. Si necesitas que los facts se almacenen en el objetivo, agrega `delegate_facts: true`:

```yaml
- name: Gather load balancer facts
  ansible.builtin.setup:
  delegate_to: lb01.parasol.example
  delegate_facts: true
```

### Actualizaciones Progresivas con `serial`

Para desplegar a muchos hosts sin tiempo de inactividad, usa `serial` a nivel de play para procesar hosts en lotes:

```yaml
- name: Rolling deployment
  hosts: webservers
  serial: 2
```

Esto procesa dos hosts a la vez. Combinado con `delegate_to` para gestión del balanceador de carga, obtienes un patrón de despliegue progresivo sin tiempo de inactividad.

### `reset_connection` para Cambios a Mitad del Play

Si una tarea cambia los parámetros de conexión a mitad del play (por ejemplo, cambiar el usuario remoto después de otorgar acceso sudo), usa `meta: reset_connection` para cerrar y reestablecer la conexión SSH:

```yaml
- name: Reset connection after user change
  ansible.builtin.meta: reset_connection
```

## Include vs Import

A medida que los playbooks crecen, dividirlos en archivos más pequeños los hace más fáciles de mantener. Ansible proporciona dos mecanismos para esto, y se comportan de manera diferente.

### `import_tasks` -- Estático (Tiempo de Compilación)

`ansible.builtin.import_tasks` funciona como pegar el contenido del archivo en tu playbook antes de que se ejecute. Ansible pre-procesa los imports durante el análisis del playbook:

```yaml
- name: Import application setup tasks
  ansible.builtin.import_tasks:
    file: tasks/setup-app.yml
```

### `include_tasks` -- Dinámico (Tiempo de Ejecución)

`ansible.builtin.include_tasks` funciona como llamar a una función en tiempo de ejecución. Ansible procesa los includes durante la ejecución del play:

```yaml
- name: Include application setup tasks
  ansible.builtin.include_tasks:
    file: tasks/setup-app.yml
```

### Cuándo Usar Cada Uno

| Característica | `import_tasks` | `include_tasks` |
|---------------|---------------|----------------|
| Momento de procesamiento | Pre-procesado (estático) | Tiempo de ejecución (dinámico) |
| Visibilidad en `--list-tasks` | Muestra nombres de tareas individuales | Muestra solo la declaración de include |
| Herencia de tags | Los tags fluyen hacia abajo a todas las tareas | Los tags aplican solo al include mismo |
| Bucles | No puede usarse en bucles | Puede usarse en bucles |
| Condicionales | `when` aplica a cada tarea importada individualmente | `when` aplica a la declaración de include |
| Handlers | Puede notificar y ser notificado por nombre | Puede notificar pero los nombres de handlers no son visibles hasta la inclusión |

!!! tip "Import = tiempo de compilación, include = tiempo de ejecución"
    En caso de duda: usa `import_tasks` para archivos de tareas fijos que siempre se ejecutan de la misma manera. Usa `include_tasks` para archivos de tareas condicionales o con bucles. La distinción importa más con tags: las tareas importadas heredan tags de la declaración de import, pero las tareas incluidas no.

### Ejemplo de Herencia de Tags

Esta es la fuente de confusión más común. Considera un archivo de tareas `tasks/setup-app.yml` con dos tareas dentro. Si lo importas con un tag:

```yaml
- name: Import setup tasks
  ansible.builtin.import_tasks:
    file: tasks/setup-app.yml
  tags:
    - setup
```

Ejecutar `--tags setup` ejecuta ambas tareas dentro del archivo, porque el tag fluye hacia abajo.

Pero si lo incluyes con un tag:

```yaml
- name: Include setup tasks
  ansible.builtin.include_tasks:
    file: tasks/setup-app.yml
  tags:
    - setup
```

Ejecutar `--tags setup` dispara la declaración de include, que luego ejecuta las tareas internas. La diferencia es sutil aquí pero se vuelve significativa en playbooks complejos: con `include_tasks`, también puedes usar la palabra clave `apply` para pasar tags a las tareas incluidas.

### Aplicándolo a Roles

Todo lo referente a `include_tasks` vs `import_tasks` aplica a roles también. `ansible.builtin.import_role` es estático y `ansible.builtin.include_role` es dinámico. Cuando extraigas archivos de tareas reutilizables en roles en el Módulo 8, las mismas reglas sobre tags, condicionales y bucles aplican.

## Ejercicios

### Ejercicio 1: Manejo de Errores con Bloques

Ejecuta el playbook de manejo de errores para ver block/rescue/always en acción:

```bash
cd ansible
ansible-navigator run playbooks/module-07/error-handling.yml --mode stdout
```

Observa la salida:

1. Las tareas del bloque se ejecutan hasta el fallo simulado de migración
2. Las tareas después del fallo en el bloque se saltan
3. Rescue se ejecuta y reporta el nombre de la tarea fallida usando `ansible_failed_task.name`
4. Always se ejecuta y registra el intento de despliegue

Ahora ejecútalo de nuevo con el fallo deshabilitado:

```bash
ansible-navigator run playbooks/module-07/error-handling.yml --mode stdout \
  -e "parasol_simulate_failure=false"
```

Observa que rescue **no** se ejecuta (no hubo fallo), pero always sí se ejecuta. Este es el patrón try/catch/finally: always significa siempre.

### Ejercicio 2: Controlando el Estado de Tareas

Ejecuta el playbook de control de tareas:

```bash
ansible-navigator run playbooks/module-07/task-control.yml --mode stdout
```

Observa cada técnica:

1. La tarea `command` reporta `ok` (no `changed`) gracias a `changed_when: false`
2. La tarea `failed_when` no falla a pesar de que `grep` devuelve código de salida 1
3. La tarea `assert` valida precondiciones con un mensaje de error claro
4. La tarea `ignore_errors` registra una advertencia pero el playbook continúa

Ejecútalo una segunda vez -- la salida debería ser idéntica, confirmando idempotencia.

### Ejercicio 3: Trabajando con Tags

Explora el playbook de despliegue con tags sin ejecutarlo primero:

```bash
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout --list-tags
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout --list-tasks --tags configure
```

Luego ejecútalo con diferentes selecciones de tags:

```bash
# Ejecutar solo tareas de instalación
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout --tags install

# Ejecutar solo tareas de verificación
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout --tags verify

# Ejecutar todo (sin filtro de tags)
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout
```

Observa que la tarea con tag `always` se ejecuta en cada caso, y el volcado de depuración con tag `never` solo se ejecuta cuando se solicita explícitamente con `--tags debug`.

### Ejercicio 4: Delegación y Run Once

Ejecuta el playbook de delegación:

```bash
ansible-navigator run playbooks/module-07/delegation.yml --mode stdout
```

Observa el patrón de despliegue progresivo:

1. "Remove from load balancer" se ejecuta en localhost pero referencia `inventory_hostname`
2. Las tareas de despliegue se ejecutan en el host objetivo
3. "Add back to load balancer" se ejecuta en localhost
4. La tarea de notificación se ejecuta solo una vez a pesar de múltiples hosts

### Ejercicio 5: Include vs Import

Ejecuta el playbook de comparación y explora las diferencias:

```bash
# Primero, lista las tareas para ver la diferencia de visibilidad
ansible-navigator run playbooks/module-07/include-vs-import.yml --mode stdout --list-tasks

# Ejecutar con el tag setup
ansible-navigator run playbooks/module-07/include-vs-import.yml --mode stdout --tags setup

# Ejecutar todo
ansible-navigator run playbooks/module-07/include-vs-import.yml --mode stdout
```

Compara la salida de `--list-tasks`: las tareas importadas muestran sus nombres individuales, mientras que las tareas incluidas muestran solo la declaración de include. Luego compara la ejecución con `--tags setup`: las tareas importadas heredan el tag, pero las tareas incluidas se comportan diferente.

## Resumen

En este módulo:

- Usaste `block`, `rescue` y `always` para manejo estructurado de errores con lógica de rollback, e inspeccionaste fallos con `ansible_failed_task` y `ansible_failed_result`
- Controlaste el reporte de estado de tareas con `changed_when` (obligatorio en `command`/`shell`) y `failed_when` para comandos que usan códigos de salida distintos de cero legítimamente
- Validaste precondiciones con `ansible.builtin.assert` en lugar de saltar tareas silenciosamente
- Aprendiste por qué `ignore_errors` es un indicador de problemas y cuándo es genuinamente apropiado
- Organizaste playbooks con tags, incluyendo los tags especiales `always` y `never`, y aplicaste la regla de seguridad: cada tag debe funcionar de forma independiente
- Delegaste tareas a otros hosts con `delegate_to` y usaste `run_once` para notificaciones y coordinación entre hosts
- Distinguiste `import_tasks` (estático, tiempo de compilación, herencia de tags) de `include_tasks` (dinámico, tiempo de ejecución, compatible con bucles) y aprendiste cuándo elegir cada uno

Lionel y Jordan ahora manejan errores de forma elegante -- cuando una migración falla, el playbook revierte y registra el intento en lugar de dejar servidores en un estado inconsistente. Usan tags para ejecutar solo el despliegue o solo el paso de verificación. Y sus playbooks crecientes están divididos en archivos de tareas reutilizables, listos para ser extraídos en roles.

## Próximos Pasos

Siguiente: [Módulo 8 -- Roles y Collections](8-roles-and-collections.md)
