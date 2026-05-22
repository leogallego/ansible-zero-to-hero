# Módulo 3: Gestión del Inventario

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Crear directorios de inventario estructurados con grupos y grupos anidados
- Definir variables de host y de grupo en archivos dedicados
- Seleccionar hosts específicos usando patrones y `--limit`
- Explicar la diferencia entre inventario estático y dinámico

## La Historia Hasta Ahora

Lionel tiene tres playbooks funcionando, pero todos apuntan a `localhost`. En el mundo real, Parasol Tech tiene docenas de servidores distribuidos en tres entornos (desarrollo, staging y producción) ejecutando diferentes servicios. Servidores web, servidores de base de datos, servidores de aplicaciones: cada entorno tiene su propio conjunto.

Lionel necesita una forma de decirle a Ansible sobre todos estos hosts, organizarlos lógicamente y asignar diferentes valores de configuración según el entorno y el rol del servidor. Esto es lo que hace el **inventario**.

## Qué es un Inventario?

Un inventario es la lista de hosts que Ansible gestiona, junto con metadatos sobre esos hosts (a qué grupos pertenecen, qué variables se les aplican). Sin un inventario, Ansible no tiene idea de qué máquinas existen ni cómo conectarse a ellas.

En el Módulo 1, usamos un inventario mínimo con una sola entrada:

```yaml
---
all:
  hosts:
    localhost:
      ansible_connection: local
```

Eso fue suficiente para empezar, pero la infraestructura de Parasol Tech se parece más a esto:

```text
Infraestructura de Parasol Tech
├── Desarrollo
│   ├── web01.dev.parasol.example
│   ├── web02.dev.parasol.example
│   └── db01.dev.parasol.example
├── Staging
│   ├── web01.staging.parasol.example
│   ├── web02.staging.parasol.example
│   └── db01.staging.parasol.example
└── Producción
    ├── web01.prod.parasol.example
    ├── web02.prod.parasol.example
    ├── web03.prod.parasol.example
    ├── db01.prod.parasol.example
    └── db02.prod.parasol.example
```

Aprendamos cómo representar esto en Ansible.

## Formatos de Inventario Estático

Un **inventario estático** es un archivo que escribes y mantienes a mano. Ansible soporta dos formatos: INI y YAML. Ambos logran el mismo resultado; la elección es cuestión de preferencia.

=== "Formato YAML (recomendado)"

    ```yaml
    ---
    all:
      hosts:
        localhost:
          ansible_connection: local

      children:
        webservers:
          hosts:
            web01.dev.parasol.example:
            web02.dev.parasol.example:
        dbservers:
          hosts:
            db01.dev.parasol.example:
    ```

    Los inventarios YAML usan la misma sintaxis que los playbooks. Los grupos se anidan bajo `children:` y los hosts se listan bajo `hosts:`. Los dos puntos al final de cada nombre de host son obligatorios: marcan el host como una clave sin valores en línea.

=== "Formato INI"

    ```ini
    localhost ansible_connection=local

    [webservers]
    web01.dev.parasol.example
    web02.dev.parasol.example

    [dbservers]
    db01.dev.parasol.example
    ```

    Los inventarios INI usan encabezados de sección entre corchetes para los grupos y listan los hosts uno por línea. Las variables se agregan en línea después del nombre del host.

!!! tip "¿Qué formato deberías usar?"
    Este curso usa YAML para todos los inventarios. YAML es más explícito, soporta anidamiento profundo de forma natural y usa la misma sintaxis que ya conoces de los playbooks. El formato INI es más simple para inventarios muy pequeños pero se vuelve difícil de leer a medida que crece la complejidad.

### El Grupo `all`

Cada host en un inventario de Ansible pertenece automáticamente al grupo `all`. No necesitas agregarlo explícitamente; cualquier host definido en cualquier parte del inventario es miembro de `all`. Esto hace que `all` sea útil para variables que deben aplicarse a todos los hosts (lo veremos en breve con `group_vars/all.yml`).

También existe un grupo `ungrouped` que contiene hosts que no son miembros de ningún otro grupo (además de `all`).

## Grupos y Grupos Anidados

Los grupos te permiten organizar hosts para poder seleccionarlos de forma selectiva. En lugar de ejecutar un playbook contra todos los hosts, puedes apuntar solo a `webservers` o solo a `production`.

### Grupos Simples

La agrupación más básica coloca hosts en categorías por función:

```yaml
---
all:
  children:
    webservers:
      hosts:
        web01.dev.parasol.example:
        web02.dev.parasol.example:
    dbservers:
      hosts:
        db01.dev.parasol.example:
```

Ahora puedes ejecutar un playbook con `hosts: webservers` y solo se ejecutará en los servidores web, o con `hosts: dbservers` solo en los servidores de base de datos.

### Grupos Anidados (Grupos de Grupos)

La infraestructura real necesita organizarse en múltiples dimensiones. Los servidores de Parasol Tech pertenecen tanto a un **entorno** (dev, staging, producción) como a una **función** (webservers, dbservers). Los grupos anidados manejan esto permitiendo que un grupo contenga otros grupos como hijos.

Así está estructurado el inventario del curso (`ansible/inventory/hosts.yml`):

```yaml
---
all:
  hosts:
    localhost:
      ansible_connection: local

  children:
    # Grupos de entorno
    dev:
      children:
        dev_webservers:
          hosts:
            web01.dev.parasol.example:
            web02.dev.parasol.example:
        dev_dbservers:
          hosts:
            db01.dev.parasol.example:

    staging:
      children:
        staging_webservers:
          hosts:
            web01.staging.parasol.example:
            web02.staging.parasol.example:
        staging_dbservers:
          hosts:
            db01.staging.parasol.example:

    production:
      children:
        prod_webservers:
          hosts:
            web01.prod.parasol.example:
            web02.prod.parasol.example:
            web03.prod.parasol.example:
        prod_dbservers:
          hosts:
            db01.prod.parasol.example:
            db02.prod.parasol.example:

    # Grupos funcionales (abarcan todos los entornos)
    webservers:
      children:
        dev_webservers:
        staging_webservers:
        prod_webservers:

    dbservers:
      children:
        dev_dbservers:
        staging_dbservers:
        prod_dbservers:
```

Esta estructura le da a Lionel la máxima flexibilidad:

| Objetivo | Hosts alcanzados |
|----------|-----------------|
| `hosts: all` | Todos los hosts |
| `hosts: production` | Todos los hosts de producción (web + db) |
| `hosts: webservers` | Todos los servidores web en todos los entornos |
| `hosts: prod_webservers` | Solo servidores web de producción |
| `hosts: dev` | Todos los hosts de desarrollo |

!!! info "Un host puede pertenecer a múltiples grupos"
    `web01.dev.parasol.example` es miembro de `dev_webservers`, `dev`, `webservers` y `all`, todo al mismo tiempo. Esto es por diseño. La jerarquía de grupos crea conjuntos superpuestos que te permiten seleccionar hosts desde diferentes ángulos.

### Convención de Nombres de Grupos

Observa el patrón de nombres: `dev_webservers`, `staging_dbservers`, `prod_webservers`. Usar guiones bajos y prefijos consistentes mantiene los nombres de grupos predecibles y facilita la construcción de patrones. Nunca uses guiones en nombres de grupos; pueden causar problemas con la resolución de variables.

## Variables de Host y de Grupo

Las variables te permiten asignar diferentes valores de configuración a diferentes hosts o grupos de hosts. Ansible proporciona una separación limpia a través de dos mecanismos: **variables de host** y **variables de grupo**.

### La Regla: Sin Variables en el Archivo de Hosts

Una buena práctica fundamental: **nunca pongas definiciones de variables en el archivo de hosts del inventario**. El archivo de hosts debe contener solo hosts y grupos. Las variables van en archivos separados.

Esta separación tiene beneficios prácticos:

- Las variables son más fáciles de encontrar, leer y revisar
- Puedes cambiar variables sin tocar la lista de hosts
- Fomenta organizar las variables por alcance (todos los hosts vs. un grupo vs. un host)
- Los diffs en control de versiones son más limpios: puedes ver que una variable cambió sin navegar por la lista de hosts

### Variables de Grupo (`group_vars/`)

Las variables de grupo se aplican a cada host en un grupo. Se definen en archivos dentro del directorio `group_vars/`, con un archivo por grupo.

Para el inventario de Parasol Tech, el directorio `group_vars/` se ve así:

```text
ansible/inventory/
├── hosts.yml
├── group_vars/
│   ├── all.yml          # Se aplica a todos los hosts
│   ├── dev.yml          # Se aplica al grupo dev
│   ├── staging.yml      # Se aplica al grupo staging
│   └── production.yml   # Se aplica al grupo production
└── host_vars/
    ├── db01.prod.parasol.example.yml
    └── db02.prod.parasol.example.yml
```

