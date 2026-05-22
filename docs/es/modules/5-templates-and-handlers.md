# Modulo 5: Templates y Handlers

## Objetivos de Aprendizaje

Al finalizar este modulo seras capaz de:

- Escribir templates Jinja2 con variables, filtros, bucles y condicionales
- Usar `{{ ansible_managed | comment }}` y `backup: true` en tareas de template
- Configurar cadenas de handlers con `notify` y entender cuando se ejecutan los handlers
- Explicar por que los templates no deben incluir timestamps ni fechas

## La Historia Hasta Ahora

Alex y Jordan han parametrizado los playbooks de Parasol Tech con variables y facts. Cada entorno lee sus propios valores desde `group_vars/`, y los playbooks se adaptan dinamicamente usando condiciones `when`. Pero hay un nuevo problema.

"Necesitamos desplegar archivos de configuracion," dice Alex. "Config de Nginx, banners MOTD, configuracion de aplicaciones -- cada uno necesita valores diferentes por entorno. Podria usar `ansible.builtin.copy` con un archivo estatico, pero entonces necesito un archivo separado para dev, staging y produccion. Eso no escala."

"Para eso exactamente son los templates," responde Jordan. "Escribes un template con placeholders, y Ansible completa los valores en el momento del despliegue. Y cuando la configuracion cambia, los handlers reinician el servicio automaticamente."

## Fundamentos de Templates Jinja2

Ansible usa el motor de templates **Jinja2**. Un template Jinja2 es un archivo de texto -- cualquier formato (YAML, INI, TOML, XML, texto plano) -- con delimitadores especiales que Ansible evalua en tiempo de ejecucion.

### Los Tres Delimitadores

| Delimitador | Proposito | Ejemplo |
|-------------|-----------|---------|
| `{{ ... }}` | Mostrar una variable o expresion | `server_name {{ parasol_nginx_server_name }};` |
| `{% ... %}` | Ejecutar logica (bucles, condicionales) | `{% if parasol_nginx_ssl_enabled %}` |
| `{# ... #}` | Comentario (no incluido en la salida) | `{# Esta linea se ignora #}` |

### Variables en Templates

Cualquier variable disponible para el play -- variables de inventario, facts, variables registradas, valores de `set_fact` -- esta disponible dentro de los templates:

```jinja
# Sustitucion simple de variables
server_name {{ parasol_nginx_server_name }};
listen {{ parasol_nginx_http_port | default(80) }};
```

El `| default(80)` es un **filtro** -- proporciona un valor de respaldo si la variable no esta definida. Los filtros son una de las caracteristicas mas utiles de Jinja2.

### Filtros

Los filtros transforman valores de variables usando la sintaxis de pipe (`|`). Estos son los filtros que usaras con mas frecuencia:

| Filtro | Que hace | Ejemplo |
|--------|----------|---------|
| `default(value)` | Proporciona un respaldo si no esta definido | `{{ port | default(8080) }}` |
| `upper` / `lower` | Cambiar mayusculas/minusculas | `{{ env | upper }}` produce `PRODUCTION` |
| `int` / `float` | Conversion de tipo | `{{ count | int }}` |
| `join(sep)` | Unir una lista en un string | `{{ servers | join(', ') }}` |
| `comment` | Envolver texto en sintaxis de comentario | `{{ ansible_managed | comment }}` |
| `regex_replace` | Sustitucion con regex | `{{ path | regex_replace('/tmp', '/var') }}` |
| `length` | Contar elementos en una lista o string | `{{ items | length }}` |

El template companero `motd.j2` usa varios de estos:

```jinja
{{ ansible_managed | comment }}

=============================================
  Welcome to {{ inventory_hostname }}
  Organization: {{ parasol_organization | default('Unknown') }}
  Environment:  {{ parasol_environment | default('unknown') | upper }}
{% if parasol_admin_email is defined %}
  Contact:      {{ parasol_admin_email }}
{% endif %}
=============================================
```

Observa como `upper` se encadena despues de `default` -- los filtros pueden encadenarse con pipe. El filtro `| comment` en `ansible_managed` envuelve el string de gestion en la sintaxis de comentario apropiada para el formato del archivo.

### Condicionales en Templates

Usa `{% if %}`, `{% elif %}` y `{% endif %}` para incluir o excluir secciones:

```jinja
{% if parasol_nginx_ssl_enabled | default(false) %}
    listen 443 ssl;
    ssl_certificate     {{ parasol_nginx_ssl_cert }};
    ssl_certificate_key {{ parasol_nginx_ssl_key }};
{% else %}
    listen 80;
{% endif %}
```

