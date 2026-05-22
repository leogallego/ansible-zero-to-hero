# Módulo 8: Empaquetado y Despliegue

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Explicar qué son los Execution Environments y por qué son importantes
- Definir un EE usando `execution-environment.yml` (versión 3)
- Construir un EE con `ansible-builder` y probarlo con `ansible-navigator`
- Firmar contenido con `ansible-sign` usando claves GPG
- Describir el flujo de seguridad de la cadena de suministro (firmar → push → verificar)

## La Historia Hasta Ahora

La CoP en Parasol Tech ha construido una colección probada y verificada, `parasoltech.infrastructure`, con un rol `webserver`, tests de integración con Molecule, tests unitarios con pytest y orquestación con tox-ansible. Cada pull request pasa por las puertas de calidad antes de poder fusionarse.

Pero entonces empiezan los problemas. Un nuevo miembro del equipo ejecuta el playbook del webserver en su portátil y obtiene un resultado diferente. Su entorno local de Python carece de una dependencia. Otro miembro del equipo trabaja en un sistema operativo distinto y tiene un conflicto de versiones en `ansible.posix`. El servidor de staging tiene una versión de `ansible-core` más antigua que la que el equipo usó para las pruebas.

"Lo probamos," dice Lionel. "Pasó todas las pruebas."

Jordan suspira. "Pasó en *nuestras* máquinas. El servidor de staging tiene un entorno de Python completamente diferente."

La CoP identifica dos problemas:

1. **Portabilidad**: la automatización funciona solo cuando el entorno de ejecución coincide con el que el desarrollador usó para probar. Cada máquina tiene diferentes paquetes de Python, bibliotecas del sistema y versiones de Ansible.
2. **Integridad**: cualquier persona con acceso de push al repositorio Git puede modificar los playbooks. No hay forma de demostrar que el contenido que se ejecuta en producción es el mismo que la CoP revisó y aprobó.

Las soluciones: **Execution Environments** para la portabilidad, y **firma de contenido** para la integridad.

## Execution Environments

Un Execution Environment (EE) es una imagen de contenedor que empaqueta todo lo que Ansible necesita para ejecutarse: `ansible-core`, dependencias de Python, paquetes del sistema y colecciones. Cuando ejecutas un playbook dentro de un EE, la ejecución utiliza el entorno del contenedor, no lo que esté instalado en la máquina anfitriona.

Esto resuelve el problema de "funciona en mi máquina". La imagen del contenedor es inmutable y versionada. Si funciona en desarrollo, funciona en staging. Si funciona en staging, funciona en producción. Cada ejecución utiliza exactamente las mismas dependencias.

### Cómo Funcionan los EEs

Sin un EE, Ansible se ejecuta en el nodo de control usando el intérprete de Python y los paquetes instalados localmente:

```text
Nodo de control (tu portatil)
├── ansible-core 2.17
├── Python 3.11
├── ansible.posix 1.5.4
├── Falta: alguna-lib-python  ← falla en ejecucion
└── playbook.yml
```

Con un EE, Ansible se ejecuta dentro de un contenedor que tiene todo preinstalado:

```text
Imagen de contenedor (EE)
├── ansible-core 2.19
├── Python 3.12
├── ansible.posix 2.1.0
├── alguna-lib-python 3.0
└── (todas las dependencias bloqueadas)

Nodo de control
├── podman (o docker)
├── ansible-navigator
└── playbook.yml  ← se ejecuta DENTRO del contenedor
```

El archivo de playbook permanece en el nodo de control. `ansible-navigator` lo monta en el contenedor en tiempo de ejecución. La ejecución ocurre dentro del contenedor, usando el Python, los módulos y las bibliotecas del contenedor.

### El Ecosistema de EEs

Tres herramientas trabajan juntas:

| Herramienta | Propósito |
|-------------|-----------|
| **`ansible-builder`** | Construye imágenes de contenedor EE a partir de un archivo de definición |
| **`ansible-navigator`** | Ejecuta playbooks dentro de contenedores EE |
| **`podman`** (o `docker`) | El runtime de contenedores que ejecuta la imagen |