**`group_vars/all.yml`**: variables para todos los hosts:

```yaml
---
parasol_organization: "Parasol Tech"
parasol_ntp_server: "ntp.parasol.example"
parasol_dns_servers:
  - "10.0.0.10"
  - "10.0.0.11"
parasol_admin_email: "platform-team@parasol.example"
```

**`group_vars/dev.yml`**: variables solo para el entorno de desarrollo:

```yaml
---
parasol_environment: "dev"
parasol_log_level: "debug"
parasol_monitoring_enabled: false
parasol_backup_schedule: "weekly"
```

**`group_vars/production.yml`**: variables para el entorno de producción:

```yaml
---
parasol_environment: "production"
parasol_log_level: "warning"
parasol_monitoring_enabled: true
parasol_backup_schedule: "hourly"
```

Cuando Ansible se ejecuta contra `web01.dev.parasol.example`, fusiona las variables de `all.yml` y `dev.yml`. El host recibe tanto `parasol_organization` (de `all`) como `parasol_log_level: debug` (de `dev`). Un host de producción recibe `parasol_log_level: warning` en su lugar.

### Variables de Host (`host_vars/`)

Las variables de host se aplican a un solo host. Se definen en archivos nombrados según el host dentro del directorio `host_vars/`.

**`host_vars/db01.prod.parasol.example.yml`**:

```yaml
---
parasol_db_role: "primary"
parasol_db_max_connections: 500
parasol_db_backup_retention_days: 30
```

**`host_vars/db02.prod.parasol.example.yml`**:

```yaml
---
parasol_db_role: "replica"
parasol_db_max_connections: 200
parasol_db_backup_retention_days: 7
```

Aunque ambos servidores de base de datos están en el grupo `production` y comparten las mismas variables de grupo, tienen diferentes roles (primario vs. réplica) y diferentes límites de conexión. Las variables de host manejan estas diferencias por host.

### Precedencia de Variables (Adelanto)

Cuando la misma variable se define en múltiples niveles, Ansible sigue un orden de precedencia. Para variables de inventario, la regla es simple:

**Las variables de host sobreescriben las variables de grupo, y las variables de grupo sobreescriben las variables de `all`.**

Por ejemplo, si `group_vars/all.yml` establece `parasol_log_level: info` y `group_vars/dev.yml` establece `parasol_log_level: debug`, un host de desarrollo obtiene `debug` porque el grupo más específico gana.

Cubriremos el sistema completo de precedencia de variables en el Módulo 4. Por ahora, recuerda: lo más específico gana.

## Directorios de Inventario Estructurados

Ya has visto la estructura. Hagámosla explícita. Un **directorio de inventario estructurado** separa hosts, variables de grupo y variables de host en sus propios archivos y directorios:

```text
inventory/
├── hosts.yml              # Definiciones de hosts y grupos (sin variables)
├── group_vars/
│   ├── all.yml            # Variables para todos los hosts
│   ├── dev.yml            # Variables para el grupo dev
│   ├── staging.yml        # Variables para el grupo staging
│   └── production.yml     # Variables para el grupo production
└── host_vars/
    ├── db01.prod.parasol.example.yml
    └── db02.prod.parasol.example.yml
```

### ¿Por Qué No un Solo Archivo?

*Puedes* poner todo en un solo archivo (hosts, grupos y todas las variables en línea). Pero no deberías, por las mismas razones por las que no pones una aplicación entera en un solo archivo:

| Inventario en un solo archivo | Directorio estructurado |
|------------------------------|------------------------|
| Todo en un lugar, difícil de navegar | Organizado por alcance, fácil encontrar lo que necesitas |
| Un cambio = un diff grande | Los cambios están aislados en archivos específicos |
| Definiciones de variables mezcladas con listas de hosts | Separación limpia de responsabilidades |
| Difícil compartir variables entre inventarios | Los archivos de `group_vars/` se pueden enlazar o usar como plantilla |

### Apuntando Ansible al Inventario

En `ansible.cfg`, la configuración `inventory` le dice a Ansible dónde encontrar el inventario:

```ini
[defaults]
inventory = inventory/hosts.yml
```