Tambien puedes verificar si una variable existe:

```jinja
{% if parasol_admin_email is defined %}
  Contact: {{ parasol_admin_email }}
{% endif %}
```

### Bucles en Templates

Usa `{% for %}` y `{% endfor %}` para iterar sobre listas:

```jinja
upstream app_backend {
{% for server in parasol_nginx_upstream_servers %}
    server {{ server.address }}:{{ server.port | default(8080) }};
{% endfor %}
}
```

Esta es una de las caracteristicas mas potentes de los templates. El template companero `nginx.conf.j2` usa un bucle para generar un bloque upstream dinamicamente a partir de una lista de servidores backend definidos en variables de inventario.

Tambien puedes acceder a metadatos del bucle:

| Variable | Descripcion |
|----------|-------------|
| `loop.index` | Iteracion actual (base 1) |
| `loop.index0` | Iteracion actual (base 0) |
| `loop.first` | `true` en la primera iteracion |
| `loop.last` | `true` en la ultima iteracion |
| `loop.length` | Numero total de elementos |

```jinja
{% for server in parasol_nginx_upstream_servers %}
    # Server {{ loop.index }} of {{ loop.length }}
    server {{ server.address }}:{{ server.port | default(8080) }};
{% endfor %}
```

## El Modulo Template

El modulo `ansible.builtin.template` renderiza un template Jinja2 en el nodo de control y copia el resultado al host destino. Funciona como `ansible.builtin.copy`, pero procesa el archivo a traves de Jinja2 primero.

### Uso Basico

```yaml
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    owner: root
    group: root
    mode: "0644"
    backup: true
```

Parametros clave:

| Parametro | Descripcion |
|-----------|-------------|
| `src` | Ruta al template Jinja2 (relativa a `templates/` en un rol, o una ruta absoluta/relativa) |
| `dest` | Ruta destino en el host objetivo |
| `owner` / `group` | Propiedad del archivo |
| `mode` | Permisos del archivo (siempre entre comillas para evitar interpretacion octal) |
| `backup` | Crear un respaldo del archivo existente antes de sobrescribir |
| `validate` | Comando para validar el archivo renderizado antes de desplegarlo |

### El Parametro `validate`

Para archivos de configuracion que tienen un verificador de sintaxis, usa `validate` para detectar errores antes del despliegue:

```yaml
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    mode: "0644"
    backup: true
    validate: "nginx -t -c %s"
```

El `%s` se reemplaza con la ruta al archivo temporal renderizado. Si la validacion falla, la tarea falla y el archivo original queda intacto. Esto es una red de seguridad que previene desplegar configuraciones rotas.

### Resolucion de Templates en Roles

Cuando se usa dentro de un rol, la ruta `src` se resuelve relativa al directorio `templates/` del rol. No necesitas especificar la ruta completa:

```yaml
# Dentro de un rol, esto busca roles/myrole/templates/nginx.conf.j2
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
```

Fuera de un rol (en un playbook independiente), necesitas proporcionar la ruta relativa al playbook o usar una ruta absoluta. El playbook companero `deploy-config.yml` usa `{{ playbook_dir }}` para construir la ruta:

```yaml
- name: Deploy nginx configuration from template
  ansible.builtin.template:
    src: "{{ playbook_dir }}/../../templates/nginx.conf.j2"
    dest: "{{ parasol_demo_dir }}/nginx.conf"
    mode: "0644"
    backup: true
```

## Buenas Practicas de Templates

### Siempre Incluir `ansible_managed`

Cada template debe comenzar con el marcador `{{ ansible_managed | comment }}`. Esto genera un comentario al inicio del archivo renderizado que advierte a cualquiera que lo edite directamente:

```text
# Ansible managed
```

Esto es critico en operaciones. Si alguien abre un archivo de configuracion en un servidor y ve este marcador, sabe que no debe editarlo a mano -- la siguiente ejecucion de Ansible sobrescribira sus cambios.

```jinja
{{ ansible_managed | comment }}

# Application configuration
server_port={{ app_port | default(8443) }}
```

El filtro `| comment` usa automaticamente la sintaxis de comentario correcta. Para la mayoria de archivos usa `#`, pero puedes personalizarlo para formatos que usen estilos de comentario diferentes.

### Siempre Usar `backup: true`

Siempre incluye `backup: true` en tareas de `ansible.builtin.template` y `ansible.builtin.copy`:

```yaml
- name: Deploy application config
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/myapp/app.conf
    mode: "0644"
    backup: true
```

Cuando Ansible sobrescribe un archivo, el respaldo se guarda junto a el con un sufijo de timestamp (por ejemplo, `app.conf.2026-05-21@12:30:45~`). Esto te da una forma rapida de revertir si algo sale mal.