Ya usaste `ansible-navigator` en el Módulo 2. Ahora aprenderás a construir las imágenes dentro de las cuales se ejecuta.

## Definiendo un EE

La definición del EE reside en `execution-environment.yml`. Este archivo le indica a `ansible-builder` qué incluir dentro de la imagen del contenedor.

La definición de `parasoltech-ee` para la colección de la CoP se encuentra en `ansible/execution-environments/parasoltech-ee/execution-environment.yml`:

```yaml
---
version: 3

images:
  base_image:
    name: ghcr.io/ansible/community-ee-base:latest

dependencies:
  galaxy: requirements.yml
  python: []
  system: []
```

Y el archivo `requirements.yml` complementario:

```yaml
---
collections:
  - name: parasoltech.infrastructure
  - name: ansible.posix
```

### El Esquema Versión 3

El esquema `version: 3` es el estándar actual para definiciones de EE. Reemplazó las versiones 1 y 2, que tenían una estructura diferente. Usa siempre la versión 3 para nuevos proyectos de EE.

### Secciones del Esquema

#### `images`

La `base_image` especifica la imagen de contenedor inicial. `ansible-builder` agrega tus dependencias sobre esta base.

Imágenes base comunes:

| Imagen | Contenido |
|--------|-----------|
| `ghcr.io/ansible/community-ee-base:latest` | `ansible-core`, Python y dependencias comunes para construir EEs personalizados |
| `ghcr.io/ansible/community-ee-minimal:latest` | Runtime mínimo con solo `ansible-core`, para EEs de producción ligeros |
| `registry.redhat.io/ansible-automation-platform/ee-minimal-rhel9` | EE mínimo soportado por Red Hat para producción |
| `registry.redhat.io/ansible-automation-platform/ee-supported-rhel9` | EE soportado por Red Hat con colecciones certificadas |

Para desarrollo, `community-ee-base` es un buen punto de partida porque incluye dependencias comunes. Para producción, usa una imagen base mínima para reducir la superficie de ataque y el tamaño de la imagen.

#### `dependencies`

Se pueden declarar tres tipos de dependencias:

- **`galaxy`**: Apunta a un archivo `requirements.yml` que lista colecciones Ansible. Se instalan con `ansible-galaxy collection install` durante la construcción.
- **`python`**: Una lista de paquetes Python (o una ruta a un archivo `requirements.txt`). Se instalan con `pip` durante la construcción.
- **`system`**: Una lista de paquetes del sistema (o una ruta a un archivo `bindep.txt`). Se instalan con el gestor de paquetes del sistema (`dnf`, `apt`, etc.) durante la construcción.

La separación es importante. Las colecciones van en `galaxy`, sus dependencias de Python en `python`, y sus dependencias de bibliotecas del sistema en `system`. Esto refleja cómo instalarías dependencias manualmente, pero `ansible-builder` lo automatiza dentro de la construcción del contenedor.

#### Secciones Opcionales

El esquema versión 3 soporta secciones adicionales para casos de uso avanzados:

```yaml
---
version: 3

images:
  base_image:
    name: ghcr.io/ansible/community-ee-base:latest

dependencies:
  galaxy: requirements.yml
  python:
    - jmespath
    - netaddr
  system:
    - iputils

additional_build_files:
  - src: custom-ansible.cfg
    dest: configs

additional_build_steps:
  prepend_final:
    - COPY _build/configs/custom-ansible.cfg /etc/ansible/ansible.cfg
  append_final:
    - RUN echo "Build complete"

options:
  tags:
    - parasoltech-ee:1.0.0
    - parasoltech-ee:latest
  package_manager_path: /usr/bin/dnf
```

