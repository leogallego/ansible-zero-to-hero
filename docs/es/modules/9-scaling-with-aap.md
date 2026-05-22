# Módulo 9: Escalando con AAP

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Describir los componentes de Ansible Automation Platform (Controller, Hub, EDA)
- Crear job templates y workflows en Controller
- Configurar inventarios y credenciales en Controller
- Establecer RBAC con equipos, roles y permisos
- Integrar Execution Environments con Controller
- Configurar la sincronización de proyectos con verificación de contenido

## La Historia Hasta Ahora

La CoP en Parasol Tech ha recorrido un largo camino. El equipo tiene una colección probada, verificada y firmada -- `parasoltech.infrastructure`. Se distribuye dentro de un Execution Environment personalizado construido con `ansible-builder`. Cada cambio pasa por `ansible-lint`, Molecule, pytest y tox-ansible antes de fusionarse. El contenido está firmado con `ansible-sign` para que nadie pueda manipular los playbooks entre la revisión y la ejecución.

Pero un nuevo problema está surgiendo. Lionel ejecuta el despliegue del servidor web desde un portátil. Jordan ejecuta el playbook de parcheado desde otro portátil. Un tercer miembro del equipo ejecuta comandos ad-hoc desde un jump host. Nadie tiene visibilidad sobre qué se ejecutó, cuándo, quién lo ejecutó, ni si tuvo éxito. No hay registro de auditoría, no hay control de acceso, y no hay forma de programar trabajos recurrentes.

"Ejecuté el playbook de respaldo de la base de datos ayer," dice Jordan. "Pero usé `--limit staging` en lugar de `--limit production`. Nadie lo notó hasta esta mañana."

Lionel frunce el ceño. "Y no tengo forma de saber quién ejecutó qué en los servidores de producción la semana pasada. Necesitamos un plano de control."

La CoP coincide: la ejecución por CLI no escala. Necesitan orquestación centralizada con gobernanza, registro de auditoría, control de acceso basado en roles, y la capacidad de encadenar automatización en flujos de trabajo de múltiples pasos. Necesitan **Ansible Automation Platform**.

## Visión General de AAP

Ansible Automation Platform (AAP) es la plataforma empresarial de Red Hat para gestionar la automatización de Ansible a escala. Toma las herramientas de CLI que has usado a lo largo de este curso y agrega un plano de control centralizado con interfaz web, API REST, RBAC, registro de auditoría, gestión de credenciales y orquestación de flujos de trabajo.

AAP tiene tres componentes principales:

### Controller

**Automation Controller** (anteriormente Ansible Tower) es la capa de gestión central. Proporciona:

- **Job Templates** -- definiciones reutilizables para ejecutar playbooks con inventarios, credenciales y variables específicas
- **Workflows** -- pipelines de automatización de múltiples pasos que encadenan job templates con lógica condicional
- **Inventarios** -- gestión centralizada de hosts con fuentes estáticas, proveedores dinámicos e inventario sincronizado desde sistemas externos
- **Credenciales** -- almacenamiento seguro para claves SSH, tokens API, credenciales de nube y contraseñas de vault -- se acabaron los secretos en portátiles individuales
- **RBAC** -- equipos, roles y permisos granulares que controlan quién puede ejecutar qué en cuáles hosts
- **Registro de auditoría** -- cada ejecución de trabajo se registra con quién la inició, qué se ejecutó, cuándo comenzó, cuánto tardó y cuál fue el resultado
- **Programación** -- ejecutar trabajos en un horario recurrente sin intervención humana
- **API REST** -- todo lo disponible en la interfaz también está disponible vía API, permitiendo integración con pipelines de CI/CD, sistemas de tickets y herramientas personalizadas

Controller es donde la CoP realizará la mayor parte de su trabajo. Reemplaza el patrón de "conectarse por SSH a un servidor y ejecutar `ansible-playbook`" con un flujo de trabajo gobernado y auditable.

### Automation Hub

**Private Automation Hub** es el repositorio interno de contenido de la organización. Cumple dos propósitos:

1. **Registro de colecciones** -- Los equipos publican colecciones en Hub en lugar de compartir tarballs o apuntar a repositorios Git. Otros equipos instalan colecciones desde Hub usando `ansible-galaxy`. Hub puede alojar colecciones certificadas (de Red Hat y socios), colecciones comunitarias validadas y las colecciones privadas de la organización como `parasoltech.infrastructure`.