### Nunca Incluir Timestamps ni Fechas

Los templates deben producir la misma salida cuando se ejecutan con las mismas entradas. Si incluyes un timestamp:

```jinja
{# MAL — rompe la idempotencia #}
# Generated on {{ ansible_facts['date_time']['iso8601'] }}
```

El archivo renderizado sera diferente en cada ejecucion, incluso si nada mas cambio. Esto significa que la tarea `template` siempre reportara `changed`, lo que dispara handlers innecesariamente y hace imposible saber si ocurrio un cambio real de configuracion.

!!! danger "Los timestamps rompen la idempotencia"
    Nunca uses `ansible_facts['date_time']`, `now()`, ni ningun valor basado en tiempo en un template. El marcador `ansible_managed` ya les dice a los operadores que el archivo esta gestionado por Ansible -- eso es suficiente.

### Usar `mode` con Strings entre Comillas

Siempre pon entre comillas el parametro `mode`:

```yaml
mode: "0644"   # Correcto — string
mode: 0644     # MAL — YAML lo interpreta como entero decimal 420
```

YAML trata numeros sin comillas que empiezan con `0` como octal, pero solo si son octales validos. `0644` funciona por casualidad, pero `0755` podria sorprenderte en casos limite. Las comillas eliminan toda ambiguedad.

## Handlers y Notify

Desplegar un nuevo archivo de configuracion es solo la mitad del trabajo. El servicio que lee ese archivo normalmente necesita ser recargado o reiniciado para aplicar los cambios. Para eso son los **handlers**.

### Que Son los Handlers

Un handler es una tarea que se ejecuta solo cuando es notificada por otra tarea. Se define en la seccion `handlers:` de un play, y las tareas lo disparan usando la palabra clave `notify`:

```yaml
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    mode: "0644"
    backup: true
  notify: Reload nginx

handlers:
  - name: Reload nginx
    ansible.builtin.systemd:
      name: nginx
      state: reloaded
```

El handler `Reload nginx` solo se ejecutara si la tarea de template reporta `changed` -- lo que significa que el archivo renderizado es diferente de lo que ya estaba en disco. Si el archivo no ha cambiado, el handler no es notificado y el servicio se deja como esta.

Este es el punto clave: **los handlers hacen que los reinicios de servicios sean idempotentes**. No reinicias nginx en cada ejecucion -- solo cuando la configuracion realmente cambio.

### Notificar Multiples Handlers

Una sola tarea puede notificar multiples handlers pasando una lista:

```yaml
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    mode: "0644"
    backup: true
  notify:
    - Validate nginx configuration
    - Reload nginx
```

Ambos handlers se dispararan si el template cambia. El playbook companero `deploy-config.yml` demuestra este patron.

### Deduplicacion de Handlers

Si multiples tareas notifican el mismo handler, este solo se ejecuta **una vez**. Ansible deduplica las notificaciones de handlers:

```yaml
tasks:
  - name: Deploy main config
    ansible.builtin.template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
      mode: "0644"
      backup: true
    notify: Reload nginx

  - name: Deploy SSL config
    ansible.builtin.template:
      src: ssl.conf.j2
      dest: /etc/nginx/conf.d/ssl.conf
      mode: "0644"
      backup: true
    notify: Reload nginx
```

Incluso si ambos templates cambian, el handler `Reload nginx` se ejecuta solo una vez. Esto es exactamente lo que quieres -- no quieres recargar nginx dos veces en el mismo play.

## Cuando se Ejecutan los Handlers

Entender el timing de los handlers es critico para escribir playbooks correctos.

### Comportamiento por Defecto: Final del Play

Por defecto, los handlers se ejecutan **al final del play**, despues de que todas las tareas se han completado. No se ejecutan inmediatamente despues de la tarea que los notifico:

```text
TASK [Deploy main config]        → changed (notifica Reload nginx)
TASK [Deploy SSL config]         → changed (notifica Reload nginx)
TASK [Deploy upstream config]    → ok (sin notificacion)
TASK [Display status message]    → ok
HANDLER [Reload nginx]           → se ejecuta una vez, aqui al final
```

Esto significa que si una tarea posterior en el play depende de que el handler ya se haya ejecutado (por ejemplo, un health check que necesita el servicio recargado), tienes un problema. El handler aun no se ha ejecutado.

### Forzar la Ejecucion con `meta: flush_handlers`

Puedes forzar que todos los handlers pendientes se ejecuten inmediatamente usando `meta: flush_handlers`:

```yaml
tasks:
  - name: Deploy nginx configuration
    ansible.builtin.template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
      mode: "0644"
      backup: true
    notify: Reload nginx

  - name: Force handlers to run now
    ansible.builtin.meta: flush_handlers

  - name: Verify nginx is responding
    ansible.builtin.uri:
      url: "http://localhost/"
      status_code: 200
```

Despues de `flush_handlers`, todos los handlers notificados se ejecutan inmediatamente. La tarea `Verify nginx is responding` puede entonces asumir con seguridad que el servicio esta corriendo con la nueva configuracion.

El playbook companero `handler-chain.yml` demuestra `flush_handlers` en accion.

### Orden de Ejecucion de Handlers

Cuando multiples handlers son notificados, se ejecutan en el orden en que estan **definidos** en la seccion `handlers:`, no en el orden en que fueron notificados. Esta es una fuente comun de confusion.

```yaml
tasks:
  - name: Deploy config
    ansible.builtin.copy:
      dest: /tmp/demo.txt
      content: "demo\n"
      mode: "0644"
    notify:
      - Third handler (C)    # notificado primero
      - First handler (A)    # notificado segundo
      - Second handler (B)   # notificado tercero

handlers:
  - name: First handler (A)    # se ejecuta primero (definido primero)
    ansible.builtin.debug:
      msg: "A"
      verbosity: 0

  - name: Second handler (B)   # se ejecuta segundo (definido segundo)
    ansible.builtin.debug:
      msg: "B"
      verbosity: 0

  - name: Third handler (C)    # se ejecuta tercero (definido tercero)
    ansible.builtin.debug:
      msg: "C"
      verbosity: 0
```

Los handlers se ejecutan en orden A, B, C -- siguiendo el orden de definicion en `handlers:`, no el orden de notificacion. Esto te permite controlar la secuencia de ejecucion organizando los handlers en el orden correcto en la seccion `handlers:`.

!!! tip "Ordenar handlers intencionalmente"
    Si necesitas que `Validate config` se ejecute antes de `Reload service`, define `Validate config` primero en la seccion `handlers:`. El orden de notificacion en `notify:` no importa.

### Handlers y Fallos

Si una tarea falla durante el play, los handlers pendientes **no se ejecutan** por defecto. Esta es una medida de seguridad -- si algo salio mal, probablemente no quieres recargar el servicio.

Puedes cambiar este comportamiento a nivel de play:

```yaml
- name: Deploy with force handlers
  hosts: webservers
  force_handlers: true
```

Con `force_handlers: true`, los handlers se ejecutaran incluso si una tarea posterior falla. Usa esto cuando la accion del handler es segura e importante (por ejemplo, recargar una configuracion que fue desplegada exitosamente antes de que ocurriera el fallo).

## Uniendo Todo

El codigo companero de este modulo une todos los conceptos.

### El Template nginx.conf.j2

Este template (`ansible/templates/nginx.conf.j2`) demuestra:

- **`{{ ansible_managed | comment }}`** al inicio
- **Variables con valores por defecto**: `{{ parasol_nginx_worker_connections | default(1024) }}`
- **Condicionales**: La configuracion SSL solo se incluye cuando `parasol_nginx_ssl_enabled` es `true`
- **Bucles**: El pool de servidores upstream se genera a partir de una variable de lista

### El Template motd.j2

Un template mas simple (`ansible/templates/motd.j2`) que muestra:

- **Filtros**: `upper` para poner en mayusculas el nombre del entorno
- **Condicionales**: Una advertencia de produccion solo aparece cuando el entorno es `production`
- **Test `is defined`**: La linea de contacto solo aparece si `parasol_admin_email` esta definida

### El Playbook deploy-config.yml

Este playbook (`ansible/playbooks/module-05/deploy-config.yml`) despliega ambos templates en un directorio demo y demuestra:

- Despliegue de templates con `backup: true`
- Notificacion de handlers ante cambios
- Multiples handlers encadenados a una tarea

### El Playbook handler-chain.yml

Este playbook (`ansible/playbooks/module-05/handler-chain.yml`) se enfoca en el comportamiento de los handlers:

- Orden de ejecucion de handlers (orden de definicion, no de notificacion)
- `meta: flush_handlers` para forzar la ejecucion inmediata
- Deduplicacion de handlers (dos tareas notificando el mismo handler)
- Idempotencia -- los handlers no se disparan cuando no hay cambio

## Ejercicios

### Ejercicio 1: Desplegar Archivos de Configuracion

Ejecuta el playbook deploy-config:

```bash
cd ansible
ansible-navigator run playbooks/module-05/deploy-config.yml --mode stdout
```