- **`additional_build_files`**: Copia archivos adicionales en el contexto de construcción. Útil para archivos de configuración personalizados, scripts o tarballs de colecciones locales.
- **`additional_build_steps`**: Inyecta instrucciones personalizadas del Containerfile en puntos específicos de la construcción (`prepend_base`, `append_base`, `prepend_galaxy`, `append_galaxy`, `prepend_builder`, `append_builder`, `prepend_final`, `append_final`).
- **`options`**: Opciones de construcción como etiquetas de imagen y la ruta del gestor de paquetes.

!!! tip "Mantenlo simple"
    Para la mayoría de los casos de uso, solo necesitas `images`, `dependencies` y quizás `options.tags`. Las secciones avanzadas existen para casos extremos, así que no agregues complejidad hasta que la necesites.

## Construyendo con ansible-builder

`ansible-builder` toma la definición del EE y produce una imagen de contenedor. Funciona en dos pasos: primero genera un Containerfile, luego construye la imagen.

### Paso 1: Previsualizar el Containerfile

Antes de construir, puedes inspeccionar lo que hará `ansible-builder`:

```bash
cd ansible/execution-environments/parasoltech-ee
ansible-builder create
```

Esto genera un directorio `context/` que contiene un `Containerfile` y todos los archivos necesarios para la construcción. Abre `context/Containerfile` para ver las cuatro etapas:

```text
context/
  Containerfile    # La definicion de construccion multi-etapa
  _build/
    requirements.yml    # Dependencias de Galaxy
    ...
```

El Containerfile generado tiene cuatro etapas:

| Etapa | Propósito |
|-------|-----------|
| **Base** | Parte de la imagen base, instala paquetes del sistema |
| **Galaxy** | Instala colecciones Ansible desde `requirements.yml` |
| **Builder** | Instala paquetes Python, compila extensiones nativas |
| **Final** | Ensambla la imagen final a partir de las etapas anteriores |

Este enfoque multi-etapa mantiene la imagen final pequeña. Las herramientas de construcción y los artefactos de compilación se descartan; solo las dependencias de runtime llegan a la imagen final.

!!! note "Inspecciona antes de construir"
    Ejecutar `ansible-builder create` es una ejecución en seco. Genera el Containerfile sin construir nada. Úsalo para verificar que tu definición de EE es correcta antes de comprometerte con una construcción completa, que puede tomar varios minutos.

### Paso 2: Construir la Imagen

Construye la imagen con una etiqueta:

```bash
ansible-builder build --tag parasoltech-ee:1.0.0
```

Para salida detallada durante la construcción:

```bash
ansible-builder build --tag parasoltech-ee:1.0.0 -v 3
```

El flag `-v 3` establece la máxima verbosidad para que puedas ver cada paso de la construcción del contenedor. Esto es útil para depurar fallos en la instalación de dependencias.

Cuando la construcción se completa:

```text
[4/4] STEP 22/22: CMD ["bash"]
[4/4] COMMIT parasoltech-ee:1.0.0
--> a1b2c3d4e5f6
Successfully tagged localhost/parasoltech-ee:1.0.0

Complete! The build context can be found at:
  /path/to/parasoltech-ee/context
```

### Trabajando con Colecciones Locales

Si tu colección aún no está publicada en Galaxy o Automation Hub, necesitas empaquetarla como un tarball y referenciarla localmente en la definición del EE.

Primero, construye el tarball de la colección:

```bash
cd ansible/collections/parasoltech/infrastructure
ansible-galaxy collection build \
  --output-path ../../execution-environments/parasoltech-ee/
```

Luego modifica la definición del EE para usar el tarball local:

```yaml
---
version: 3

images:
  base_image:
    name: ghcr.io/ansible/community-ee-base:latest

dependencies:
  python_interpreter:
    python_path: /usr/bin/python3

  galaxy:
    collections:
      - name: collection_tarballs/parasoltech-infrastructure-1.0.0.tar.gz
        type: file
  python: []
  system: []

additional_build_files:
  - src: parasoltech-infrastructure-1.0.0.tar.gz
    dest: collection_tarballs
```

