# Módulo 6: Protegiendo tus Datos

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Encriptar variables sensibles usando `ansible-vault encrypt_string` e incorporarlas en archivos YAML en texto plano
- Encriptar archivos completos con `ansible-vault encrypt` y gestionarlos con `edit`, `view`, `rekey` y `decrypt`
- Gestionar contraseñas de vault usando archivos de contraseña y variables de entorno
- Ejecutar playbooks protegidos con vault usando `ansible-navigator`
- Usar plugins de lookup (`ansible.builtin.file`, `ansible.builtin.env`, `ansible.builtin.pipe`, `ansible.builtin.password`) para obtener datos desde fuera de los playbooks
- Proteger la salida sensible de las tareas en los logs usando `no_log: true`

## La Historia Hasta Ahora

El equipo de Lionel ha sido productivo. Han parametrizado playbooks con variables, desplegado archivos de configuración con templates y configurado handlers para reiniciar servicios cuando las configuraciones cambian. Los playbooks de la plataforma Parasol Tech están registrados en el repositorio Git del equipo, y todos están contribuyendo.

Entonces sucede. Durante una revisión de código rutinaria, Jordan nota que `group_vars/production.yml` contiene la contraseña de la base de datos de producción en texto plano: `parasol_db_password: "Sup3rS3cret!"`. Peor aún, el archivo ha estado en control de versiones durante tres semanas. El equipo de seguridad lo marca durante una auditoría. Aunque la contraseña se rota inmediatamente, el valor en texto plano está permanentemente integrado en el historial de Git. "Necesitamos tratar los secretos de manera diferente a las variables regulares," dice Lionel. "Contraseñas, claves API, certificados -- ninguno de estos debe estar en texto plano, ni siquiera en un repositorio privado."

Jordan consulta la documentación de Ansible. "Ansible tiene esto incorporado. Se llama Vault. Podemos encriptar valores individuales directamente dentro de nuestros archivos de variables existentes, o encriptar archivos completos. De cualquier manera, los secretos conviven con nuestro código pero están protegidos en reposo. Y hay plugins de lookup para obtener secretos desde archivos, variables de entorno o comandos externos -- así que no estamos limitados a codificar nada de forma fija." El equipo pasa una tarde aprendiendo Vault y asegurando cada secreto en el repositorio. Al final del día, el equipo de seguridad da su aprobación.

## El Problema: Secretos en Texto Plano

Antes de sumergirnos en soluciones, vale la pena entender por qué los secretos en texto plano son peligrosos -- incluso en un repositorio privado.

Considera esta línea en `group_vars/production.yml`:

```yaml
parasol_db_password: "Sup3rS3cret!"
```

En el momento en que se hace commit de este archivo, la contraseña existe en el historial de Git para siempre. Ejecutar `git rm` o sobrescribir el archivo no ayuda -- cualquier persona con acceso al repositorio puede ejecutar `git log -p` y encontrar el valor en texto plano. Rotar la contraseña soluciona el riesgo inmediato, pero el valor filtrado permanece en el historial.

Los secretos caen en la categoría de **datos en reposo** cuando se encuentran en archivos en disco o en control de versiones. Ansible Vault protege los datos en reposo encriptándolos con AES-256, el mismo estándar usado por gobiernos e instituciones financieras. Pero hay una segunda categoría -- **datos en uso** -- que Vault por sí solo no cubre. Cuando Ansible desencripta un valor y lo pasa a una tarea, el texto plano puede aparecer en logs, salida de callbacks o resultados de tareas. Proteger los datos en uso requiere `no_log: true`, que cubriremos más adelante en este módulo.

!!! warning "Datos en reposo vs. datos en uso"
    Ansible Vault protege secretos **en reposo** -- encriptados en disco y en control de versiones. Una vez que Ansible desencripta un valor y lo usa en una tarea, el texto plano existe en memoria y puede aparecer en logs o artefactos. Vault no previene filtraciones en tiempo de ejecución. Siempre combina la encriptación de vault con `no_log: true` en las tareas que manejan valores sensibles.

## Ansible Vault: Encriptando Variables