Cuando apuntas a un archivo dentro de un directorio que también contiene `group_vars/` y `host_vars/`, Ansible carga automáticamente las variables de esos directorios. Por eso el enfoque de directorio estructurado funciona sin ninguna configuración adicional.

!!! info "Ruta de directorio vs. ruta de archivo"
    También puedes apuntar `inventory` al directorio mismo (`inventory = inventory/`). El comportamiento es casi idéntico: Ansible carga todos los archivos de inventario válidos en el directorio junto con `group_vars/` y `host_vars/`. Apuntar al archivo específico es más explícito y evita cargar archivos no deseados accidentalmente.

## Selección de Hosts

Una vez que tienes un inventario con grupos, puedes seleccionar contra qué hosts se ejecuta un playbook usando **patrones de host** y el flag `--limit`.

### Patrones de Host en Playbooks

La directiva `hosts:` en un play acepta patrones, no solo nombres de grupos:

```yaml
# Apuntar a un solo grupo
- hosts: webservers

# Apuntar a múltiples grupos (unión)
- hosts: webservers:dbservers

# Apuntar a la intersección de dos grupos (hosts en AMBOS)
- hosts: staging:&webservers

# Apuntar a un grupo pero excluir otro
- hosts: production:!dbservers
```

| Patrón | Significado |
|--------|------------|
| `webservers` | Todos los hosts en el grupo webservers |
| `webservers:dbservers` | Hosts en webservers O dbservers |
| `staging:&webservers` | Hosts en AMBOS staging Y webservers |
| `production:!dbservers` | Hosts en production pero NO en dbservers |
| `web*.prod.parasol.example` | Hosts que coinciden con el comodín |
| `all` | Todos los hosts en el inventario |

### El Flag `--limit`

El flag `--limit` (o `-l`) reduce los hosts que un playbook selecciona en tiempo de ejecución, sin cambiar el playbook. Esto es especialmente útil para:

- Probar un playbook contra un host antes de desplegarlo a un grupo
- Ejecutar en producción en un subconjunto de hosts a la vez (actualizaciones progresivas)
- Diagnosticar problemas en un solo host

```bash
# Ejecutar solo contra web01 en producción
ansible-navigator run playbooks/deploy.yml --mode stdout --limit web01.prod.parasol.example

# Ejecutar solo contra el entorno de desarrollo
ansible-navigator run playbooks/deploy.yml --mode stdout --limit dev

# Ejecutar contra webservers solo en staging
ansible-navigator run playbooks/deploy.yml --mode stdout --limit 'staging:&webservers'
```

!!! warning "Usa comillas en patrones con caracteres especiales"
    Cuando uses `:`, `&`, `!` o `*` en patrones de limit en la línea de comandos, envuelve el patrón entre comillas para evitar que el shell los interprete.

### Listar Hosts Sin Ejecutar

Puedes previsualizar qué hosts seleccionaría un playbook sin ejecutarlo:

```bash
# Listar todos los hosts en el inventario
ansible-navigator inventory --list --mode stdout

# Listar hosts en un grupo específico
ansible-navigator inventory --graph production --mode stdout

# Mostrar qué hosts seleccionaría un playbook
ansible-navigator run playbooks/deploy.yml --mode stdout --list-hosts
```

La opción `--graph` muestra la jerarquía de grupos como un árbol, lo cual es una excelente forma de verificar la estructura de tu inventario.

## Conceptos de Inventario Dinámico

Todo lo que hemos cubierto hasta ahora es **inventario estático**: escribes la lista de hosts a mano y la actualizas manualmente cuando se agregan o eliminan hosts. Esto funciona bien para entornos pequeños y estables.

Pero ¿qué pasa con entornos en la nube donde las máquinas virtuales se crean y destruyen automáticamente? ¿O entornos grandes con cientos de hosts gestionados por un CMDB (Base de Datos de Gestión de Configuración)?

Aquí es donde entra el **inventario dinámico**. Un inventario dinámico es un script o plugin que consulta una fuente externa y genera el inventario sobre la marcha.

### Cómo Funciona el Inventario Dinámico

En lugar de apuntar `inventory` a un archivo estático, apuntas a un script o configuras un plugin de inventario. Cuando Ansible se ejecuta, ejecuta el script (o llama al plugin), que devuelve la lista de hosts y variables en formato JSON.

Las fuentes comunes de inventario dinámico incluyen:

| Fuente | Caso de Uso |
|--------|------------|
| AWS EC2 | Instancias en la nube de Amazon Web Services |
| Azure RM | Máquinas virtuales en Microsoft Azure |
| GCP Compute | Instancias en Google Cloud Platform |
| Red Hat Satellite | Hosts gestionados por Satellite |
| NetBox | Hosts registrados en una fuente de verdad de red |
| ServiceNow CMDB | Gestión de servicios de TI empresarial |

### Estático + Dinámico Juntos

Puedes combinar inventarios estáticos y dinámicos apuntando `inventory` a un directorio que contenga tanto un archivo estático como un script de inventario dinámico o configuración de plugin. Ansible fusiona los resultados.

Esto es común en la práctica: mantienes un inventario estático para hosts que no existen en una fuente dinámica, y usas un plugin para el resto.

!!! info "Inventario dinámico en este curso"
    No configuraremos inventario dinámico en este curso porque requiere acceso a un servicio externo (un proveedor de nube, un CMDB, etc.). Lo importante es entender el concepto: el inventario puede generarse programáticamente desde cualquier fuente. Los patrones de grupos y variables que aprendes con inventario estático se aplican igualmente al inventario dinámico.

## Ejercicios

### Ejercicio 1: Explorar el Inventario

Navega al directorio `ansible/` y ejecuta el playbook de verificación de inventario:

```bash
cd ansible
ansible-navigator run playbooks/module-03/check-inventory.yml --mode stdout
```

Examina la salida. Deberías ver:

- Todos los grupos definidos
- Hosts en cada grupo de entorno (dev, staging, production)
- Hosts en cada grupo funcional (webservers, dbservers)
- Variables de `group_vars/all.yml`
- El conteo total de hosts

### Ejercicio 2: Ver el Grafo del Inventario

Usa `ansible-navigator` para visualizar la jerarquía del inventario:

```bash
ansible-navigator inventory --graph --mode stdout
```

Deberías ver un árbol mostrando cómo están anidados los grupos. Prueba graficar un grupo específico:

```bash
ansible-navigator inventory --graph production --mode stdout
```

### Ejercicio 3: Practicar con `--limit`

Ejecuta el playbook check-inventory con diferentes valores de `--limit` y observa cómo cambia la salida:

```bash
# Apuntar solo a localhost (el único host al que podemos conectarnos)
ansible-navigator run playbooks/module-03/check-inventory.yml --mode stdout --limit localhost

# Ver qué pasaría si apuntáramos a producción
ansible-navigator run playbooks/module-03/check-inventory.yml --mode stdout --limit production --list-hosts
```

### Ejercicio 4: Agregar un Archivo de Variables de Grupo

Crea un nuevo archivo `ansible/inventory/group_vars/webservers.yml` con variables específicas para servidores web:

```yaml
---
parasol_http_port: 8080
parasol_max_connections: 1000
parasol_document_root: "/var/www/html"
```

Ejecuta el playbook check-inventory de nuevo. ¿Puedes modificar el playbook para mostrar estas nuevas variables? (Pista: agrega una nueva tarea `ansible.builtin.debug`.)

### Ejercicio 5: Inspeccionar Variables de Host

Ejecuta el siguiente comando para ver todas las variables que Ansible asignaría a un host específico:

```bash
ansible-navigator inventory --host db01.prod.parasol.example --mode stdout
```

Observa cómo la salida incluye variables de `group_vars/all.yml`, `group_vars/production.yml` y `host_vars/db01.prod.parasol.example.yml`, todas fusionadas.

## Resumen

En este módulo:

- Aprendiste los dos formatos de inventario estático (INI y YAML) y por qué se prefiere YAML
- Construiste un inventario estructurado con grupos anidados por entorno y función
- Separaste las variables en directorios `group_vars/` y `host_vars/`, nunca en el archivo de hosts
- Usaste patrones de host y `--limit` para seleccionar subconjuntos específicos de hosts
- Viste cómo los comandos `ansible-navigator inventory` ayudan a verificar y explorar la estructura del inventario
- Entendiste el concepto de inventario dinámico y cuándo usarlo

Lionel ahora tiene un inventario que representa toda la infraestructura de Parasol Tech. Cada entorno tiene sus propios valores de configuración, y hosts específicos pueden tener configuraciones únicas. El siguiente desafío: cómo usar esas variables para hacer que los playbooks se adapten a diferentes hosts y entornos.

## Próximos Pasos

Siguiente: [Módulo 4 -- Variables y Facts](4-variables-and-facts.md)