El `type: file` le dice a `ansible-galaxy` que instale desde la ruta local en vez de descargar desde Galaxy. La sección `additional_build_files` copia el tarball en el contexto de construcción donde la etapa Galaxy puede encontrarlo.

## Probando tu EE

Después de construir, verifica la imagen antes de desplegarla en cualquier lugar.

### Verificar con podman

Comprueba que la imagen existe y que las colecciones están instaladas:

```bash
# Listar imagenes locales
podman images | grep parasoltech

# Verificar la version de ansible-core dentro del EE
podman run --rm parasoltech-ee:1.0.0 ansible --version

# Listar colecciones instaladas
podman run --rm parasoltech-ee:1.0.0 \
  ansible-galaxy collection list
```

Salida esperada de la lista de colecciones:

```text
# /usr/share/ansible/collections/ansible_collections
Collection                   Version
---------------------------- -------
ansible.posix                2.1.0
parasoltech.infrastructure   1.0.0
```

### Probar con ansible-navigator

Ejecuta el playbook del webserver usando el EE personalizado:

```bash
ansible-navigator run \
  ansible/playbooks/module-05/deploy-webserver.yml \
  --execution-environment-image parasoltech-ee:1.0.0 \
  --pull-policy never
```

El flag `--pull-policy never` le indica a `ansible-navigator` que use la imagen local en vez de intentar descargarla de un registro. Esto es importante durante el desarrollo cuando la imagen solo existe localmente.

Si el playbook se ejecuta exitosamente dentro del EE, el entorno está correctamente empaquetado. Cada máquina que use esta imagen obtendrá el mismo resultado.

!!! tip "Desarrollo iterativo"
    Durante el desarrollo de EEs, usa el ciclo `create` → `build` → `test`:

    1. Edita `execution-environment.yml`
    2. Ejecuta `ansible-builder create` para previsualizar el Containerfile
    3. Ejecuta `ansible-builder build --tag parasoltech-ee:dev` para construir
    4. Ejecuta `podman run --rm parasoltech-ee:dev ansible-galaxy collection list` para verificar
    5. Ejecuta un playbook con `ansible-navigator` para probar de extremo a extremo

    Solo etiqueta con un número de versión (como `1.0.0`) cuando el EE esté validado y listo para promoción.

## Firma de Contenido con ansible-sign

Los Execution Environments resuelven el problema de portabilidad. La firma de contenido resuelve el problema de integridad.

`ansible-sign` es una utilidad que firma y verifica directorios de proyectos Ansible. Funciona de la siguiente manera:

1. Calcula checksums SHA-256 de cada archivo que quieres proteger
2. Escribe esos checksums en un archivo de manifiesto
3. Firma el manifiesto con una clave GPG

Cualquier persona con la clave pública correspondiente puede verificar que el contenido no ha sido alterado: ningún archivo modificado, ningún archivo añadido, ningún archivo eliminado.

### Configuración de Claves GPG

`ansible-sign` utiliza claves de GNU Privacy Guard (GPG). Si no tienes una clave GPG, crea una usando un archivo batch para generación no interactiva:

Crea un archivo llamado `gpg-batch.txt`:

```text
%echo Generating a GPG key for ansible-sign
Key-Type: default
Key-Length: 4096
Subkey-Type: default
Subkey-Length: default
Name-Real: Parasol Tech Automation
Name-Comment: content signing key
Name-Email: automation@parasol.example
Expire-Date: 1y
%no-ask-passphrase
%no-protection
%commit
%echo done
```

Genera la clave:

```bash
gpg --batch --gen-key gpg-batch.txt
```

Verifica que se creó:

```bash
gpg --list-secret-keys
```

```text
sec   rsa4096 2026-05-21 [SC] [expires: 2027-05-21]
      ABCDEF1234567890ABCDEF1234567890ABCDEF12
uid           [ultimate] Parasol Tech Automation (content signing key) <automation@parasol.example>
ssb   rsa3072 2026-05-21 [E]
```