El patrón más común en el mundo real es encriptar valores de variables individuales mientras el resto del archivo YAML permanece legible. Esto se llama **encriptación a nivel de variable**, y la herramienta para ello es `ansible-vault encrypt_string`.

### Encriptando un Valor Individual

Para encriptar un valor de cadena y asignarlo a un nombre de variable:

```bash
ansible-vault encrypt_string \
  --vault-password-file .vault_password \
  'Sup3rS3cret!' \
  --name 'parasol_db_password'
```

Esto produce una salida como:

```yaml
parasol_db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          63306536653963613135303839343061383532316130623562653463623437376665
          3738633237343963643339353833396533626562373934340a626431646537363633
          ...
```

La etiqueta `!vault |` le indica a Ansible que este valor está encriptado. Pegas este bloque en cualquier archivo de variables YAML, y el texto plano circundante permanece legible.

### Incorporando Valores Encriptados en Archivos de Variables

El poder de `encrypt_string` es que los valores encriptados conviven con variables en texto plano en el mismo archivo:

```yaml
---
parasol_db_description: "Production PostgreSQL database"
parasol_db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          63306536653963613135303839343061383532316130623562653463623437376665
          ...
```

Cualquier persona que lea este archivo puede ver que `parasol_db_description` es "Production PostgreSQL database" y que `parasol_db_password` existe y está encriptado. Conocen el nombre de la variable, su propósito por contexto, y que contiene un secreto -- sin ver el valor real. Este es el equilibrio ideal entre transparencia y seguridad.

### Usando Variables Encriptadas en Playbooks

Las variables encriptadas son completamente transparentes para los playbooks. Ansible las desencripta automáticamente cuando se proporciona la contraseña de vault:

```yaml
- name: Display the decrypted database password
  ansible.builtin.debug:
    msg: "Database password is {{ parasol_db_password }}"
    verbosity: 0
```

Sin la contraseña de vault, Ansible se niega a ejecutar:

```text
ERROR! Attempting to decrypt but no vault secrets found
```

## Ansible Vault: Encriptando Archivos

A veces tiene más sentido encriptar un archivo completo en lugar de valores individuales. Esto es apropiado cuando cada variable en un archivo es sensible (por ejemplo, un archivo lleno de credenciales de API) o cuando quieres encriptar contenido que no es YAML como certificados o claves de licencia.

### Encriptando un Archivo

Comienza con un archivo en texto plano:

```yaml
---
parasol_api_key: "l9bTqfBlbXTQiDaJMqgPJ1VdeFLfId98"
parasol_api_secret: "k8mPq2nRtYwXzA3bC5dE7fG9hJ1lN4oQ"
```

Encríptalo en su lugar:

```bash
ansible-vault encrypt \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml
```

El archivo ahora es opaco:

```text
$ANSIBLE_VAULT;1.1;AES256
36313338626336336233626231663835643435393434623535613530636365363034
...
```

### Gestionando Archivos Encriptados

Ansible Vault proporciona cuatro comandos para trabajar con archivos encriptados:

| Comando | Qué hace |
|---------|----------|
| `ansible-vault view` | Desencripta y muestra el contenido sin modificar el archivo |
| `ansible-vault edit` | Desencripta en un archivo temporal, abre en `$EDITOR`, re-encripta al guardar |
| `ansible-vault rekey` | Cambia la contraseña de encriptación sin desencriptar a texto plano |
| `ansible-vault decrypt` | Elimina la encriptación por completo (usar con precaución) |

```bash
# Ver sin modificar
ansible-vault view \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml

# Editar en su lugar
ansible-vault edit \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml

# Cambiar la contraseña
ansible-vault rekey \
  --vault-password-file .vault_password \
  --new-vault-password-file .vault_password_new \
  playbooks/module-06/vars/api_credentials.yml
```

### Encriptación de Variables vs. Archivos