Examina los archivos generados:

```bash
cat /tmp/ansible-demo/nginx.conf
cat /tmp/ansible-demo/motd
```

Mira la parte superior de cada archivo. Ves el comentario `# Ansible managed`? Este es el marcador `{{ ansible_managed | comment }}` en accion.

Ejecuta el playbook de nuevo sin cambiar nada. Observa que las tareas reportan `ok` (no `changed`) y los handlers **no** se ejecutan. Esto es idempotencia.

### Ejercicio 2: Explorar el Comportamiento de Handlers

Ejecuta el playbook de cadena de handlers:

```bash
ansible-navigator run playbooks/module-05/handler-chain.yml --mode stdout
```

Observa la salida cuidadosamente:

1. Los tres handlers se ejecutan en orden A, B, C (orden de definicion), aunque fueron notificados en orden C, A, B
2. `meta: flush_handlers` causa que se ejecuten a mitad del play
3. La segunda tarea copy no dispara handlers porque el contenido no cambio
4. El handler deduplicado se ejecuta solo una vez a pesar de ser notificado por dos tareas

### Ejercicio 3: Agregar SSL al Template de nginx

Modifica el playbook `deploy-config.yml` para habilitar SSL:

```yaml
vars:
  parasol_nginx_ssl_enabled: true
  parasol_nginx_ssl_cert: "/etc/pki/tls/certs/parasol.crt"
  parasol_nginx_ssl_key: "/etc/pki/tls/private/parasol.key"
```

Ejecuta el playbook de nuevo y examina el `nginx.conf` generado. Deberias ver el bloque de configuracion SSL aparecer, incluyendo la redireccion de HTTP a HTTPS.

### Ejercicio 4: Escribe Tu Propio Template

Crea un template para un archivo de configuracion de aplicacion. Por ejemplo, crea `ansible/templates/app.conf.j2`:

```jinja
{{ ansible_managed | comment }}

[server]
port={{ parasol_app_port | default(8443) }}
bind_address={{ parasol_app_bind | default('0.0.0.0') }}
workers={{ parasol_app_workers | default(4) }}

[logging]
level={{ parasol_log_level | default('info') }}
file=/var/log/myapp/app.log

[database]
{% if parasol_db_host is defined %}
host={{ parasol_db_host }}
port={{ parasol_db_port | default(5432) }}
name={{ parasol_db_name | default('myapp') }}
{% else %}
# No database configured — using local SQLite
file=/var/lib/myapp/data.db
{% endif %}
```

Escribe un playbook que despliegue este template con `backup: true` y notifique un handler cuando el archivo cambie.

### Ejercicio 5: MOTD Especifico por Entorno

Ejecuta el playbook deploy-config con la variable de entorno de produccion:

```bash
ansible-navigator run playbooks/module-05/deploy-config.yml \
  --mode stdout -e "parasol_environment=production"
```

Compara la salida del MOTD con la ejecucion por defecto (dev). La version de produccion incluye el mensaje de advertencia porque el template verifica `parasol_environment`.

Esto demuestra un principio clave: **un template, multiples salidas**. El mismo archivo `motd.j2` produce resultados diferentes basados en las variables proporcionadas.

## Resumen

En este modulo:

- Aprendiste los tres delimitadores de Jinja2 (`{{ }}`, `{% %}`, `{# #}`) y como usar variables, filtros, bucles y condicionales en templates
- Usaste el modulo `ansible.builtin.template` con `backup: true` y `validate` para desplegar archivos de configuracion renderizados de forma segura
- Agregaste `{{ ansible_managed | comment }}` a cada template para que los operadores sepan que el archivo esta gestionado por Ansible
- Entendiste por que los timestamps y fechas nunca deben aparecer en templates (rompen la idempotencia)
- Configuraste handlers con `notify` para reiniciar o recargar servicios solo cuando la configuracion realmente cambia
- Exploraste el orden de ejecucion de handlers (orden de definicion, no de notificacion), deduplicacion y `meta: flush_handlers`
- Usaste `force_handlers` para asegurar que handlers criticos se ejecuten incluso cuando tareas posteriores fallan

Alex y Jordan ahora despliegan archivos de configuracion como templates. Un solo `nginx.conf.j2` funciona en dev, staging y produccion -- cada entorno completa sus propios valores desde variables de inventario. Cuando la configuracion cambia, los handlers recargan el servicio automaticamente. Cuando no cambia, no pasa nada. La automatizacion es idempotente y autodocumentada.

## Proximos Pasos

Siguiente: [Modulo 6 -- Roles y Colecciones](6-roles-and-collections.md)