!!! warning "Gestión de claves en producción"
    El ejemplo anterior crea una clave sin frase de paso por simplicidad. En producción, usa siempre una clave protegida con frase de paso y almacénala en un sistema seguro de gestión de claves. Nunca guardes claves privadas en el control de versiones.

### El Archivo MANIFEST.in

Antes de firmar, necesitas un archivo `MANIFEST.in` que le indica a `ansible-sign` qué archivos incluir en el manifiesto de checksums. Este archivo usa la sintaxis de `distlib.manifest` de Python, el mismo formato utilizado por las herramientas de empaquetado de Python.

El ejemplo de firma en `ansible/execution-environments/signing-example/MANIFEST.in`:

```text
# Excluir artefactos de control de versiones y desarrollo
global-exclude .git
global-exclude .git/*
prune .git

# Incluir todos los playbooks
recursive-include . *.yml
recursive-include . *.yaml

# Incluir documentacion
include README.md

# Excluir archivos de prueba y temporales
prune .tox
prune .venv
prune tmp
global-exclude *.pyc
global-exclude __pycache__
```

Directivas clave:

| Directiva | Significado |
|-----------|-------------|
| `include <archivo>` | Incluye un archivo específico |
| `recursive-include <dir> <patron>` | Incluye todos los archivos que coincidan con el patrón en el directorio y subdirectorios |
| `global-exclude <patron>` | Excluye archivos que coincidan con el patrón en todas partes |
| `prune <dir>` | Excluye un árbol de directorios completo |

El principio: incluye todo lo que afecta la ejecución (playbooks, roles, inventario, configuración), excluye todo lo que no (control de versiones, artefactos de prueba, cachés).

### Firma y Verificación

Con la clave GPG y el `MANIFEST.in` en su lugar, firmar es un solo comando.

**Firmar el proyecto:**

```bash
cd ansible/execution-environments/signing-example
ansible-sign project gpg-sign .
```

```text
[OK   ] GPG signing successful!
[NOTE ] Checksum manifest: ./.ansible-sign/sha256sum.txt
[NOTE ] GPG summary: signature created
```

Esto crea dos archivos dentro de `.ansible-sign/`:

```text
.ansible-sign/
  sha256sum.txt       # Manifiesto de checksums (un hash por archivo)
  sha256sum.txt.sig   # Firma GPG del manifiesto
```

El archivo `sha256sum.txt` contiene una línea por cada archivo protegido:

```text
a1b2c3d4...  ./playbook.yml
e5f6a7b8...  ./README.md
```

**Verificar el proyecto:**

```bash
ansible-sign project gpg-verify .
```

```text
[OK   ] GPG signature verification succeeded.
[NOTE ] Checksum manifest: ./.ansible-sign/sha256sum.txt
[NOTE ] GPG summary: valid signature
```

Si algún archivo ha sido modificado, añadido o eliminado desde la firma, la verificación falla:

```text
[FAIL ] GPG signature verification FAILED.
[NOTE ] Modified: ./playbook.yml
```

### Flujo de Seguridad de la Cadena de Suministro

La firma de contenido se vuelve poderosa cuando se integra en el pipeline de despliegue. El flujo es:

```text
Estacion del desarrollador     Repositorio Git         AAP Controller
┌──────────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ 1. Escribir contenido│     │                  │     │                  │
│ 2. Ejecutar pruebas  │────▶│ 3. Push contenido│────▶│ 4. Project Sync  │
│ 3. Firmar proyecto   │     │    firmado       │     │ 5. Verificar     │
│    (gpg-sign)        │     │                  │     │    firma GPG     │
└──────────────────────┘     └──────────────────┘     │ 6. Ejecutar si   │
                                                      │    es valido     │
                                                      └──────────────────┘
```