| Aspecto | Encriptación de variables (`encrypt_string`) | Encriptación de archivos (`encrypt`) |
|---------|-----------------------------------------------|--------------------------------------|
| Legibilidad | Contexto en texto plano preservado | Archivo completo es opaco |
| Capacidad de búsqueda | `grep` encuentra nombres de variables | `grep` no encuentra nada útil |
| Granularidad | Mezclar secretos y no-secretos en un archivo | Todo o nada |
| Diffs en control de versiones | Diffs significativos para porciones en texto plano | Diffs son bloques binarios opacos |
| Mejor para | Algunos secretos entre muchas variables | Archivos donde todo es sensible |

En la práctica, la mayoría de los equipos usan encriptación a nivel de variable para inventario y variables de roles, y encriptación a nivel de archivo para certificados, claves de licencia y paquetes de credenciales.

## Gestionando Contraseñas de Vault

La encriptación de Vault es tan fuerte como la gestión de tu contraseña. Hay varias formas de proporcionar la contraseña de vault a Ansible.

### Archivos de Contraseña

El enfoque más simple es un archivo que contiene la contraseña:

```bash
echo 'parasol-vault-password' > .vault_password
chmod 600 .vault_password
```

Úsalo con la bandera `--vault-password-file`:

```bash
ansible-vault encrypt_string \
  --vault-password-file .vault_password \
  'my-secret' --name 'my_variable'
```

!!! danger "Nunca hagas commit de archivos de contraseña de vault"
    Los archivos de contraseña de vault (`.vault_password`, `.vault_password_dev`, etc.) NUNCA deben ser incluidos en control de versiones. Agrégalos a `.gitignore` inmediatamente. Si haces commit de una contraseña de vault junto con archivos encriptados con vault, cualquier persona con acceso al repositorio puede desencriptar todo -- anulando el propósito completo de la encriptación.

### Variables de Entorno

Establece `ANSIBLE_VAULT_PASSWORD_FILE` para evitar pasar `--vault-password-file` en cada comando:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-vault encrypt_string 'my-secret' --name 'my_variable'
```

Esto es especialmente útil en pipelines de CI/CD y entornos de desarrollo compartidos donde la ruta del archivo de contraseña está estandarizada.

### Scripts de Contraseña

Para recuperación dinámica de contraseñas (desde un gestor de contraseñas, servicio de secretos o token de hardware), apunta `--vault-password-file` a un script ejecutable:

```bash
#!/bin/bash
# .vault_password_script.sh
# Obtener contraseña de vault desde un gestor de secretos
pass show ansible/vault-password 2>/dev/null
```

```bash
chmod 700 .vault_password_script.sh
ansible-vault view \
  --vault-password-file .vault_password_script.sh \
  playbooks/module-06/vars/api_credentials.yml
```

Ansible detecta que el archivo es ejecutable y lo ejecuta, usando su salida estándar como contraseña. Esto permite a los equipos integrar vault con cualquier herramienta de gestión de secretos.

### Vault IDs (Vista Previa)

Cuando un proyecto crece para gestionar múltiples entornos, puedes necesitar diferentes contraseñas de vault para dev, staging y producción. Los Vault IDs proporcionan esta capacidad. Cubriremos los Vault IDs en profundidad en el Módulo 10 cuando discutamos empaquetado y despliegue. Por ahora, sabe que el patrón existe y que todas las técnicas de contraseña única que aprendes aquí se extienden naturalmente a configuraciones con múltiples contraseñas.

## Ejecutando Vault con ansible-navigator

A lo largo de este curso, has estado usando `ansible-navigator` para ejecutar playbooks. Vault se integra sin problemas, pero hay algunos patrones específicos de navigator.

### Método 1: Variable de Entorno (Recomendado)

El enfoque más simple es establecer la variable de entorno antes de ejecutar navigator:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-navigator run playbooks/module-06/vault-string-demo.yml --mode stdout
```

La variable de entorno `ANSIBLE_VAULT_PASSWORD_FILE` se pasa automáticamente al entorno de ejecución, así que esto funciona de manera idéntica ya sea que navigator se ejecute localmente o dentro de un contenedor.

### Método 2: Argumentos de Paso Directo

Puedes pasar argumentos de vault directamente al comando `ansible-playbook` subyacente usando `--` como separador:

```bash
ansible-navigator run playbooks/module-06/vault-string-demo.yml \
  --mode stdout -- --vault-password-file .vault_password
```

Todo después de `--` se pasa directamente a `ansible-playbook` sin cambios.

### Comandos de Vault a través de Navigator

Puedes ejecutar comandos de vault dentro del entorno de ejecución usando `ansible-navigator exec`:

```bash
ansible-navigator exec -- ansible-vault encrypt_string \
  --vault-password-file .vault_password 'my-secret' --name 'my_variable'
```

Esto asegura que estés usando la misma versión de Ansible dentro del entorno de ejecución que la que ejecutará tus playbooks.

!!! warning "Los prompts interactivos no funcionan con navigator"
    La bandera `--ask-vault-pass` NO funciona con `ansible-navigator` en modo predeterminado porque los prompts interactivos están deshabilitados. Siempre usa archivos de contraseña o variables de entorno con navigator.

## Plugins de Lookup: Obteniendo Datos desde el Exterior

Vault no es la única forma de manejar datos sensibles. Los **plugins de lookup** te permiten obtener valores de fuentes externas en tiempo de ejecución -- archivos, variables de entorno, comandos o contraseñas generadas. Los lookups complementan a vault manteniendo los secretos fuera de los archivos de variables por completo.

### `ansible.builtin.file` -- Leer un Archivo

Lee el contenido de un archivo en el nodo de control:

```yaml
- name: Read the MOTD banner from a file
  ansible.builtin.debug:
    msg: "{{ lookup('ansible.builtin.file', 'files/motd_banner.txt') }}"
    verbosity: 0
```

Esto es útil para certificados, claves de licencia o cualquier contenido que ya existe como archivo y no debería duplicarse en variables.

### `ansible.builtin.env` -- Leer una Variable de Entorno

Lee una variable de entorno del nodo de control:

```yaml
- name: Read the deploy token from the environment
  ansible.builtin.debug:
    msg: "Deploy token: {{ lookup('ansible.builtin.env', 'PARASOL_DEPLOY_TOKEN') }}"
    verbosity: 0
```

Si la variable no está establecida, el lookup devuelve una cadena vacía por defecto. Puedes hacer que falle ante una variable ausente:

```yaml
msg: "{{ lookup('ansible.builtin.env', 'PARASOL_DEPLOY_TOKEN', default=undef()) }}"
```

### `ansible.builtin.pipe` -- Ejecutar un Comando

Ejecuta un comando en el nodo de control y usa su salida estándar:

```yaml
- name: Get the current user
  ansible.builtin.debug:
    msg: "Running as: {{ lookup('ansible.builtin.pipe', 'whoami') }}"
    verbosity: 0
```

Esto es útil para extraer secretos de herramientas CLI como `pass`, `aws secretsmanager` o `vault` (HashiCorp).

### `ansible.builtin.password` -- Generar o Recuperar una Contraseña

Genera una contraseña aleatoria y opcionalmente almacénala en un archivo:

```yaml
- name: Generate a random password
  ansible.builtin.debug:
    msg: "Generated: {{ lookup('ansible.builtin.password', '/dev/null length=20 chars=ascii_letters,digits') }}"
    verbosity: 0
```

Usar `/dev/null` como ruta genera una nueva contraseña cada vez sin guardarla. Para persistir la contraseña entre ejecuciones, especifica una ruta de archivo:

```yaml
parasol_app_secret: "{{ lookup('ansible.builtin.password', 'credentials/app_secret length=32') }}"
```

Ansible crea el archivo en la primera ejecución y lee la contraseña almacenada en ejecuciones posteriores, asegurando que el valor permanezca consistente.

### `lookup()` vs. `query()`

Verás dos sintaxis para llamar a plugins de lookup:

```yaml
# lookup() devuelve una cadena (separada por comas para múltiples resultados)
msg: "{{ lookup('ansible.builtin.file', 'file1.txt', 'file2.txt') }}"

# query() devuelve una lista (útil en loops)
loop: "{{ query('ansible.builtin.file', 'file1.txt', 'file2.txt') }}"
```

