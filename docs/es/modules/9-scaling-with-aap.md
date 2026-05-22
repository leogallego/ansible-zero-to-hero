# Modulo 9: Escalando con AAP

## Objetivos de Aprendizaje

Al finalizar este modulo seras capaz de:

- Describir los componentes de Ansible Automation Platform (Controller, Hub, EDA)
- Crear job templates y workflows en Controller
- Configurar inventarios y credenciales en Controller
- Establecer RBAC con equipos, roles y permisos
- Integrar Execution Environments con Controller
- Configurar la sincronizacion de proyectos con verificacion de contenido

## La Historia Hasta Ahora

La CoP en Parasol Tech ha recorrido un largo camino. El equipo tiene una coleccion probada, verificada y firmada -- `parasoltech.infrastructure`. Se distribuye dentro de un Execution Environment personalizado construido con `ansible-builder`. Cada cambio pasa por `ansible-lint`, Molecule, pytest y tox-ansible antes de fusionarse. El contenido esta firmado con `ansible-sign` para que nadie pueda manipular los playbooks entre la revision y la ejecucion.

Pero un nuevo problema esta surgiendo. Alex ejecuta el despliegue del servidor web desde un portatil. Jordan ejecuta el playbook de parcheado desde otro portatil. Un tercer miembro del equipo ejecuta comandos ad-hoc desde un jump host. Nadie tiene visibilidad sobre que se ejecuto, cuando, quien lo ejecuto, ni si tuvo exito. No hay registro de auditoria, no hay control de acceso, y no hay forma de programar trabajos recurrentes.

"Ejecute el playbook de respaldo de la base de datos ayer," dice Jordan. "Pero use `--limit staging` en lugar de `--limit production`. Nadie lo noto hasta esta manana."

Alex frunce el ceno. "Y no tengo forma de saber quien ejecuto que en los servidores de produccion la semana pasada. Necesitamos un plano de control."

La CoP coincide: la ejecucion por CLI no escala. Necesitan orquestacion centralizada con gobernanza, registro de auditoria, control de acceso basado en roles, y la capacidad de encadenar automatizacion en flujos de trabajo de multiples pasos. Necesitan **Ansible Automation Platform**.

## Vision General de AAP

Ansible Automation Platform (AAP) es la plataforma empresarial de Red Hat para gestionar la automatizacion de Ansible a escala. Toma las herramientas de CLI que has usado a lo largo de este curso y agrega un plano de control centralizado con interfaz web, API REST, RBAC, registro de auditoria, gestion de credenciales y orquestacion de flujos de trabajo.

AAP tiene tres componentes principales:

### Controller

**Automation Controller** (anteriormente Ansible Tower) es la capa de gestion central. Proporciona:

- **Job Templates** -- definiciones reutilizables para ejecutar playbooks con inventarios, credenciales y variables especificas
- **Workflows** -- pipelines de automatizacion de multiples pasos que encadenan job templates con logica condicional
- **Inventarios** -- gestion centralizada de hosts con fuentes estaticas, proveedores dinamicos e inventario sincronizado desde sistemas externos
- **Credenciales** -- almacenamiento seguro para claves SSH, tokens API, credenciales de nube y contrasenas de vault -- se acabaron los secretos en portatiles individuales
- **RBAC** -- equipos, roles y permisos granulares que controlan quien puede ejecutar que en cuales hosts
- **Registro de auditoria** -- cada ejecucion de trabajo se registra con quien la inicio, que se ejecuto, cuando comenzo, cuanto tardo y cual fue el resultado
- **Programacion** -- ejecutar trabajos en un horario recurrente sin intervencion humana
- **API REST** -- todo lo disponible en la interfaz tambien esta disponible via API, permitiendo integracion con pipelines de CI/CD, sistemas de tickets y herramientas personalizadas

Controller es donde la CoP realizara la mayor parte de su trabajo. Reemplaza el patron de "conectarse por SSH a un servidor y ejecutar `ansible-playbook`" con un flujo de trabajo gobernado y auditable.

### Automation Hub

**Private Automation Hub** es el repositorio interno de contenido de la organizacion. Cumple dos propositos:

1. **Registro de colecciones** -- Los equipos publican colecciones en Hub en lugar de compartir tarballs o apuntar a repositorios Git. Otros equipos instalan colecciones desde Hub usando `ansible-galaxy`. Hub puede alojar colecciones certificadas (de Red Hat y socios), colecciones comunitarias validadas y las colecciones privadas de la organizacion como `parasoltech.infrastructure`.

2. **Registro de contenedores EE** -- Hub almacena imagenes de Execution Environments. Controller obtiene las imagenes EE de Hub cuando ejecuta trabajos, asegurando que cada ejecucion use la imagen aprobada y probada. Aqui es donde se publicaria el EE construido en el Modulo 8 para uso en produccion.