1. **El desarrollador firma**: Después de que la CoP revisa y aprueba los cambios, un firmante de confianza ejecuta `ansible-sign project gpg-sign .` en el directorio del proyecto.
2. **Push a Git**: El contenido firmado (incluyendo `.ansible-sign/`) se confirma y se sube al repositorio.
3. **Project Sync de AAP**: El Controller de Ansible Automation Platform descarga el repositorio.
4. **AAP verifica**: Controller está configurado con la clave pública GPG como credencial. Durante el Project Sync, ejecuta el equivalente de `ansible-sign project gpg-verify .` sobre el contenido descargado.
5. **Ejecutar o rechazar**: Si la verificación tiene éxito, el contenido es de confianza y puede ejecutarse. Si falla, la sincronización falla y ningún job template puede ejecutarse. El contenido queda bloqueado.

Esto significa que incluso si un atacante compromete el repositorio Git y modifica un playbook, el contenido no se ejecutará. Los checksums no coincidirán, la firma GPG será inválida y AAP rechazará el contenido.

!!! note "Dos capas de confianza"
    La firma de contenido protege el **contenido** (playbooks, roles, inventario). Los Execution Environments protegen el **runtime** (Python, colecciones, paquetes del sistema). Juntos, forman un modelo completo de seguridad de la cadena de suministro: sabes exactamente qué código se ejecutará y exactamente en qué entorno se ejecutará.

## Publicación en Automation Hub

Una vez que la imagen del EE está construida y probada, el siguiente paso es publicarla en un registro de contenedores donde AAP Controller pueda descargarla. Los destinos típicos son:

- **Private Automation Hub**: El registro interno de la organización, parte de AAP. Es el destino recomendado para imágenes de EE en producción.
- **Quay.io**: El registro de contenedores público/privado de Red Hat.
- **Cualquier registro compatible con OCI**: Harbor, Docker Hub, GitLab Container Registry, etc.

### Push a un Registro

Etiquetar y subir usando `podman`:

```bash
# Etiquetar para el registro destino
podman tag parasoltech-ee:1.0.0 \
  hub.parasol.example/ee-images/parasoltech-ee:1.0.0

# Iniciar sesion en el registro
podman login hub.parasol.example

# Subir la imagen
podman push hub.parasol.example/ee-images/parasoltech-ee:1.0.0
```

### Publicar la Colección

La colección en sí puede publicarse en Automation Hub o Galaxy:

```bash
cd ansible/collections/parasoltech/infrastructure

# Construir el tarball de la coleccion
ansible-galaxy collection build

# Publicar en Private Automation Hub
ansible-galaxy collection publish \
  parasoltech-infrastructure-1.0.0.tar.gz \
  --server https://hub.parasol.example/api/galaxy/content/published/ \
  --token <tu-token-api>
```

Una vez publicada, otros equipos pueden instalar la colección desde Automation Hub en vez de copiar archivos, y las definiciones de EE pueden referenciar la colección publicada en vez de usar tarballs locales.

### El Ciclo de Vida Completo

El ciclo de vida completo de empaquetado y despliegue para la CoP se ve así:

```text
1. Desarrollar  ──▶  Escribir roles y playbooks
2. Probar       ──▶  ansible-lint + pytest + molecule + tox-ansible
3. Empaquetar   ──▶  ansible-builder build --tag parasoltech-ee:1.0.0
4. Probar EE    ──▶  ansible-navigator run ... --eei parasoltech-ee:1.0.0
5. Firmar       ──▶  ansible-sign project gpg-sign .
6. Publicar     ──▶  Push del EE al registro, coleccion al Hub
7. Desplegar    ──▶  AAP descarga, verifica, ejecuta
```

Cada paso se basa en el anterior. Nada llega a producción sin pasar por cada puerta.

## Ejercicios

### Ejercicio 1: Construir un Execution Environment

Navega al directorio del EE y previsualiza la construcción:

```bash
cd ansible/execution-environments/parasoltech-ee
ansible-builder create
```

Examina el `context/Containerfile` generado. Identifica las cuatro etapas de construcción y comprende qué hace cada una. Luego construye la imagen:

```bash
ansible-builder build --tag parasoltech-ee:latest
```

Verifica que la imagen existe:

```bash
podman images | grep parasoltech
```

### Ejercicio 2: Probar el EE

Ejecuta un comando dentro del EE para verificar que las colecciones están instaladas:

```bash
podman run --rm parasoltech-ee:latest \
  ansible-galaxy collection list
```

Confirma que `parasoltech.infrastructure` y `ansible.posix` aparecen en la salida.

### Ejercicio 3: Agregar una Dependencia Python

Modifica `execution-environment.yml` para agregar `jmespath` como dependencia Python:

```yaml
dependencies:
  galaxy: requirements.yml
  python:
    - jmespath
  system: []
```

Reconstruye el EE y verifica que `jmespath` está instalado:

```bash
ansible-builder build --tag parasoltech-ee:latest
podman run --rm parasoltech-ee:latest \
  python3 -c "import jmespath; print(jmespath.__version__)"
```

### Ejercicio 4: Firmar un Proyecto

Navega al ejemplo de firma y crea una clave GPG:

```bash
cd ansible/execution-environments/signing-example
gpg --batch --gen-key gpg-batch.txt
```

Firma el proyecto:

```bash
ansible-sign project gpg-sign .
```

Verifica la firma:

```bash
ansible-sign project gpg-verify .
```

Ahora modifica un archivo y verifica de nuevo. La verificación debería fallar.

??? example "Solución"
    ```bash
    # Modificar un archivo firmado
    echo "# alterado" >> MANIFEST.in

    # La verificacion deberia fallar
    ansible-sign project gpg-verify .
    # [FAIL] GPG signature verification FAILED.

    # Restaurar el archivo original
    git checkout MANIFEST.in

    # Re-verificar — deberia pasar de nuevo
    ansible-sign project gpg-verify .
    # [OK] GPG signature verification succeeded.
    ```

### Ejercicio 5: Ejecutar un Playbook en el EE

Usa `ansible-navigator` para ejecutar un playbook dentro del EE personalizado:

```bash
ansible-navigator run \
  ansible/playbooks/module-05/deploy-webserver.yml \
  --execution-environment-image parasoltech-ee:latest \
  --pull-policy never \
  --mode stdout
```

Compara la salida con la ejecución del mismo playbook sin un EE. Los resultados deberían ser idénticos, pero el entorno de ejecución es ahora portable y reproducible.

## Resumen

En este módulo:

- Aprendiste que los Execution Environments son imágenes de contenedor que empaquetan `ansible-core`, colecciones, paquetes Python y dependencias del sistema en un runtime inmutable y portable
- Definiste un EE usando el esquema versión 3 de `execution-environment.yml`, especificando una imagen base y dependencias en tres categorías (galaxy, python, system)
- Usaste `ansible-builder create` para previsualizar el Containerfile multi-etapa generado, y `ansible-builder build` para producir la imagen de contenedor
- Probaste el EE con `podman` para verificaciones rápidas y `ansible-navigator` para ejecución de playbooks de extremo a extremo
- Configuraste claves GPG y un archivo `MANIFEST.in` para firmar proyectos Ansible con `ansible-sign`, creando manifiestos de checksums protegidos por firmas criptográficas
- Comprendiste el flujo de seguridad de la cadena de suministro donde los desarrolladores firman contenido, lo suben a Git, y el Controller de AAP verifica la firma GPG antes de permitir la ejecución
- Publicaste imágenes de EE en registros de contenedores y colecciones en Automation Hub, completando el ciclo de vida de empaquetado

La CoP en Parasol Tech ahora tiene un pipeline completo: el código se prueba (Módulo 7), se empaqueta en Execution Environments, se firma para integridad y se publica para consumo. No más conflictos de dependencias, no más "funciona en mi máquina" y no más contenido sin verificar ejecutándose en producción.

## Próximos Pasos

Siguiente: [Módulo 9: Escalando con AAP](9-scaling-with-aap.md)