Usa `lookup()` cuando necesites un único valor de cadena. Usa `query()` cuando necesites una lista, especialmente en construcciones `loop:`.

!!! info "Los lookups se ejecutan en el nodo de control"
    Todos los plugins de lookup se ejecutan en el nodo de control de Ansible, no en los hosts destino. El lookup `ansible.builtin.env` lee variables de entorno de la máquina que ejecuta Ansible. Si necesitas leer un archivo o variable de entorno de un host remoto, usa el módulo `ansible.builtin.slurp` o `ansible.builtin.command` con `register` en su lugar.

## Protegiendo la Salida Sensible: `no_log`

Vault protege los secretos en reposo, pero ¿qué pasa en tiempo de ejecución? Cuando Ansible ejecuta una tarea, registra los parámetros y resultados de la tarea en la consola, archivos de log y plugins de callback. Si una tarea maneja una contraseña, el valor en texto plano puede aparecer en la salida.

La directiva `no_log: true` suprime toda la salida de una tarea:

```yaml
- name: Create application database user
  community.postgresql.postgresql_user:
    name: "parasol_app"
    password: "{{ parasol_db_password }}"
    state: present
  no_log: true
```

Con `no_log: true`, Ansible reemplaza la salida de la tarea con `censored`:

```text
TASK [Create application database user] ****
ok: [db-01] => {"censored": "the output has been hidden due to the fact
that 'no_log: true' was specified for this result"}
```

Sin ella, la contraseña aparece en la salida:

```text
TASK [Create application database user] ****
ok: [db-01] => {"changed": false, "password": "Sup3rS3cret!", ...}
```

### Cuándo Usar `no_log`

Usa `no_log: true` en cualquier tarea que maneje valores sensibles:

- Tareas que pasan contraseñas como parámetros
- Tareas que establecen claves API o tokens en configuración
- Tareas que usan `ansible.builtin.uri` con encabezados de autenticación
- Tareas que iteran sobre una lista que contiene secretos

!!! tip "ansible-lint detecta no_log faltante"
    La herramienta `ansible-lint` (que aprenderás en el Módulo 9) incluye una regla llamada `no-log-password` que marca tareas con parámetros de contraseña sin `no_log: true`. Esta es una red de seguridad automatizada -- pero entender por qué `no_log` importa es más importante que depender del linter para detectarlo.

### El Compromiso de Depuración

`no_log: true` dificulta la depuración porque no puedes ver los parámetros o resultados de la tarea. Cuando estés solucionando problemas de una tarea que falla, puedes necesitar eliminar temporalmente `no_log` en un entorno de desarrollo, diagnosticar el problema y luego restaurarlo. Nunca dejes `no_log` deshabilitado en playbooks de producción.

## Mejores Prácticas: Qué Encriptar con Vault y Qué No

No todo necesita encriptación. Encriptar en exceso crea fricción (cada desarrollador necesita la contraseña de vault para ejecutar cualquier playbook), y encriptar de menos deja secretos expuestos.

### Qué Encriptar

- Contraseñas y frases de paso
- Claves API y tokens
- Claves privadas y certificados TLS/SSL
- Cadenas de conexión a bases de datos con credenciales
- Claves privadas SSH
- Claves de licencia

### Qué NO Encriptar

- Nombres de paquetes (`parasol_packages`)
- Números de puerto (`parasol_http_port: 8080`)
- Banderas de funcionalidad (`parasol_monitoring_enabled: true`)
- Rutas de archivos (`parasol_log_dir: "/var/log/parasol"`)
- Valores de configuración no sensibles

La regla es simple: si el valor causaría un incidente de seguridad si se expone, encríptalo. Todo lo demás permanece en texto plano por legibilidad y facilidad de uso.

### El Patrón de Prefijo `vault_`

Cuando encriptas variables individuales, los nombres de variables permanecen visibles y buscables. Pero cuando encriptas archivos completos (como `group_vars/production/vault.yml`), `grep` no puede encontrar nada dentro de ellos.

El patrón recomendado divide las variables en dos archivos por grupo:

```text
group_vars/production/
    vars.yml          # Referencias en texto plano (buscables)
    vault.yml         # Valores encriptados
```

En `vault.yml` (encriptado):

```yaml
vault_parasol_db_password: "Sup3rS3cret!"
```

En `vars.yml` (texto plano):

```yaml
parasol_db_password: "{{ vault_parasol_db_password }}"
```

De esta manera, `grep parasol_db_password` encuentra la referencia en `vars.yml`, y el valor real está encriptado de forma segura en `vault.yml`. Ansible carga automáticamente ambos archivos del directorio del grupo y resuelve la referencia en tiempo de ejecución.

### Vault en Control de Versiones

Los archivos encriptados con Vault son seguros para incluir en control de versiones. El contenido encriptado es un bloque opaco AES-256 -- sin la contraseña de vault, es computacionalmente inviable recuperar el texto plano. Esta es la diferencia clave con el problema de texto plano con el que empezamos: los secretos encriptados en el historial de Git no son un riesgo de seguridad.

### Rotación de Contraseñas con `rekey`

Cuando necesites cambiar la contraseña de vault (por ejemplo, cuando un miembro del equipo se va), usa `ansible-vault rekey` para re-encriptar todos los archivos protegidos con vault con una nueva contraseña. Esta es la forma correcta de rotar contraseñas de vault -- no necesitas desencriptar y re-encriptar cada archivo manualmente.

## Ejercicios

### Ejercicio 1: Encriptar una Variable con `ansible-vault encrypt_string`

Crea un archivo de contraseña de vault y encripta una contraseña de base de datos:

```bash
cd ansible
echo 'parasol-vault-password' > .vault_password
chmod 600 .vault_password
```

Encripta un valor:

```bash
ansible-vault encrypt_string \
  --vault-password-file .vault_password \
  'Sup3rS3cret!' \
  --name 'parasol_db_password'
```

Copia la salida. Abre `playbooks/module-06/vars/db_secrets.yml` y compáralo con la salida -- este archivo ya tiene el valor encriptado incorporado junto a una variable en texto plano.

Ahora ejecuta el playbook acompañante:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-navigator run playbooks/module-06/vault-string-demo.yml --mode stdout
```

Intenta ejecutarlo sin la contraseña de vault:

```bash
unset ANSIBLE_VAULT_PASSWORD_FILE
ansible-navigator run playbooks/module-06/vault-string-demo.yml --mode stdout
```

Deberías ver `ERROR! Attempting to decrypt but no vault secrets found`. Esto confirma que el valor encriptado no puede usarse sin la contraseña correcta.

### Ejercicio 2: Encriptar y Gestionar un Archivo Completo

Crea un archivo de secretos en texto plano:

```bash
cat > playbooks/module-06/vars/api_credentials.yml << 'EOF'
---
parasol_api_key: "l9bTqfBlbXTQiDaJMqgPJ1VdeFLfId98"
parasol_api_secret: "k8mPq2nRtYwXzA3bC5dE7fG9hJ1lN4oQ"
EOF
```

Encríptalo:

```bash
ansible-vault encrypt \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml
```

Visualiza el archivo encriptado con `cat` -- deberías ver el encabezado `$ANSIBLE_VAULT;1.1;AES256` seguido de datos codificados en hexadecimal:

```bash
cat playbooks/module-06/vars/api_credentials.yml
```

Ahora visualiza el contenido desencriptado:

```bash
ansible-vault view \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml
```

Edita el archivo y agrega una tercera variable (`parasol_api_endpoint: "https://api.parasol.example"`):

```bash
ansible-vault edit \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml
```

Ejecuta el playbook acompañante:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-navigator run playbooks/module-06/vault-file-demo.yml --mode stdout
```

### Ejercicio 3: Vault en group_vars del Inventario

Este ejercicio usa el patrón recomendado de archivos divididos para gestionar secretos en inventarios estructurados.

Examina los dos archivos que se han configurado en `inventory/group_vars/production/`:

- `vars.yml` -- referencias en texto plano
- `vault.yml` -- valores encriptados