Hub resuelve el problema de distribucion de contenido. En lugar de que cada equipo mantenga su propia copia de colecciones e imagenes EE, hay una unica fuente de verdad gobernada.

### Event-Driven Ansible

**Event-Driven Ansible (EDA)** extiende la automatizacion de "un humano dispara un trabajo" a "los eventos disparan trabajos automaticamente." EDA introduce:

- **Fuentes de eventos** -- integraciones que escuchan eventos de sistemas de monitoreo (Prometheus, Datadog), sistemas de tickets (ServiceNow), proveedores de nube (AWS CloudWatch), sistemas de mensajeria (Kafka), webhooks y mas
- **Rulebooks** -- archivos YAML que definen condiciones y acciones: "cuando ocurra este evento, ejecutar este job template"
- **Decision Environments** -- imagenes de contenedor (similares a los EEs) que empaquetan las dependencias de Python necesarias para los plugins de fuentes de eventos

Un rulebook simple se ve asi:

```yaml
---
- name: Respond to web server alerts
  hosts: all
  sources:
    - ansible.eda.webhook:
        host: 0.0.0.0
        port: 5000
  rules:
    - name: Restart web server on health check failure
      condition: event.payload.alert == "webserver_down"
      action:
        run_job_template:
          name: "Restart Web Server"
          organization: "Parasol Tech"
```

EDA es poderoso pero es un tema avanzado. Este modulo se centra en Controller y Hub -- los componentes que la CoP necesita primero. EDA se vuelve relevante una vez que el equipo tiene job templates y workflows estables que pueden ser disparados programaticamente.

!!! note "Alcance de EDA"
    Event-Driven Ansible es un tema completo por si mismo. Este modulo introduce el concepto para que entiendas donde encaja en la plataforma. Para trabajo practico con EDA, consulta la [documentacion de EDA](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/).

## Entorno de Laboratorio

### Acceso al Sandbox de AAP

Para seguir los ejercicios de este modulo, necesitas acceso a una instancia de AAP. Hay dos opciones:

**Opcion 1: Sandbox de AAP de Red Hat (recomendado)**

Red Hat proporciona un entorno sandbox de AAP gratuito y de tiempo limitado para aprendizaje:

1. Visita la [pagina de prueba de AAP](https://www.redhat.com/en/technologies/management/ansible/trial)
2. Inicia sesion con tu cuenta de Red Hat (gratuita para crear)
3. Sigue las instrucciones de configuracion para aprovisionar tu sandbox
4. Recibiras una URL de Controller y credenciales

El sandbox incluye Controller, un Automation Hub privado y recursos preconfigurados para explorar.

**Opcion 2: Sandbox de Desarrollador de Red Hat**

El [Sandbox de Desarrollador de Red Hat](https://developers.redhat.com/products/ansible/getting-started) proporciona acceso a AAP como parte de un entorno de desarrollador mas amplio. Esta opcion incluye herramientas y servicios adicionales de desarrollo.

!!! tip "Sin acceso a AAP?"
    Si no puedes acceder a una instancia de AAP en este momento, este modulo sigue siendo valioso. Los conceptos, la arquitectura y el mapeo de CLI a Controller aplican a cualquier version de AAP. Lee el material, estudia los diagramas y vuelve a los ejercicios cuando tengas acceso.

## De CLI a Controller

Todo lo que has hecho en la linea de comandos se mapea directamente a un concepto de Controller. La transicion no se trata de aprender nueva automatizacion -- se trata de gestionar la misma automatizacion a traves de una plataforma gobernada.

| Concepto CLI | Equivalente en Controller | Que Cambia |
|--------------|--------------------------|------------|
| `ansible-playbook deploy.yml` | **Job Template** | Playbook, inventario, credenciales y variables se agrupan en una definicion reutilizable y parametrizada |
| Archivos de inventario (`hosts.yml`, `group_vars/`) | **Inventory** + **Inventory Source** | Los inventarios se almacenan en Controller. Las fuentes pueden sincronizar desde Git, proveedores de nube o scripts personalizados |
| Claves `~/.ssh/`, contrasenas de vault | **Credentials** | Los secretos se almacenan cifrados en Controller. Los usuarios pueden *usar* credenciales sin *verlas* |
| `ansible.cfg` | **Project** + **Configuracion de Organization** | La configuracion se gestiona por proyecto y por organizacion a traves de la UI/API |
| `--limit webservers` | Campo **Limit** en el Job Template | El mismo concepto, expuesto como un campo de la interfaz que puede bloquearse o parametrizarse |
| `--extra-vars "env=prod"` | **Extra Variables** / **Survey** | Las variables pueden solicitarse al momento de lanzar con validacion usando surveys |
| Ejecutar desde cron | **Schedule** en el Job Template | Programador integrado con reglas de recurrencia, sin necesidad de gestionar cron |
| Revisar la salida del terminal | **Log de salida del job** + **Notificaciones** | Captura completa de stdout, retencion de logs y notificaciones a Slack, email, webhook, etc. |

La idea clave: Controller no cambia *que* hace Ansible. Cambia *como gestionas* lo que Ansible hace. Tus playbooks, roles, colecciones y EEs funcionan exactamente igual -- Controller agrega gobernanza, auditoria y colaboracion encima.

### Proyectos

Un **Proyecto** en Controller es una referencia a un repositorio de control de versiones que contiene contenido de Ansible. Cuando creas un Proyecto, le dices a Controller:

- Donde vive el repositorio Git (URL)
- Que rama o etiqueta usar
- Que credencial usar para la autenticacion (clave SSH o token)
- Si verificar las firmas de contenido (usando la credencial GPG del Modulo 8)

Controller clona el repositorio y pone su contenido disponible para los Job Templates. Cuando el repositorio cambia, sincronizas el Proyecto para obtener el contenido mas reciente.

Asi es como el contenido firmado del Modulo 8 llega a Controller. El flujo de seguridad de la cadena de suministro se completa aqui:

```text
Desarrollador firma contenido → Push a Git → Controller sincroniza Proyecto → Verifica firma GPG
```

## Job Templates

Un **Job Template** es la unidad de trabajo mas fundamental en Controller. Agrupa todo lo necesario para ejecutar un playbook:

- **Project** -- que repositorio Git contiene el playbook
- **Playbook** -- que archivo de playbook ejecutar (seleccionado del Proyecto)
- **Inventory** -- que hosts apuntar
- **Credentials** -- que claves/tokens usar para la autenticacion
- **Execution Environment** -- que imagen EE usar para el runtime
- **Extra Variables** -- variables predeterminadas para pasar al playbook
- **Limit** -- patron de hosts opcional para restringir la ejecucion
- **Verbosity** -- el nivel `-v` (0-5)

### Creando un Job Template

Para crear un Job Template para el despliegue del servidor web del Modulo 6:

1. **Crear un Proyecto** apuntando al repositorio Git que contiene la coleccion `parasoltech.infrastructure` y sus playbooks
2. **Crear o seleccionar un Inventario** con los hosts destino
3. **Crear o seleccionar una Credencial** con la clave SSH para los hosts destino
4. **Crear el Job Template** con:
    - Nombre: `Deploy Web Server`
    - Proyecto: el proyecto creado en el paso 1
    - Playbook: `playbooks/deploy-webserver.yml`
    - Inventario: el inventario del paso 2
    - Credenciales: la credencial SSH del paso 3
    - Execution Environment: `parasoltech-ee`

Una vez creado, cualquier persona con los permisos adecuados puede lanzar el job template desde la interfaz o la API. Cada ejecucion se registra con el usuario que la lanzo, los parametros usados y la salida completa.

### Surveys

Los **Surveys** te permiten solicitar informacion al usuario al momento de lanzar. En lugar de confiar en que los usuarios escriban `--extra-vars` correctamente, defines un formulario con campos tipados, valores predeterminados y reglas de validacion.

Por ejemplo, un survey para el despliegue del servidor web podria incluir:

- **Entorno** (desplegable): `dev`, `staging`, `production`
- **Puerto del servidor web** (entero): predeterminado `8080`, minimo `1024`, maximo `65535`
- **Habilitar TLS** (booleano): predeterminado `true`

Los surveys convierten un job template generico en una interfaz de autoservicio. Un miembro del equipo que no conoce Ansible puede desplegar un servidor web llenando un formulario -- el survey mapea sus respuestas a extra variables que el playbook consume.

!!! tip "Las variables del survey se mapean a extra vars"
    Las respuestas del survey se inyectan como extra variables. Si tu playbook usa `webserver_port`, crea una pregunta del survey con el nombre de variable `webserver_port`. El codigo del playbook no cambia en absoluto.

### Lanzamiento y Monitoreo

Despues de crear un job template, puedes:

- **Lanzarlo** inmediatamente desde la interfaz o via la API
- **Programarlo** para ejecutarse en horarios especificos (diario, semanal, con una expresion cron)
- **Monitorear** trabajos en ejecucion en tiempo real -- la salida se transmite en vivo, igual que ver un terminal
- **Revisar** trabajos completados -- cada ejecucion se almacena con su salida completa, hora de inicio/fin y estado

La vista de detalle del trabajo muestra la misma salida que verias de `ansible-playbook` en la linea de comandos, mas metadatos sobre el execution environment, las credenciales usadas y que usuario disparo la ejecucion.

## Workflows

Un **Workflow** encadena multiples job templates en un pipeline de automatizacion de multiples pasos. Cada nodo en un workflow puede:

- Ejecutar un **Job Template**
- Ejecutar otro **Workflow** (workflows anidados)
- Ejecutar una **Sincronizacion de Proyecto**
- Ejecutar una **Sincronizacion de Inventory Source**
- Ejecutar un nodo de **Aprobacion** (pausar y esperar a que un humano apruebe antes de continuar)

Los nodos se conectan con tres tipos de aristas:

| Tipo de Arista | Significado |
|----------------|-------------|
| **On Success** (verde) | Ejecutar el siguiente nodo solo si este tuvo exito |
| **On Failure** (rojo) | Ejecutar el siguiente nodo solo si este fallo |
| **Always** (azul) | Ejecutar el siguiente nodo sin importar el resultado de este |

### Ejemplo: Workflow de Despliegue de Parasol Tech

La CoP disena un workflow de despliegue que encadena la automatizacion de modulos anteriores:

```text
┌─────────────────┐   exito     ┌────────────────┐   exito     ┌──────────────────┐
│  Sincronizar    │────────────▶│  Desplegar     │────────────▶│  Verificar Salud │
│  Proyecto       │             │  Servidor Web  │             │  del Servicio    │
│  (verificar GPG)│             │                │             │                  │
└─────────────────┘             └────────────────┘             └──────────────────┘
        │                              │                              │
      fallo                          fallo                          fallo
        ▼                              ▼                              ▼
┌─────────────────┐             ┌────────────────┐             ┌──────────────────┐
│  Notificar:     │             │  Notificar:    │             │  Rollback        │
│  Contenido      │             │  Despliegue    │             │  Servidor Web    │
│  Manipulado     │             │  Fallido       │             │                  │
└─────────────────┘             └────────────────┘             └──────────────────┘
                                                                      │
                                                                   siempre
                                                                      ▼
                                                               ┌──────────────────┐
                                                               │  Notificar:      │
                                                               │  Rollback        │
                                                               │  Ejecutado       │
                                                               └──────────────────┘
```

Este workflow:

1. **Sincroniza el Proyecto** y verifica la firma GPG (Modulo 8). Si el contenido ha sido manipulado, el workflow se detiene y envia una notificacion.
2. **Despliega el servidor web** usando el job template. Si el despliegue falla, se envia una notificacion.
3. **Verifica que el servicio** este saludable. Si la verificacion de salud falla, dispara un rollback y luego notifica sin importar el resultado del rollback.

Cada nodo en este workflow es un job template separado. El workflow los orquesta, maneja los fallos y asegura que las personas correctas sean notificadas. Esto es mucho mas robusto que un script de shell que ejecuta tres comandos `ansible-playbook` en secuencia.

### Convergencia y Ramificacion

Los workflows soportan mas que cadenas lineales. Los nodos pueden ramificarse (un nodo dispara multiples nodos en paralelo) y converger (multiples nodos deben completarse antes de que el siguiente comience). Esto habilita patrones como:

- Ejecutar migracion de base de datos y calentamiento de cache en paralelo, luego desplegar la aplicacion despues de que ambos tengan exito
- Ejecutar el mismo playbook contra multiples entornos en paralelo
- Agregar una puerta de aprobacion antes del despliegue a produccion

## Inventarios y Credenciales

### Inventarios en Controller

Los inventarios de Controller cumplen el mismo proposito que los archivos de inventario del Modulo 3, pero con capacidades adicionales:

- **Hosts estaticos** -- agregar hosts y grupos directamente en la interfaz, equivalente a editar `hosts.yml`
- **Inventory Sources** -- sincronizar hosts de sistemas externos automaticamente:
    - **SCM (Git)** -- obtener archivos de inventario de un repositorio (tu directorio estructurado `inventory/` funciona directamente)
    - **Proveedores de nube** -- descubrir hosts de AWS, Azure, GCP, VMware, OpenStack
    - **Scripts personalizados** -- ejecutar un script de inventario dinamico que retorna JSON
- **Smart Inventories** -- crear grupos dinamicos basados en facts de hosts y filtros

Para la CoP, el punto de partida mas natural es un inventory source SCM que apunte al mismo repositorio Git que el Proyecto. Esto mantiene los archivos de inventario que el equipo ya escribio (en el Modulo 3) como la fuente de verdad, mientras los pone disponibles en Controller.

### Variables en Controller

Las variables de inventario en Controller siguen las mismas reglas de precedencia que Ansible por CLI. Puedes definir variables a nivel de host, grupo o inventario. Estas se mapean directamente a lo que pondrias en `host_vars/` y `group_vars/` en tu directorio de inventario estructurado.

!!! warning "Una sola fuente de verdad"
    Evita definir la misma variable tanto en tus archivos de inventario rastreados por Git como en la interfaz de Controller. Elige una ubicacion y se consistente. El enfoque recomendado es mantener las variables en Git (gestionadas por la CoP) y sincronizarlas a Controller via el inventory source SCM.

### Credenciales

Las credenciales son una de las funcionalidades mas importantes de Controller. Almacenan secretos -- claves SSH, contrasenas, tokens API, contrasenas de vault, credenciales de proveedores de nube -- cifrados en la base de datos.

Tipos de credenciales clave:

| Tipo | Proposito |
|------|-----------|
| **Machine** | Claves SSH y contrasenas para conectarse a los hosts gestionados |
| **Source Control** | Credenciales Git para sincronizar Proyectos |
| **Vault** | Contrasenas de Ansible Vault para descifrar archivos cifrados |
| **Container Registry** | Credenciales para obtener imagenes EE de registros privados |
| **GPG Public Key** | Clave publica para verificacion de firmas de contenido |
| **Cloud** | Credenciales de AWS, Azure, GCP, VMware para modulos de nube e inventario dinamico |

El beneficio critico de seguridad: los usuarios pueden *usar* una credencial para ejecutar un trabajo sin ver nunca el valor del secreto. Un miembro junior del equipo puede desplegar en servidores de produccion usando una clave SSH que no puede descargar, copiar ni ver. La credencial es inyectada en el EE en tiempo de ejecucion por Controller.

Este es un cambio fundamental respecto a Ansible por CLI, donde todos los que ejecutan playbooks necesitan acceso directo a claves SSH y contrasenas de vault en su maquina local.

## RBAC

El Control de Acceso Basado en Roles (RBAC) en Controller determina quien puede hacer que. Se construye sobre tres conceptos:

### Organizaciones

Una **Organizacion** es la agrupacion de nivel superior. Contiene usuarios, equipos, proyectos, inventarios y credenciales. Una sola instalacion de AAP puede alojar multiples organizaciones.

Para Parasol Tech, podria haber una organizacion por cada division:

- `Parasol Tech - Plataforma` (la organizacion de la CoP)
- `Parasol Tech - Base de Datos` (el equipo de base de datos)
- `Parasol Tech - Redes` (el equipo de redes)

### Equipos

Un **Equipo** es un grupo de usuarios dentro de una organizacion. Los equipos son la forma de asignar permisos a escala -- en lugar de dar permisos a cada usuario individualmente, asignas permisos a un equipo y agregas usuarios a ese equipo.

La CoP podria crear equipos como:

- `Admins de Plataforma` -- acceso completo a todos los recursos
- `Desarrolladores de Plataforma` -- pueden crear y editar job templates, pero no pueden modificar credenciales ni inventarios
- `Operadores de Plataforma` -- pueden lanzar job templates y ver resultados, pero no pueden editarlos

### Roles y Permisos

Controller tiene un modelo de permisos granular. Para cada tipo de recurso (Job Template, Inventory, Credential, Project, etc.), existen varios niveles de permiso:

| Rol | Capacidades |
|-----|-------------|
| **Admin** | Control total -- crear, editar, eliminar, ejecutar y otorgar permisos a otros |
| **Use** | Puede usar el recurso (ej., adjuntar una credencial a un job template) pero no puede editarlo |
| **Execute** | Puede lanzar un job template o workflow pero no puede editar su configuracion |
| **Read** | Puede ver el recurso pero no puede modificarlo ni ejecutarlo |
| **Approval** | Puede aprobar o denegar nodos de aprobacion de workflows |

Estos roles se asignan por recurso. Esto significa que puedes dar a un equipo permiso `Execute` en el job template `Deploy Web Server`, permiso `Read` en el inventario de produccion, y ningun acceso a las credenciales usadas por ese job template. El equipo puede lanzar el despliegue pero no puede ver las claves SSH, editar el inventario ni modificar la configuracion del job template.

### Diseno de RBAC para la CoP

Una configuracion practica de RBAC para Parasol Tech:

```text
Organizacion: Parasol Tech - Plataforma
│
├── Equipo: Admins de Plataforma
│   ├── Admin en todos los Proyectos
│   ├── Admin en todos los Inventarios
│   ├── Admin en todas las Credenciales
│   └── Admin en todos los Job Templates
│
├── Equipo: Desarrolladores de Plataforma
│   ├── Admin en Job Templates (pueden crear/editar)
│   ├── Use en Credenciales (pueden adjuntar a JTs)
│   ├── Use en Inventarios (pueden adjuntar a JTs)
│   └── Read en Proyectos
│
└── Equipo: Operadores de Plataforma
    ├── Execute en Job Templates especificos
    ├── Read en Inventarios
    └── Approval en Workflow de Despliegue
```

Con esta configuracion:

- **Admins** gestionan la infraestructura: credenciales, inventarios, proyectos y configuraciones de EE
- **Desarrolladores** crean y prueban job templates usando credenciales e inventarios existentes
- **Operadores** ejecutan job templates aprobados y aprueban workflows de despliegue sin ninguna capacidad de modificar la automatizacion o acceder a secretos

Esta es la gobernanza que la CoP necesitaba cuando todos ejecutaban `ansible-playbook` desde su propio portatil.

## Integracion de EE

El Execution Environment construido en el Modulo 8 se integra directamente con Controller. En lugar de ejecutar playbooks con el Python que este instalado en un servidor, Controller ejecuta cada trabajo dentro de un contenedor EE.

### Agregando EEs a Controller

Controller necesita saber de donde obtener las imagenes EE. Hay dos enfoques:

**Desde un registro de contenedores (recomendado para produccion):**

1. Sube la imagen EE a un registro de contenedores (Private Automation Hub, Quay.io, o cualquier registro OCI) -- como se mostro en el Modulo 8
2. En Controller, crea un recurso de **Execution Environment** apuntando a la URL de la imagen (ej., `hub.parasol.example/ee-images/parasoltech-ee:1.0.0`)
3. Si el registro requiere autenticacion, crea una credencial de **Container Registry** y adjuntala al EE

**Desde una imagen local (para desarrollo/pruebas):**

1. Construye la imagen en el host de Controller con `ansible-builder`
2. Referencia el nombre de la imagen local en la configuracion de EE de Controller

### Asignando EEs a Job Templates

Cada job template puede especificar que EE usar. Cuando el trabajo se lanza, Controller obtiene la imagen EE (si no esta en cache) y ejecuta el playbook dentro de ella.

Esto completa la historia de portabilidad del Modulo 8:

```text
Modulo 8:  Construir EE → Probar localmente con ansible-navigator
Modulo 9:  Subir EE al registro → Controller lo obtiene y usa para cada trabajo
```

Cada ejecucion -- ya sea disparada por un usuario, un horario, un workflow o una llamada API -- usa la misma imagen EE con las mismas dependencias. El problema de "funciona en mi maquina" se elimina a nivel de plataforma, no solo a nivel de desarrollador individual.

### Ciclo de Vida del EE

A medida que la CoP actualiza su coleccion y dependencias, el ciclo de vida del EE se ve asi:

1. El desarrollador actualiza `execution-environment.yml` (agregar una nueva coleccion, actualizar una dependencia de Python)
2. CI construye una nueva imagen EE con una nueva etiqueta de version (ej., `parasoltech-ee:1.1.0`)
3. La imagen se sube al registro de contenedores
4. Un admin actualiza el recurso EE de Controller para apuntar a la nueva etiqueta
5. Todos los job templates que usan ese EE ahora se ejecutan con las dependencias actualizadas

Este es un proceso controlado y versionado. El EE en produccion no cambia hasta que un admin deliberadamente lo actualiza. El rollback es tan simple como apuntar de vuelta a la etiqueta anterior.

## Sincronizacion de Proyectos y Verificacion de Contenido

### Sincronizacion de Proyectos

Cuando Controller sincroniza un Proyecto, clona (u obtiene) el repositorio Git y pone su contenido disponible. Puedes disparar una sincronizacion manualmente, programarla o configurar webhooks para que un push a Git dispare automaticamente una sincronizacion.

El proceso de sincronizacion:

1. Controller se conecta al repositorio Git usando la credencial de Source Control
2. Clona el repositorio (u obtiene actualizaciones de un clon existente)
3. Escanea el repositorio en busca de archivos de playbook y los pone disponibles para Job Templates
4. Si la verificacion de contenido esta configurada, ejecuta la verificacion de firma

### Verificacion de Contenido con GPG

Aqui es donde la firma de contenido del Modulo 8 cierra el ciclo. Cuando un Proyecto tiene habilitada la verificacion de contenido GPG:

1. Sube la clave publica GPG a Controller como una credencial de **GPG Public Key**
2. Configura el Proyecto para usar esta credencial para la verificacion de contenido
3. En cada sincronizacion, Controller ejecuta el equivalente de `ansible-sign project gpg-verify .` sobre el contenido del repositorio

Si la verificacion tiene exito, el Proyecto se sincroniza normalmente y su contenido esta disponible. Si la verificacion falla -- porque un archivo fue modificado, agregado o eliminado despues de la firma -- la sincronizacion falla. Ningun job template puede ejecutar el contenido no verificado.

```text
Cadena de suministro completa:

Desarrollador → Revisa codigo → Firma con ansible-sign → Push a Git
                                                              │
Controller ← Sincroniza Proyecto ← Verifica firma GPG ───────┘
     │
     └── Ejecuta playbook en EE ← Obtiene EE de Hub
```

Cada eslabon en esta cadena esta verificado:

- El **contenido** esta firmado y verificado (ansible-sign + GPG)
- El **runtime** esta empaquetado y versionado (EE + registro de contenedores)
- El **acceso** esta gobernado (RBAC + credenciales)
- La **ejecucion** esta auditada (logs de trabajos + notificaciones)

Esta es la practica madura de automatizacion que la CoP se propuso construir.

## Ejercicios

### Ejercicio 1: Explorar la Interfaz de AAP

Inicia sesion en tu sandbox de AAP y explora las areas principales de navegacion. Identifica donde vive cada concepto de este modulo en la interfaz:

- Organizaciones
- Proyectos
- Inventarios
- Credenciales
- Job Templates
- Workflows
- Execution Environments

!!! tip "Usa la documentacion"
    La interfaz de AAP puede variar ligeramente entre versiones. Consulta la [documentacion de AAP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/) para instrucciones de navegacion especificas de cada version.

### Ejercicio 2: Crear un Proyecto

Crea un Proyecto en Controller:

1. Navega a la seccion de Proyectos
2. Crea un nuevo Proyecto con:
    - **Nombre**: `Parasol Infrastructure`
    - **Organizacion**: tu organizacion del sandbox
    - **Tipo de Control de Versiones**: Git
    - **URL de Control de Versiones**: la URL de tu repositorio del curso

3. Sincroniza el Proyecto y verifica que tenga exito

Si configuraste la firma de contenido en el Modulo 8 y tienes una clave publica GPG, configura el Proyecto para verificar firmas durante la sincronizacion.

### Ejercicio 3: Crear un Inventario

Crea un Inventario en Controller:

1. Navega a la seccion de Inventarios
2. Crea un nuevo Inventario:
    - **Nombre**: `Parasol Dev Environment`
    - **Organizacion**: tu organizacion del sandbox
3. Agrega un host manualmente (usa `localhost` con `ansible_connection: local` para pruebas en el sandbox)
4. Crea un grupo llamado `webservers` y agrega el host a el

### Ejercicio 4: Crear y Lanzar un Job Template

Crea un Job Template que una el Proyecto y el Inventario:

1. Navega a Job Templates
2. Crea un nuevo Job Template:
    - **Nombre**: `Deploy Web Server`
    - **Proyecto**: `Parasol Infrastructure`
    - **Playbook**: selecciona un playbook del Proyecto sincronizado
    - **Inventario**: `Parasol Dev Environment`
    - **Credenciales**: selecciona o crea una credencial apropiada

3. Lanza el job template
4. Observa la salida en tiempo real
5. Despues de completarse, revisa los detalles del trabajo -- observa la hora de inicio, hora de fin, usuario y estado

### Ejercicio 5: Construir un Workflow Simple

Crea un Workflow que encadene dos job templates:

1. Navega a Workflow Templates
2. Crea un nuevo Workflow Template:
    - **Nombre**: `Deploy and Verify`
    - **Organizacion**: tu organizacion del sandbox
3. Abre el visualizador de workflows
4. Agrega el job template `Deploy Web Server` como el primer nodo
5. Agrega un segundo nodo (un playbook de verificacion simple) conectado con una arista "On Success"
6. Guarda y lanza el workflow
7. Observa ambos nodos ejecutarse en secuencia

### Ejercicio 6: Configurar RBAC

Explora el modelo de RBAC:

1. Navega a Equipos y crea un equipo llamado `Operators`
2. Navega a Usuarios y crea un usuario de prueba o toma nota de uno existente
3. Agrega el usuario al equipo `Operators`
4. En el job template `Deploy Web Server`, otorga al equipo `Operators` permiso **Execute**
5. Verifica que el equipo puede lanzar el job template pero no puede editarlo

!!! note "Limitaciones del sandbox"
    Algunos entornos sandbox pueden no soportar todas las operaciones de RBAC. Si encuentras restricciones de permisos, estudia los conceptos de RBAC y el modelo de permisos en la documentacion.

## Resumen

En este modulo:

- Aprendiste que Ansible Automation Platform proporciona un plano de control centralizado con tres componentes: **Controller** para orquestacion y gobernanza, **Automation Hub** para distribucion de contenido, y **Event-Driven Ansible** para automatizacion basada en eventos
- Mapeaste cada concepto de CLI a su equivalente en Controller -- los playbooks se convierten en Job Templates, los archivos de inventario en Inventarios con Sources, las claves SSH en Credenciales, y los scripts en Schedules
- Creaste Job Templates que agrupan un playbook, inventario, credenciales, EE y variables en una unidad de trabajo reutilizable y lanzable
- Construiste Workflows que encadenan job templates con aristas de exito, fallo y siempre para crear pipelines de automatizacion robustos de multiples pasos con puertas de aprobacion
- Configuraste Inventarios desde hosts estaticos y fuentes SCM, y usaste Credenciales para almacenar e inyectar secretos de forma segura sin exponerlos a los usuarios
- Estableciste RBAC con Organizaciones, Equipos y roles granulares por recurso (Admin, Use, Execute, Read) para gobernar quien puede hacer que
- Integraste el Execution Environment del Modulo 8 con Controller, asegurando que cada trabajo use el mismo runtime versionado y probado
- Completaste el flujo de seguridad de la cadena de suministro: los desarrolladores firman contenido con `ansible-sign`, hacen push a Git, y Controller verifica la firma GPG en cada sincronizacion de Proyecto antes de permitir la ejecucion

La CoP en Parasol Tech ahora tiene una practica de automatizacion completa. El contenido se desarrolla colaborativamente (Modulo 6), se prueba rigurosamente (Modulo 7), se empaqueta reproduciblemente (Modulo 8) y se gestiona a traves de una plataforma gobernada con RBAC, registro de auditoria y orquestacion de workflows (Modulo 9). El viaje desde Alex ejecutando comandos ad-hoc en un portatil hasta una practica empresarial de automatizacion completamente gobernada esta completo.

## Conclusion del Curso

Alex se reclina y mira el dashboard. El workflow de despliegue se ejecuto durante la noche -- Proyecto sincronizado, firmas GPG verificadas, servidores web desplegados en tres entornos, verificaciones de salud pasadas, notificaciones enviadas al canal del equipo. Nadie tuvo que conectarse por SSH a nada. Nadie escribio `ansible-playbook` a las 2 AM.

Es dificil creer que esto comenzo con un solo comando ad-hoc en un portatil.

**El viaje:**

- **Modulo 1** -- Alex descubrio Ansible y ejecuto el primer comando ad-hoc. Un ingeniero, una maquina, un problema.
- **Modulo 2** -- Los comandos ad-hoc se convirtieron en playbooks. La automatizacion se volvio repetible.
- **Modulo 3** -- Los playbooks crecieron mas alla de localhost. Los inventarios estructurados organizaron hosts a traves de los entornos.
- **Modulo 4** -- Las variables y los facts hicieron los playbooks flexibles. La misma automatizacion se adapto a diferentes entornos.
- **Modulo 5** -- Las plantillas y los handlers convirtieron los playbooks en herramientas de gestion de configuracion. Los servicios se reiniciaban cuando las configuraciones cambiaban.
- **Modulo 6** -- La CoP se formo. Los roles y las colecciones convirtieron playbooks individuales en componentes reutilizables y compartibles. `ansible-creator` genero la coleccion. `ade` gestiono el entorno de desarrollo.
- **Modulo 7** -- Las puertas de calidad se levantaron. `ansible-lint` detecto problemas de estilo, Molecule probo los roles de extremo a extremo, pytest valido la logica, y tox-ansible orquesto la matriz. Ningun codigo no probado llego a produccion.
- **Modulo 8** -- Los Execution Environments eliminaron "funciona en mi maquina." La firma de contenido con `ansible-sign` demostro que lo que se ejecuta en produccion es lo que la CoP reviso. La cadena de suministro quedo asegurada.
- **Modulo 9** -- Controller trajo gobernanza. Job templates, workflows, RBAC, registro de auditoria y gestion centralizada de credenciales reemplazaron el caos de todos ejecutando playbooks desde su propio portatil.

Lo que comenzo como una persona resolviendo un problema es ahora una practica empresarial de automatizacion con pruebas, empaquetado, firma y gobernanza.

### Que Viene Despues

El viaje principal esta completo, pero hay mas por explorar:

**Tracks de dominio (Modulos 10-11)**

- [Modulo 10 -- Sistemas Linux](10-linux-systems.md): Aplica todo lo que has aprendido a la administracion de sistemas Linux -- gestion de usuarios, hardening, parcheado y cumplimiento a escala
- [Modulo 11 -- Automatizacion de Redes](11-network-automation.md): Extiende Ansible a dispositivos de red con `network_cli`, modulos de recursos e integracion con NetBox como fuente de verdad

Estos tracks son opcionales y autocontenidos. No introducen nuevos conceptos fundamentales -- aplican las habilidades de los modulos 1-9 a dominios especificos.

**Comunidad y certificacion**

- **Contribuir a Ansible** -- La comunidad de Ansible prospera con las contribuciones. Comienza mejorando la documentacion, enviando reportes de errores o compartiendo roles en [Ansible Galaxy](https://galaxy.ansible.com/). Unete a la comunidad en [forum.ansible.com](https://forum.ansible.com/).
- **Certificacion de Red Hat** -- Valida tus habilidades con el examen [Red Hat Certified Engineer (RHCE)](https://www.redhat.com/en/services/certification/rhce), que incluye automatizacion con Ansible, o el examen [Red Hat Certified Specialist in Developing Automation with Ansible Automation Platform](https://www.redhat.com/en/services/certification/red-hat-certified-specialist-developing-automation-ansible-automation-platform).
- **Ansible Development Tools** -- Continua explorando `adt` y sus componentes. Las herramientas evolucionan rapidamente -- consulta la [documentacion de Ansible Development Tools](https://ansible.readthedocs.io/projects/dev-tools/) para las ultimas funcionalidades.

**Sigue practicando**

La mejor forma de aprender automatizacion es automatizar. Encuentra un proceso manual en tu organizacion, descomponlo en la jerarquia de arquitectura (landscape, tipo, funcion, componente), escribe un rol, pruebalo con Molecule, empaquetalo como una coleccion y despliegalo a traves de Controller. Luego hazlo de nuevo con el siguiente proceso.

El Zen de Ansible lo dice bien: *"Ansible no es solo una herramienta -- es una practica."* Este curso te dio las herramientas y los patrones. La practica es tuya para construir.