2. **Registro de contenedores EE** -- Hub almacena imágenes de Execution Environments. Controller obtiene las imágenes EE de Hub cuando ejecuta trabajos, asegurando que cada ejecución use la imagen aprobada y probada. Aquí es donde se publicaría el EE construido en el Módulo 8 para uso en producción.

Hub resuelve el problema de distribución de contenido. En lugar de que cada equipo mantenga su propia copia de colecciones e imágenes EE, hay una única fuente de verdad gobernada.

### Event-Driven Ansible

**Event-Driven Ansible (EDA)** extiende la automatización de "un humano dispara un trabajo" a "los eventos disparan trabajos automáticamente." EDA introduce:

- **Fuentes de eventos** -- integraciones que escuchan eventos de sistemas de monitoreo (Prometheus, Datadog), sistemas de tickets (ServiceNow), proveedores de nube (AWS CloudWatch), sistemas de mensajería (Kafka), webhooks y más
- **Rulebooks** -- archivos YAML que definen condiciones y acciones: "cuando ocurra este evento, ejecutar este job template"
- **Decision Environments** -- imágenes de contenedor (similares a los EEs) que empaquetan las dependencias de Python necesarias para los plugins de fuentes de eventos

Un rulebook simple se ve así:

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

EDA es poderoso pero es un tema avanzado. Este módulo se centra en Controller y Hub -- los componentes que la CoP necesita primero. EDA se vuelve relevante una vez que el equipo tiene job templates y workflows estables que pueden ser disparados programáticamente.

!!! note "Alcance de EDA"
    Event-Driven Ansible es un tema completo por sí mismo. Este módulo introduce el concepto para que entiendas dónde encaja en la plataforma. Para trabajo práctico con EDA, consulta la [documentación de EDA](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/).

## Entorno de Laboratorio

### Acceso al Sandbox de AAP

Para seguir los ejercicios de este módulo, necesitas acceso a una instancia de AAP. Hay dos opciones:

**Opción 1: Sandbox de AAP de Red Hat (recomendado)**

Red Hat proporciona un entorno sandbox de AAP gratuito y de tiempo limitado para aprendizaje:

1. Visita la [página de prueba de AAP](https://www.redhat.com/en/technologies/management/ansible/trial)
2. Inicia sesión con tu cuenta de Red Hat (gratuita para crear)
3. Sigue las instrucciones de configuración para aprovisionar tu sandbox
4. Recibirás una URL de Controller y credenciales

El sandbox incluye Controller, un Automation Hub privado y recursos preconfigurados para explorar.

**Opción 2: Sandbox de Desarrollador de Red Hat**

El [Sandbox de Desarrollador de Red Hat](https://developers.redhat.com/products/ansible/getting-started) proporciona acceso a AAP como parte de un entorno de desarrollador más amplio. Esta opción incluye herramientas y servicios adicionales de desarrollo.

!!! tip "Sin acceso a AAP?"
    Si no puedes acceder a una instancia de AAP en este momento, este módulo sigue siendo válido. Los conceptos, la arquitectura y el mapeo de CLI a Controller aplican a cualquier versión de AAP. Lee el material, estudia los diagramas y vuelve a los ejercicios cuando tengas acceso.

## De CLI a Controller

Todo lo que has hecho en la línea de comandos se mapea directamente a un concepto de Controller. La transición no se trata de aprender nueva automatización -- se trata de gestionar la misma automatización a través de una plataforma gobernada.

| Concepto CLI | Equivalente en Controller | Qué Cambia |
|--------------|--------------------------|------------|
| `ansible-playbook deploy.yml` | **Job Template** | Playbook, inventario, credenciales y variables se agrupan en una definición reutilizable y parametrizada |
| Archivos de inventario (`hosts.yml`, `group_vars/`) | **Inventory** + **Inventory Source** | Los inventarios se almacenan en Controller. Las fuentes pueden sincronizar desde Git, proveedores de nube o scripts personalizados |
| Claves `~/.ssh/`, contraseñas de vault | **Credentials** | Los secretos se almacenan cifrados en Controller. Los usuarios pueden *usar* credenciales sin *verlas* |
| `ansible.cfg` | **Project** + **Configuración de Organization** | La configuración se gestiona por proyecto y por organización a través de la UI/API |
| `--limit webservers` | Campo **Limit** en el Job Template | El mismo concepto, expuesto como un campo de la interfaz que puede bloquearse o parametrizarse |
| `--extra-vars "env=prod"` | **Extra Variables** / **Survey** | Las variables pueden solicitarse al momento de lanzar con validación usando surveys |
| Ejecutar desde cron | **Schedule** en el Job Template | Programador integrado con reglas de recurrencia, sin necesidad de gestionar cron |
| Revisar la salida del terminal | **Log de salida del job** + **Notificaciones** | Captura completa de stdout, retención de logs y notificaciones a Slack, email, webhook, etc. |

La idea clave: Controller no cambia *qué* hace Ansible. Cambia *cómo gestionas* lo que Ansible hace. Tus playbooks, roles, colecciones y EEs funcionan exactamente igual -- Controller agrega gobernanza, auditoría y colaboración encima.

### Proyectos

Un **Proyecto** en Controller es una referencia a un repositorio de control de versiones que contiene contenido de Ansible. Cuando creas un Proyecto, le dices a Controller:

- Dónde vive el repositorio Git (URL)
- Qué rama o etiqueta usar
- Qué credencial usar para la autenticación (clave SSH o token)
- Si verificar las firmas de contenido (usando la credencial GPG del Módulo 8)

Controller clona el repositorio y pone su contenido disponible para los Job Templates. Cuando el repositorio cambia, sincronizas el Proyecto para obtener el contenido más reciente.

Así es como el contenido firmado del Módulo 8 llega a Controller. El flujo de seguridad de la cadena de suministro se completa aquí:

```text
Desarrollador firma contenido → Push a Git → Controller sincroniza Proyecto → Verifica firma GPG
```

## Job Templates

Un **Job Template** es la unidad de trabajo más fundamental en Controller. Agrupa todo lo necesario para ejecutar un playbook:

- **Project** -- qué repositorio Git contiene el playbook
- **Playbook** -- qué archivo de playbook ejecutar (seleccionado del Proyecto)
- **Inventory** -- qué hosts apuntar
- **Credentials** -- qué claves/tokens usar para la autenticación
- **Execution Environment** -- qué imagen EE usar para el runtime
- **Extra Variables** -- variables predeterminadas para pasar al playbook
- **Limit** -- patrón de hosts opcional para restringir la ejecución
- **Verbosity** -- el nivel `-v` (0-5)

### Creando un Job Template

Para crear un Job Template para el despliegue del servidor web del Módulo 6:

1. **Crear un Proyecto** apuntando al repositorio Git que contiene la colección `parasoltech.infrastructure` y sus playbooks
2. **Crear o seleccionar un Inventario** con los hosts destino
3. **Crear o seleccionar una Credencial** con la clave SSH para los hosts destino
4. **Crear el Job Template** con:
    - Nombre: `Deploy Web Server`
    - Proyecto: el proyecto creado en el paso 1
    - Playbook: `playbooks/deploy-webserver.yml`
    - Inventario: el inventario del paso 2
    - Credenciales: la credencial SSH del paso 3
    - Execution Environment: `parasoltech-ee`

Una vez creado, cualquier persona con los permisos adecuados puede lanzar el job template desde la interfaz o la API. Cada ejecución se registra con el usuario que la lanzó, los parámetros usados y la salida completa.

### Surveys

Los **Surveys** te permiten solicitar información al usuario al momento de lanzar. En lugar de confiar en que los usuarios escriban `--extra-vars` correctamente, defines un formulario con campos tipados, valores predeterminados y reglas de validación.

Por ejemplo, un survey para el despliegue del servidor web podría incluir:

- **Entorno** (desplegable): `dev`, `staging`, `production`
- **Puerto del servidor web** (entero): predeterminado `8080`, mínimo `1024`, máximo `65535`
- **Habilitar TLS** (booleano): predeterminado `true`

Los surveys convierten un job template genérico en una interfaz de autoservicio. Un miembro del equipo que no conoce Ansible puede desplegar un servidor web llenando un formulario -- el survey mapea sus respuestas a extra variables que el playbook consume.

!!! tip "Las variables del survey se mapean a extra vars"
    Las respuestas del survey se inyectan como extra variables. Si tu playbook usa `webserver_port`, crea una pregunta del survey con el nombre de variable `webserver_port`. El código del playbook no cambia en absoluto.

### Lanzamiento y Monitoreo

Después de crear un job template, puedes:

- **Lanzarlo** inmediatamente desde la interfaz o vía la API
- **Programarlo** para ejecutarse en horarios específicos (diario, semanal, con una expresión cron)
- **Monitorear** trabajos en ejecución en tiempo real -- la salida se transmite en vivo, igual que ver un terminal
- **Revisar** trabajos completados -- cada ejecución se almacena con su salida completa, hora de inicio/fin y estado

La vista de detalle del trabajo muestra la misma salida que verías de `ansible-playbook` en la línea de comandos, más metadatos sobre el execution environment, las credenciales usadas y qué usuario disparó la ejecución.

## Workflows

Un **Workflow** encadena múltiples job templates en un pipeline de automatización de múltiples pasos. Cada nodo en un workflow puede:

- Ejecutar un **Job Template**
- Ejecutar otro **Workflow** (workflows anidados)
- Ejecutar una **Sincronización de Proyecto**
- Ejecutar una **Sincronización de Inventory Source**
- Ejecutar un nodo de **Aprobación** (pausar y esperar a que un humano apruebe antes de continuar)

Los nodos se conectan con tres tipos de aristas:

| Tipo de Arista | Significado |
|----------------|-------------|
| **On Success** (verde) | Ejecutar el siguiente nodo solo si este tuvo éxito |
| **On Failure** (rojo) | Ejecutar el siguiente nodo solo si este falló |
| **Always** (azul) | Ejecutar el siguiente nodo sin importar el resultado de este |

### Ejemplo: Workflow de Despliegue de Parasol Tech

La CoP diseña un workflow de despliegue que encadena la automatización de módulos anteriores:

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

1. **Sincroniza el Proyecto** y verifica la firma GPG (Módulo 8). Si el contenido ha sido manipulado, el workflow se detiene y envía una notificación.
2. **Despliega el servidor web** usando el job template. Si el despliegue falla, se envía una notificación.
3. **Verifica que el servicio** esté saludable. Si la verificación de salud falla, dispara un rollback y luego notifica sin importar el resultado del rollback.

Cada nodo en este workflow es un job template separado. El workflow los orquesta, maneja los fallos y asegura que las personas correctas sean notificadas. Esto es mucho más robusto que un script de shell que ejecuta tres comandos `ansible-playbook` en secuencia.

### Convergencia y Ramificación

Los workflows soportan más que cadenas lineales. Los nodos pueden ramificarse (un nodo dispara múltiples nodos en paralelo) y converger (múltiples nodos deben completarse antes de que el siguiente comience). Esto habilita patrones como:

- Ejecutar migración de base de datos y calentamiento de caché en paralelo, luego desplegar la aplicación después de que ambos tengan éxito
- Ejecutar el mismo playbook contra múltiples entornos en paralelo
- Agregar una puerta de aprobación antes del despliegue a producción

## Inventarios y Credenciales

### Inventarios en Controller

Los inventarios de Controller cumplen el mismo propósito que los archivos de inventario del Módulo 3, pero con capacidades adicionales:

- **Hosts estáticos** -- agregar hosts y grupos directamente en la interfaz, equivalente a editar `hosts.yml`
- **Inventory Sources** -- sincronizar hosts de sistemas externos automáticamente:
    - **SCM (Git)** -- obtener archivos de inventario de un repositorio (tu directorio estructurado `inventory/` funciona directamente)
    - **Proveedores de nube** -- descubrir hosts de AWS, Azure, GCP, VMware, OpenStack
    - **Scripts personalizados** -- ejecutar un script de inventario dinámico que retorna JSON
- **Smart Inventories** -- crear grupos dinámicos basados en facts de hosts y filtros

Para la CoP, el punto de partida más natural es un inventory source SCM que apunte al mismo repositorio Git que el Proyecto. Esto mantiene los archivos de inventario que el equipo ya escribió (en el Módulo 3) como la fuente de verdad, mientras los pone disponibles en Controller.

### Variables en Controller

Las variables de inventario en Controller siguen las mismas reglas de precedencia que Ansible por CLI. Puedes definir variables a nivel de host, grupo o inventario. Estas se mapean directamente a lo que pondrías en `host_vars/` y `group_vars/` en tu directorio de inventario estructurado.

!!! warning "Una sola fuente de verdad"
    Evita definir la misma variable tanto en tus archivos de inventario rastreados por Git como en la interfaz de Controller. Elige una ubicación y sé consistente. El enfoque recomendado es mantener las variables en Git (gestionadas por la CoP) y sincronizarlas a Controller vía el inventory source SCM.

### Credenciales

Las credenciales son una de las funcionalidades más importantes de Controller. Almacenan secretos -- claves SSH, contraseñas, tokens API, contraseñas de vault, credenciales de proveedores de nube -- cifrados en la base de datos.

Tipos de credenciales clave:

| Tipo | Propósito |
|------|-----------|
| **Machine** | Claves SSH y contraseñas para conectarse a los hosts gestionados |
| **Source Control** | Credenciales Git para sincronizar Proyectos |
| **Vault** | Contraseñas de Ansible Vault para descifrar archivos cifrados |
| **Container Registry** | Credenciales para obtener imágenes EE de registros privados |
| **GPG Public Key** | Clave pública para verificación de firmas de contenido |
| **Cloud** | Credenciales de AWS, Azure, GCP, VMware para módulos de nube e inventario dinámico |

El beneficio crítico de seguridad: los usuarios pueden *usar* una credencial para ejecutar un trabajo sin ver nunca el valor del secreto. Un miembro junior del equipo puede desplegar en servidores de producción usando una clave SSH que no puede descargar, copiar ni ver. La credencial es inyectada en el EE en tiempo de ejecución por Controller.

Este es un cambio fundamental respecto a Ansible por CLI, donde todos los que ejecutan playbooks necesitan acceso directo a claves SSH y contraseñas de vault en su máquina local.

## RBAC

El Control de Acceso Basado en Roles (RBAC) en Controller determina quién puede hacer qué. Se construye sobre tres conceptos:

### Organizaciones

Una **Organización** es la agrupación de nivel superior. Contiene usuarios, equipos, proyectos, inventarios y credenciales. Una sola instalación de AAP puede alojar múltiples organizaciones.

Para Parasol Tech, podría haber una organización por cada división:

- `Parasol Tech - Plataforma` (la organización de la CoP)
- `Parasol Tech - Base de Datos` (el equipo de base de datos)
- `Parasol Tech - Redes` (el equipo de redes)

### Equipos

Un **Equipo** es un grupo de usuarios dentro de una organización. Los equipos son la forma de asignar permisos a escala -- en lugar de dar permisos a cada usuario individualmente, asignas permisos a un equipo y agregas usuarios a ese equipo.

La CoP podría crear equipos como:

- `Admins de Plataforma` -- acceso completo a todos los recursos
- `Desarrolladores de Plataforma` -- pueden crear y editar job templates, pero no pueden modificar credenciales ni inventarios
- `Operadores de Plataforma` -- pueden lanzar job templates y ver resultados, pero no pueden editarlos

### Roles y Permisos

Controller tiene un modelo de permisos granular. Para cada tipo de recurso (Job Template, Inventory, Credential, Project, etc.), existen varios niveles de permiso:

| Rol | Capacidades |
|-----|-------------|
| **Admin** | Control total -- crear, editar, eliminar, ejecutar y otorgar permisos a otros |
| **Use** | Puede usar el recurso (ej., adjuntar una credencial a un job template) pero no puede editarlo |
| **Execute** | Puede lanzar un job template o workflow pero no puede editar su configuración |
| **Read** | Puede ver el recurso pero no puede modificarlo ni ejecutarlo |
| **Approval** | Puede aprobar o denegar nodos de aprobación de workflows |

Estos roles se asignan por recurso. Esto significa que puedes dar a un equipo permiso `Execute` en el job template `Deploy Web Server`, permiso `Read` en el inventario de producción, y ningún acceso a las credenciales usadas por ese job template. El equipo puede lanzar el despliegue pero no puede ver las claves SSH, editar el inventario ni modificar la configuración del job template.

### Diseño de RBAC para la CoP

Una configuración práctica de RBAC para Parasol Tech:

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

Con esta configuración:

- **Admins** gestionan la infraestructura: credenciales, inventarios, proyectos y configuraciones de EE
- **Desarrolladores** crean y prueban job templates usando credenciales e inventarios existentes
- **Operadores** ejecutan job templates aprobados y aprueban workflows de despliegue sin ninguna capacidad de modificar la automatización o acceder a secretos

Esta es la gobernanza que la CoP necesitaba cuando todos ejecutaban `ansible-playbook` desde su propio portátil.

## Integración de EE

El Execution Environment construido en el Módulo 8 se integra directamente con Controller. En lugar de ejecutar playbooks con el Python que esté instalado en un servidor, Controller ejecuta cada trabajo dentro de un contenedor EE.

### Agregando EEs a Controller

Controller necesita saber de dónde obtener las imágenes EE. Hay dos enfoques:

**Desde un registro de contenedores (recomendado para producción):**

1. Sube la imagen EE a un registro de contenedores (Private Automation Hub, Quay.io, o cualquier registro OCI) -- como se mostró en el Módulo 8
2. En Controller, crea un recurso de **Execution Environment** apuntando a la URL de la imagen (ej., `hub.parasol.example/ee-images/parasoltech-ee:1.0.0`)
3. Si el registro requiere autenticación, crea una credencial de **Container Registry** y adjúntala al EE

**Desde una imagen local (para desarrollo/pruebas):**

1. Construye la imagen en el host de Controller con `ansible-builder`
2. Referencia el nombre de la imagen local en la configuración de EE de Controller

### Asignando EEs a Job Templates

Cada job template puede especificar qué EE usar. Cuando el trabajo se lanza, Controller obtiene la imagen EE (si no está en caché) y ejecuta el playbook dentro de ella.

Esto completa la historia de portabilidad del Módulo 8:

```text
Modulo 8:  Construir EE → Probar localmente con ansible-navigator
Modulo 9:  Subir EE al registro → Controller lo obtiene y usa para cada trabajo
```

Cada ejecución -- ya sea disparada por un usuario, un horario, un workflow o una llamada API -- usa la misma imagen EE con las mismas dependencias. El problema de "funciona en mi máquina" se elimina a nivel de plataforma, no solo a nivel de desarrollador individual.

### Ciclo de Vida del EE

A medida que la CoP actualiza su colección y dependencias, el ciclo de vida del EE se ve así:

1. El desarrollador actualiza `execution-environment.yml` (agregar una nueva colección, actualizar una dependencia de Python)
2. CI construye una nueva imagen EE con una nueva etiqueta de versión (ej., `parasoltech-ee:1.1.0`)
3. La imagen se sube al registro de contenedores
4. Un admin actualiza el recurso EE de Controller para apuntar a la nueva etiqueta
5. Todos los job templates que usan ese EE ahora se ejecutan con las dependencias actualizadas

Este es un proceso controlado y versionado. El EE en producción no cambia hasta que un admin deliberadamente lo actualiza. El rollback es tan simple como apuntar de vuelta a la etiqueta anterior.

## Sincronización de Proyectos y Verificación de Contenido

### Sincronización de Proyectos

Cuando Controller sincroniza un Proyecto, clona (u obtiene) el repositorio Git y pone su contenido disponible. Puedes disparar una sincronización manualmente, programarla o configurar webhooks para que un push a Git dispare automáticamente una sincronización.

El proceso de sincronización:

1. Controller se conecta al repositorio Git usando la credencial de Source Control
2. Clona el repositorio (u obtiene actualizaciones de un clon existente)
3. Escanea el repositorio en busca de archivos de playbook y los pone disponibles para Job Templates
4. Si la verificación de contenido está configurada, ejecuta la verificación de firma

### Verificación de Contenido con GPG

Aquí es donde la firma de contenido del Módulo 8 cierra el ciclo. Cuando un Proyecto tiene habilitada la verificación de contenido GPG:

1. Sube la clave pública GPG a Controller como una credencial de **GPG Public Key**
2. Configura el Proyecto para usar esta credencial para la verificación de contenido
3. En cada sincronización, Controller ejecuta el equivalente de `ansible-sign project gpg-verify .` sobre el contenido del repositorio

Si la verificación tiene éxito, el Proyecto se sincroniza normalmente y su contenido está disponible. Si la verificación falla -- porque un archivo fue modificado, agregado o eliminado después de la firma -- la sincronización falla. Ningún job template puede ejecutar el contenido no verificado.

```text
Cadena de suministro completa:

Desarrollador → Revisa codigo → Firma con ansible-sign → Push a Git
                                                              │
Controller ← Sincroniza Proyecto ← Verifica firma GPG ───────┘
     │
     └── Ejecuta playbook en EE ← Obtiene EE de Hub
```

Cada eslabón en esta cadena está verificado:

- El **contenido** está firmado y verificado (ansible-sign + GPG)
- El **runtime** está empaquetado y versionado (EE + registro de contenedores)
- El **acceso** está gobernado (RBAC + credenciales)
- La **ejecución** está auditada (logs de trabajos + notificaciones)

Esta es la práctica madura de automatización que la CoP se propuso construir.

## Ejercicios

### Ejercicio 1: Explorar la Interfaz de AAP

Inicia sesión en tu sandbox de AAP y explora las áreas principales de navegación. Identifica dónde vive cada concepto de este módulo en la interfaz:

- Organizaciones
- Proyectos
- Inventarios
- Credenciales
- Job Templates
- Workflows
- Execution Environments

!!! tip "Usa la documentación"
    La interfaz de AAP puede variar ligeramente entre versiones. Consulta la [documentación de AAP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/) para instrucciones de navegación específicas de cada versión.

### Ejercicio 2: Crear un Proyecto

Crea un Proyecto en Controller:

1. Navega a la sección de Proyectos
2. Crea un nuevo Proyecto con:
    - **Nombre**: `Parasol Infrastructure`
    - **Organización**: tu organización del sandbox
    - **Tipo de Control de Versiones**: Git
    - **URL de Control de Versiones**: la URL de tu repositorio del curso

3. Sincroniza el Proyecto y verifica que tenga éxito

Si configuraste la firma de contenido en el Módulo 8 y tienes una clave pública GPG, configura el Proyecto para verificar firmas durante la sincronización.

### Ejercicio 3: Crear un Inventario

Crea un Inventario en Controller:

1. Navega a la sección de Inventarios
2. Crea un nuevo Inventario:
    - **Nombre**: `Parasol Dev Environment`
    - **Organización**: tu organización del sandbox
3. Agrega un host manualmente (usa `localhost` con `ansible_connection: local` para pruebas en el sandbox)
4. Crea un grupo llamado `webservers` y agrega el host a él

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
5. Después de completarse, revisa los detalles del trabajo -- observa la hora de inicio, hora de fin, usuario y estado

### Ejercicio 5: Construir un Workflow Simple

Crea un Workflow que encadene dos job templates:

1. Navega a Workflow Templates
2. Crea un nuevo Workflow Template:
    - **Nombre**: `Deploy and Verify`
    - **Organización**: tu organización del sandbox
3. Abre el visualizador de workflows
4. Agrega el job template `Deploy Web Server` como el primer nodo
5. Agrega un segundo nodo (un playbook de verificación simple) conectado con una arista "On Success"
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
    Algunos entornos sandbox pueden no soportar todas las operaciones de RBAC. Si encuentras restricciones de permisos, estudia los conceptos de RBAC y el modelo de permisos en la documentación.

## Resumen

En este módulo:

- Aprendiste que Ansible Automation Platform proporciona un plano de control centralizado con tres componentes: **Controller** para orquestación y gobernanza, **Automation Hub** para distribución de contenido, y **Event-Driven Ansible** para automatización basada en eventos
- Mapeaste cada concepto de CLI a su equivalente en Controller -- los playbooks se convierten en Job Templates, los archivos de inventario en Inventarios con Sources, las claves SSH en Credenciales, y los scripts en Schedules
- Creaste Job Templates que agrupan un playbook, inventario, credenciales, EE y variables en una unidad de trabajo reutilizable y lanzable
- Construiste Workflows que encadenan job templates con aristas de éxito, fallo y siempre para crear pipelines de automatización robustos de múltiples pasos con puertas de aprobación
- Configuraste Inventarios desde hosts estáticos y fuentes SCM, y usaste Credenciales para almacenar e inyectar secretos de forma segura sin exponerlos a los usuarios
- Estableciste RBAC con Organizaciones, Equipos y roles granulares por recurso (Admin, Use, Execute, Read) para gobernar quién puede hacer qué
- Integraste el Execution Environment del Módulo 8 con Controller, asegurando que cada trabajo use el mismo runtime versionado y probado
- Completaste el flujo de seguridad de la cadena de suministro: los desarrolladores firman contenido con `ansible-sign`, hacen push a Git, y Controller verifica la firma GPG en cada sincronización de Proyecto antes de permitir la ejecución

La CoP en Parasol Tech ahora tiene una práctica de automatización completa. El contenido se desarrolla colaborativamente (Módulo 6), se prueba rigurosamente (Módulo 7), se empaqueta reproduciblemente (Módulo 8) y se gestiona a través de una plataforma gobernada con RBAC, registro de auditoría y orquestación de workflows (Módulo 9). El viaje desde Lionel ejecutando comandos ad-hoc en un portátil hasta una práctica empresarial de automatización completamente gobernada está completo.

## Conclusión del Curso

Lionel se reclina y mira el dashboard. El workflow de despliegue se ejecutó durante la noche -- Proyecto sincronizado, firmas GPG verificadas, servidores web desplegados en tres entornos, verificaciones de salud pasadas, notificaciones enviadas al canal del equipo. Nadie tuvo que conectarse por SSH a nada. Nadie escribió `ansible-playbook` a las 2 AM.

Es difícil creer que esto comenzó con un solo comando ad-hoc en un portátil.

**El viaje:**

- **Módulo 1** -- Lionel descubrió Ansible y ejecutó el primer comando ad-hoc. Un ingeniero, una máquina, un problema.
- **Módulo 2** -- Los comandos ad-hoc se convirtieron en playbooks. La automatización se volvió repetible.
- **Módulo 3** -- Los playbooks crecieron más allá de localhost. Los inventarios estructurados organizaron hosts a través de los entornos.
- **Módulo 4** -- Las variables y los facts hicieron los playbooks flexibles. La misma automatización se adaptó a diferentes entornos.
- **Módulo 5** -- Las plantillas y los handlers convirtieron los playbooks en herramientas de gestión de configuración. Los servicios se reiniciaban cuando las configuraciones cambiaban.
- **Módulo 6** -- La CoP se formó. Los roles y las colecciones convirtieron playbooks individuales en componentes reutilizables y compartibles. `ansible-creator` generó la colección. `ade` gestionó el entorno de desarrollo.
- **Módulo 7** -- Las puertas de calidad se levantaron. `ansible-lint` detectó problemas de estilo, Molecule probó los roles de extremo a extremo, pytest validó la lógica, y tox-ansible orquestó la matriz. Ningún código no probado llegó a producción.
- **Módulo 8** -- Los Execution Environments eliminaron "funciona en mi máquina." La firma de contenido con `ansible-sign` demostró que lo que se ejecuta en producción es lo que la CoP revisó. La cadena de suministro quedó asegurada.
- **Módulo 9** -- Controller trajo gobernanza. Job templates, workflows, RBAC, registro de auditoría y gestión centralizada de credenciales reemplazaron el caos de todos ejecutando playbooks desde su propio portátil.

Lo que comenzó como una persona resolviendo un problema es ahora una práctica empresarial de automatización con pruebas, empaquetado, firma y gobernanza.

### Qué Viene Después

El viaje principal está completo, pero hay más por explorar:

**Tracks de dominio (Módulos 10-11)**

- [Módulo 10 -- Sistemas Linux](10-linux-systems.md): Aplica todo lo que has aprendido a la administración de sistemas Linux -- gestión de usuarios, hardening, parcheado y cumplimiento a escala
- [Módulo 11 -- Automatización de Redes](11-network-automation.md): Extiende Ansible a dispositivos de red con `network_cli`, módulos de recursos e integración con NetBox como fuente de verdad

Estos tracks son opcionales y autocontenidos. No introducen nuevos conceptos fundamentales -- aplican las habilidades de los módulos 1-9 a dominios específicos.

**Comunidad y certificación**

- **Contribuir a Ansible** -- La comunidad de Ansible prospera con las contribuciones. Comienza mejorando la documentación, enviando reportes de errores o compartiendo roles en [Ansible Galaxy](https://galaxy.ansible.com/). Únete a la comunidad en [forum.ansible.com](https://forum.ansible.com/).
- **Certificación de Red Hat** -- Valida tus habilidades con el examen [Red Hat Certified Engineer (RHCE)](https://www.redhat.com/en/services/certification/rhce), que incluye automatización con Ansible, o el examen [Red Hat Certified Specialist in Developing Automation with Ansible Automation Platform](https://www.redhat.com/en/services/certification/red-hat-certified-specialist-developing-automation-ansible-automation-platform).
- **Ansible Development Tools** -- Continúa explorando `adt` y sus componentes. Las herramientas evolucionan rápidamente -- consulta la [documentación de Ansible Development Tools](https://ansible.readthedocs.io/projects/dev-tools/) para las últimas funcionalidades.

**Sigue practicando**

La mejor forma de aprender automatización es automatizar. Encuentra un proceso manual en tu organización, descompónlo en la jerarquía de arquitectura (landscape, tipo, función, componente), escribe un rol, pruébalo con Molecule, empaquétalo como una colección y despliégalo a través de Controller. Luego hazlo de nuevo con el siguiente proceso.

El Zen de Ansible lo dice bien: *"Ansible no es solo una herramienta -- es una práctica."* Este curso te dio las herramientas y los patrones. La práctica es tuya para construir.