```bash
cat inventory/group_vars/production/vars.yml
ansible-vault view \
  --vault-password-file .vault_password \
  inventory/group_vars/production/vault.yml
```

Ejecuta el playbook acompañante:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-navigator run playbooks/module-06/vault-groupvars-demo.yml --mode stdout
```

Verifica que `grep` puede encontrar el nombre de la variable en el archivo de texto plano:

```bash
grep parasol_db_password inventory/group_vars/production/vars.yml
```

Deberías ver la referencia `parasol_db_password: "{{ vault_parasol_db_password }}"`. El valor real está encriptado en `vault.yml`, pero el nombre de la variable es buscable en `vars.yml`. Este es el patrón recomendado para inventarios de producción.

### Ejercicio 4: Plugins de Lookup

Establece una variable de entorno para la demostración del lookup `env`:

```bash
export PARASOL_DEPLOY_TOKEN="token-abc-123"
```

Ejecuta el playbook de lookups:

```bash
ansible-navigator run playbooks/module-06/lookups-demo.yml --mode stdout
```

Observa los cuatro lookups en acción:

1. **`ansible.builtin.file`** lee el banner desde `files/motd_banner.txt`
2. **`ansible.builtin.env`** lee `PARASOL_DEPLOY_TOKEN` del entorno
3. **`ansible.builtin.pipe`** ejecuta `whoami` y captura la salida
4. **`ansible.builtin.password`** genera una contraseña aleatoria de 20 caracteres

Intenta desestablecer la variable de entorno y ejecutar nuevamente:

```bash
unset PARASOL_DEPLOY_TOKEN
ansible-navigator run playbooks/module-06/lookups-demo.yml --mode stdout
```

Nota que el lookup `env` devuelve una cadena vacía en lugar de fallar. En producción, usarías `default=undef()` para hacer que una variable ausente sea un error.

### Ejercicio 5: Protegiendo la Salida con `no_log`

Ejecuta el playbook de demostración de no-log:

```bash
ansible-navigator run playbooks/module-06/no-log-demo.yml --mode stdout
```

Observa la diferencia entre las dos tareas:

1. La tarea **sin protección** muestra el valor de la contraseña en la salida
2. La tarea **protegida** muestra `censored` en su lugar

Ahora edita `playbooks/module-06/no-log-demo.yml` y agrega `no_log: true` a la tarea sin protección. Ejecútalo nuevamente y confirma que ambas tareas ahora muestran `censored`.

Esta es la protección de "datos en uso" que complementa la encriptación de "datos en reposo" de Vault. Siempre usa `no_log: true` en tareas que manejan valores sensibles.

## Resumen

En este módulo:

- Entendiste por qué los secretos en texto plano en control de versiones son peligrosos -- incluso después de eliminarlos, persisten en el historial de Git
- Encriptaste valores de variables individuales con `ansible-vault encrypt_string` y los incorporaste en archivos YAML legibles
- Encriptaste archivos completos con `ansible-vault encrypt` y los gestionaste con `view`, `edit`, `rekey` y `decrypt`
- Gestionaste contraseñas de vault con archivos de contraseña, variables de entorno y scripts ejecutables
- Ejecutaste playbooks protegidos con vault usando `ansible-navigator` con `ANSIBLE_VAULT_PASSWORD_FILE` y argumentos de paso directo
- Usaste cuatro plugins de lookup (`file`, `env`, `pipe`, `password`) para obtener datos desde fuera de los playbooks en tiempo de ejecución
- Protegiste la salida sensible de las tareas en logs usando `no_log: true`
- Aplicaste el patrón de prefijo `vault_` para mantener los nombres de variables buscables mientras los valores permanecen encriptados

Lionel y Jordan han asegurado cada secreto en el repositorio de Parasol Tech. Las contraseñas están encriptadas con Vault, las claves API se obtienen desde variables de entorno, y `no_log` previene que los valores sensibles se filtren en los logs. El equipo de seguridad está satisfecho, y el equipo tiene un marco de decisión claro para qué encriptar y qué dejar en texto plano.

## Próximos Pasos

Siguiente: [Módulo 8 -- Roles y Colecciones](8-roles-and-collections.md)
