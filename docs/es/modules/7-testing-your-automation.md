# Modulo 7: Testing de tu Automatizacion

## Objetivos de Aprendizaje

Al finalizar este modulo seras capaz de:

- Ejecutar `ansible-lint` para analisis estatico y configurar reglas de auto-correccion
- Escribir y ejecutar tests de integracion con Molecule usando verificacion basada en aserciones
- Crear tests funcionales con `pytest-ansible`
- Orquestar matrices de tests con `tox-ansible`
- Describir la piramide de testing de Ansible (lint -> unit -> integration)

## La Historia Hasta Ahora

La CoP en Parasol Tech tiene su primera coleccion -- `parasoltech.infrastructure` con un rol `webserver` que instala paquetes, despliega configuracion desde plantillas y gestiona el ciclo de vida del servicio. Varios equipos estan empezando a adoptarla.

Entonces algo se rompe. El equipo de monitoreo sobreescribe `webserver_port` con una cadena de texto en lugar de un entero, y la plantilla genera basura. Jordan lo detecta durante una revision de codigo, pero ya se habia desplegado a staging.

"Tuvimos suerte," dice Alex. "La proxima vez podria ser produccion."

La CoP convoca una reunion de emergencia. El resultado: **ninguna automatizacion sin testear va a produccion.** Cada rol necesita tests automatizados. Cada pull request debe pasar linting, tests unitarios y tests de integracion antes de poder fusionarse. El equipo acuerda una estrategia de testing usando cuatro herramientas de la suite `ansible-dev-tools`: `ansible-lint`, Molecule, `pytest-ansible` y `tox-ansible`.

## La Piramide de Testing de Ansible

El testing no es una unica cosa -- es un espectro de verificaciones a diferentes niveles de abstraccion y costo. La piramide de testing de Ansible organiza estos niveles desde los mas baratos y rapidos en la base hasta los mas completos y lentos en la cima:

```text
          /\
         /  \
        / In \         Tests de integracion (Molecule)
       / tegr \        Aplica el rol a hosts reales, verifica postcondiciones
      / acion  \
     /----------\
    /   Unit     \     Tests unitarios (pytest-ansible)
   /   Tests      \    Valida componentes individuales en aislamiento
  /----------------\
 / Analisis Estatico \ Linting (ansible-lint)
/  (ansible-lint)     \Rapido, barato, detecta errores de estilo y sintaxis
/______________________\
```

| Nivel | Herramienta | Que detecta | Velocidad |
|-------|-------------|-------------|-----------|
| **Lint** | `ansible-lint` | Errores de sintaxis, modulos deprecados, violaciones de nomenclatura, FQCNs faltantes | Segundos |
| **Unit** | `pytest-ansible` | Defaults incorrectos, argument specs rotos, errores de logica en modulos | Segundos |
| **Integracion** | Molecule | Fallos del rol en sistemas reales, plantillas faltantes, errores de configuracion de servicios | Minutos |

El principio es simple: detectar tanto como sea posible en los niveles inferiores, porque esos tests son rapidos, baratos y se ejecutan en cada guardado. Reserva los tests de integracion para lo que solo se puede validar aplicando realmente el rol.

## Analisis Estatico con ansible-lint

`ansible-lint` verifica tu contenido Ansible contra un conjunto completo de reglas -- desde formato YAML hasta uso de modulos deprecados pasando por convenciones de nomenclatura. Es la primera linea de defensa y detecta los errores mas comunes antes de que siquiera ejecutes un playbook.

### Configuracion

La coleccion incluye un archivo `.ansible-lint` en su raiz:

```yaml
---
profile: production
strict: true

exclude_paths:
  - .tox
  - .venv
  - collections
  - .ade

enable_list:
  - fqcn
  - args
  - name

warn_list:
  - experimental

skip_list:
  - galaxy[version-incorrect]

offline: false
project_dir: .
```

Configuraciones clave:

- **`profile: production`** -- Usa el conjunto de reglas integrado mas estricto. Otras opciones son `min`, `basic`, `moderate`, `safety` y `shared`, cada una agregando mas reglas.
- **`strict: true`** -- Las advertencias se tratan como errores. Si `ansible-lint` encuentra algo, el codigo de salida es distinto de cero.
- **`enable_list`** -- Habilita explicitamente categorias de reglas para soporte de auto-correccion.
- **`skip_list`** -- Suprime reglas especificas que no aplican (en este caso, la regla `galaxy[version-incorrect]` que marca versiones no publicadas en Galaxy).

### Ejecutando ansible-lint

Desde la raiz de la coleccion:

```bash
cd ansible/collections/parasoltech/infrastructure
ansible-lint
```

Si no hay violaciones, la salida esta limpia. Si hay problemas, `ansible-lint` muestra el archivo, numero de linea, ID de regla y una descripcion:

```text
roles/webserver/tasks/main.yml:5: fqcn[action-core]
  Use FQCN for builtin module actions.

roles/webserver/handlers/main.yml:8: name[casing]
  All names should start with an uppercase letter.
```

### Auto-correccion

Muchas reglas soportan correccion automatica. En lugar de editar manualmente cada archivo, ejecuta:

```bash
ansible-lint --fix
```

`ansible-lint` reescribe los archivos in situ, corrigiendo lo que puede. Las correcciones automaticas comunes incluyen:

- Reemplazar nombres cortos de modulos con FQCNs (`copy` se convierte en `ansible.builtin.copy`)
- Convertir `yes`/`no` a `true`/`false`
- Corregir formato YAML (espacios finales, indentacion)

Despues de la auto-correccion, revisa los cambios con `git diff` antes de hacer commit. No toda auto-correccion es perfecta -- siempre verifica.

!!! tip "Integracion con el IDE"
    `ansible-lint` se integra con VS Code a traves de la extension de Ansible. Las violaciones aparecen como subrayados ondulados en el editor, y la auto-correccion esta disponible a traves del menu de correccion rapida (Ctrl+.). Esto te da retroalimentacion instantanea mientras escribes.

### Categorias de Reglas

`ansible-lint` organiza las reglas en categorias:

| Categoria | Ejemplos |
|-----------|----------|
| **fqcn** | Usar FQCNs para todos los modulos |
| **name** | Los nombres de tareas deben comenzar con mayuscula, usar forma imperativa |
| **args** | Argumentos requeridos faltantes, argumentos deprecados usados |
| **yaml** | Errores de indentacion, espacios finales, valores truthy |
| **no-changed-when** | Tareas `command`/`shell` sin `changed_when` |
| **risky-file-permissions** | Tareas de archivos sin `mode` explicito |
| **role-name** | Nombres de roles con guiones o caracteres invalidos |
| **galaxy** | Problemas en metadatos de la coleccion |

Cada categoria corresponde a reglas que ya has aprendido en este curso. `ansible-lint` las aplica automaticamente en lugar de depender de la revision de codigo.

## Testing de Integracion con Molecule

Mientras que `ansible-lint` detecta problemas estaticos, Molecule detecta los dinamicos -- problemas que solo aparecen cuando realmente aplicas un rol a un sistema. La plantilla se renderiza correctamente? El servicio arranca? El archivo de configuracion termina en el lugar correcto?

Molecule proporciona un framework para testing de integracion de contenido Ansible. Crea entornos de prueba, aplica tus roles, ejecuta aserciones de verificacion y desmonta todo.

### Escenarios de Molecule

Un **escenario** es una definicion de test completa. Cada escenario vive en su propio directorio bajo `extensions/molecule/` y contiene como minimo un archivo de configuracion `molecule.yml`. La mayoria de los escenarios tambien incluyen un playbook `converge.yml` y un playbook `verify.yml`.

El escenario de la coleccion para el rol webserver esta en:

```text
extensions/molecule/integration_webserver/
  molecule.yml    # Configuracion del escenario
  converge.yml    # Playbook que aplica el rol
  verify.yml      # Verificacion basada en aserciones
```

#### molecule.yml

La configuracion del escenario define el entorno de test y el ciclo de vida:

```yaml
---
dependency:
  name: galaxy
  options:
    requirements-file: ${MOLECULE_SCENARIO_DIRECTORY}/../../../requirements.yml
    force: false

driver:
  name: delegated
  options:
    managed: false
    ansible_connection_options:
      ansible_connection: local

platforms:
  - name: localhost
    managed: false
    groups:
      - webservers

provisioner:
  name: ansible
  inventory:
    host_vars:
      localhost:
        ansible_connection: local
        ansible_python_interpreter: "{{ ansible_playbook_python }}"

verifier:
  name: ansible

scenario:
  name: integration_webserver
  test_sequence:
    - dependency
    - cleanup
    - destroy
    - syntax
    - create
    - prepare
    - converge
    - verify
    - cleanup
    - destroy
```

Secciones clave:

- **`driver: delegated`** -- Usa el driver delegado en lugar de contenedores. Esto significa que Molecule ejecuta todo en localhost sin necesitar Docker o Podman. Es mas simple para aprender y funciona en cualquier entorno.
- **`platforms`** -- Define los hosts de prueba. Con el driver delegado, `localhost` es la unica plataforma.
- **`provisioner`** -- Configura como se ejecuta Ansible. La seccion de inventario establece las variables de conexion para localhost.
- **`verifier: ansible`** -- Usa playbooks de Ansible para la verificacion en lugar de una herramienta separada como Testinfra.
- **`scenario.test_sequence`** -- La lista ordenada de etapas que `molecule test` ejecuta.

#### converge.yml

El playbook converge aplica el rol bajo prueba:

```yaml
---
- name: Converge — aplicar el rol webserver
  hosts: all
  gather_facts: true

  tasks:
    - name: Include the webserver role
      ansible.builtin.include_role:
        name: parasoltech.infrastructure.webserver
      vars:
        webserver_port: 8080
        webserver_server_name: test.parasol.example
        webserver_document_root: /tmp/molecule-webserver
        webserver_service_enabled: false
```

Observa los valores especificos para testing:

- **Puerto 8080** en lugar de 80 (evita necesitar privilegios de root)
- **`/tmp/molecule-webserver`** como document root (escribible sin root)
- **`webserver_service_enabled: false`** (no se necesita un servicio httpd real para la verificacion)

Estos valores hacen que el test sea portable -- se ejecuta en cualquier lugar sin privilegios elevados ni servicios instalados.

### Escribiendo Aserciones

El playbook `verify.yml` contiene tareas de asercion que verifican postcondiciones -- cosas que deberian ser verdaderas despues de que el rol se ha ejecutado:

```yaml
---
- name: Verify — verificar postcondiciones del rol webserver
  hosts: all
  gather_facts: false

  vars:
    __verify_document_root: /tmp/molecule-webserver
    __verify_server_name: test.parasol.example

  tasks:
    - name: Check that the document root directory exists
      ansible.builtin.stat:
        path: "{{ __verify_document_root }}"
      register: __verify_docroot_stat

    - name: Assert document root was created
      ansible.builtin.assert:
        that:
          - __verify_docroot_stat.stat.exists
          - __verify_docroot_stat.stat.isdir
        fail_msg: >-
          El document root {{ __verify_document_root }} no existe
          o no es un directorio.
        success_msg: >-
          El document root {{ __verify_document_root }} existe.

    - name: Read the index page content
      ansible.builtin.slurp:
        src: "{{ __verify_document_root }}/index.html"
      register: __verify_index_content

    - name: Assert index page contains the server name
      ansible.builtin.assert:
        that:
          - >-
            __verify_server_name in
            (__verify_index_content.content | b64decode)
        fail_msg: >-
          El index.html no contiene el server name esperado.
        success_msg: >-
          index.html contiene el server name correcto.

    - name: Assert index page contains the ansible_managed header
      ansible.builtin.assert:
        that:
          - >-
            'Ansible managed' in
            (__verify_index_content.content | b64decode)
        fail_msg: >-
          Al index.html le falta la cabecera ansible_managed.
        success_msg: >-
          index.html contiene la cabecera ansible_managed.
```

El patron para cada asercion es:

1. **Recopilar un hecho** -- usar `ansible.builtin.stat`, `ansible.builtin.slurp` u otro modulo de solo lectura para capturar estado
2. **Verificar la condicion** -- usar `ansible.builtin.assert` con `that:`, `fail_msg:` y `success_msg:`

!!! warning "Usa `ansible.builtin.slurp` en lugar de `command: cat`"
    `ansible.builtin.slurp` es idempotente y funciona correctamente en modo check. `command: cat` reporta `changed` por defecto y falla en modo check a menos que agregues `changed_when: false` y `check_mode: false`. Para leer contenidos de archivos en tests, siempre prefiere `slurp`.

### El Ciclo de Vida del Test

Cuando ejecutas `molecule test -s integration_webserver`, Molecule ejecuta diez etapas en secuencia:

| Etapa | Que sucede |
|-------|-----------|
| **1. Dependency** | Instala colecciones requeridas desde `requirements.yml` |
| **2. Cleanup** | Ejecuta un playbook de limpieza (si esta definido) |
| **3. Destroy** | Desmonta cualquier entorno de prueba existente |
| **4. Syntax** | Valida la sintaxis del playbook (como `ansible-playbook --syntax-check`) |
| **5. Create** | Crea el entorno de prueba (con driver delegado, esto es un no-op) |
| **6. Prepare** | Ejecuta un playbook de preparacion de prerequisitos (si esta definido) |
| **7. Converge** | Ejecuta el playbook converge -- esto aplica el rol |
| **8. Verify** | Ejecuta el playbook verify -- esto verifica las aserciones |
| **9. Cleanup** | Limpia recursos de prueba |
| **10. Destroy** | Desmonta el entorno de prueba |

Para desarrollo iterativo, no necesitas ejecutar el ciclo completo cada vez. Usa etapas individuales:

```bash
# Ejecutar solo converge (aplicar el rol) — mantiene el entorno
molecule converge -s integration_webserver

# Ejecutar solo verify (verificar aserciones) — reutiliza el entorno existente
molecule verify -s integration_webserver

# Ejecutar el ciclo completo desde estado limpio
molecule test -s integration_webserver

# Listar todos los escenarios disponibles
molecule list

# Destruir el entorno de prueba cuando termines
molecule destroy -s integration_webserver
```

!!! tip "Flujo de trabajo iterativo"
    Durante el desarrollo, usa `molecule converge` y `molecule verify` por separado. Es mucho mas rapido que ejecutar el ciclo completo de `molecule test`, que destruye y recrea el entorno en cada ejecucion. Solo ejecuta `molecule test` cuando quieras una validacion desde cero (por ejemplo, en CI/CD).

## Testing Funcional con pytest-ansible

Molecule prueba el rol como un todo -- aplica el rol a un sistema y verifica los resultados. Pero a veces necesitas tests mas granulares que validen piezas individuales en aislamiento. Ahi es donde entra `pytest-ansible`.

`pytest-ansible` es un plugin de pytest que conecta el framework `pytest` de Python con Ansible. Proporciona fixtures para ejecutar modulos de Ansible directamente desde codigo de test en Python, haciendo posible escribir tests rapidos y aislados para modulos, plugins e internos de roles.

### Estructura de Tests

Los archivos de test de la coleccion estan bajo `tests/`:

```text
tests/
  conftest.py                      # Configuracion de pytest
  unit/
    __init__.py
    test_webserver_defaults.py     # Tests unitarios para el rol webserver
```

#### conftest.py

El archivo `conftest.py` configura el entorno para que `pytest-ansible` pueda encontrar los modulos de la coleccion:

```python
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)

# Apuntar Ansible al directorio plugins/modules
MODULES_PATH = os.path.join(PROJECT_ROOT, "plugins", "modules")
os.environ.setdefault("ANSIBLE_LIBRARY", MODULES_PATH)

# Apuntar Ansible al arbol de symlinks de instalacion editable
COLLECTIONS_PATH = os.path.join(PROJECT_ROOT, "collections")
os.environ.setdefault("ANSIBLE_COLLECTIONS_PATH", COLLECTIONS_PATH)
```

Esto se ejecuta antes de que se recopile cualquier test. Sin esto, Ansible no puede localizar modulos personalizados ni resolver FQCNs, resultando en errores de "module not found".

#### Tests Unitarios

Los tests unitarios validan los archivos YAML del rol sin ejecutar ningun codigo Ansible. Parsean el YAML y verifican propiedades estructurales:

```python
import os
import yaml
import pytest

ROLE_DIR = os.path.join(COLLECTION_ROOT, "roles", "webserver")
DEFAULTS_FILE = os.path.join(ROLE_DIR, "defaults", "main.yml")

@pytest.fixture
def defaults():
    """Carga y devuelve los defaults del rol como diccionario."""
    with open(DEFAULTS_FILE, "r") as fh:
        return yaml.safe_load(fh)

class TestWebserverDefaults:
    def test_all_defaults_prefixed(self, defaults):
        """Cada clave en defaults debe comenzar con 'webserver_'."""
        for key in defaults:
            assert key.startswith("webserver_"), (
                f"La variable '{key}' no tiene el prefijo 'webserver_'"
            )

    def test_port_is_integer(self, defaults):
        """webserver_port debe ser un entero."""
        assert isinstance(defaults["webserver_port"], int)

    def test_service_enabled_is_boolean(self, defaults):
        """webserver_service_enabled debe ser un booleano."""
        assert isinstance(defaults["webserver_service_enabled"], bool)

    def test_document_root_is_absolute_path(self, defaults):
        """webserver_document_root debe ser una ruta absoluta."""
        assert defaults["webserver_document_root"].startswith("/")
```

Estos tests se ejecutan en milisegundos. Validan convenciones que es facil violar accidentalmente -- una nueva variable sin el prefijo del rol, un default que deberia ser entero pero es cadena, una ruta que deberia ser absoluta pero es relativa.

El archivo de test completo en el codigo companero tambien verifica:

- **Variables internas** (`vars/main.yml`) estan todas con prefijo `__webserver_`
- **Argument specs** (`meta/argument_specs.yml`) cubren cada variable en defaults
- **Consistencia de tipos** entre defaults y argument specs

### Ejecutando pytest

Desde la raiz de la coleccion:

```bash
cd ansible/collections/parasoltech/infrastructure
pytest tests/ -v
```

Salida:

```text
tests/unit/test_webserver_defaults.py::TestWebserverDefaults::test_defaults_file_exists PASSED
tests/unit/test_webserver_defaults.py::TestWebserverDefaults::test_all_defaults_prefixed PASSED
tests/unit/test_webserver_defaults.py::TestWebserverDefaults::test_port_is_integer PASSED
tests/unit/test_webserver_defaults.py::TestWebserverDefaults::test_service_enabled_is_boolean PASSED
tests/unit/test_webserver_defaults.py::TestWebserverDefaults::test_document_root_is_absolute_path PASSED
tests/unit/test_webserver_defaults.py::TestWebserverDefaults::test_expected_defaults_present PASSED
tests/unit/test_webserver_defaults.py::TestWebserverInternalVars::test_all_internal_vars_prefixed PASSED
tests/unit/test_webserver_defaults.py::TestWebserverArgumentSpecs::test_defaults_covered_by_specs PASSED
```

Flags utiles de pytest:

| Flag | Proposito |
|------|-----------|
| `-v` | Verbose -- muestra cada nombre de test y resultado |
| `-s` | Sin captura -- muestra sentencias print y salida de debug |
| `-x` | Detener en el primer fallo |
| `--tb=short` | Tracebacks cortos para salida mas limpia |
| `-k "patron"` | Ejecutar solo tests que coincidan con el patron |

## Orquestacion de Tests con tox-ansible

Ahora tienes tres herramientas de testing: `ansible-lint` para analisis estatico, `pytest` para tests unitarios y Molecule para tests de integracion. Ejecutarlos por separado funciona, pero es tedioso -- especialmente cuando necesitas probar contra multiples versiones de Python y Ansible.

`tox-ansible` resuelve esto. Es un plugin de tox (incluido en `ansible-dev-tools`) que escanea la estructura de tu coleccion y **genera automaticamente entornos de test** para linting, tests unitarios, tests de sanity y tests de integracion. No se necesitan definiciones manuales de entornos.

### Configuracion

El archivo de configuracion es `tox-ansible.ini` (no `tox.ini` -- esto mantiene tox-ansible separado de cualquier configuracion estandar de tox):

```ini
[ansible]
skip =
    py3.7
    py3.8
    py3.9
    py3.10
    py3.11
    2.9
    2.10
    2.11
    2.12
    2.13
    2.14
    2.15
    2.16
    2.17
    devel
    milestone
```

Esa es toda la configuracion. La lista `skip` excluye versiones de Python y Ansible que no estan disponibles en tu entorno. Todo lo demas es convencion sobre configuracion -- el plugin descubre que testear escaneando la estructura de la coleccion.

### Auto-descubrimiento

El plugin escanea la coleccion y genera entornos de test basado en lo que encuentra:

```bash
cd ansible/collections/parasoltech/infrastructure
tox --ansible -c tox-ansible.ini list
```

Salida:

```text
default environments:
galaxy                       -> Build and validate collection artifact
integration-py3.12-2.19      -> Integration tests (Molecule scenarios)
sanity-py3.12-2.19           -> Sanity tests (ansible-test sanity)
unit-py3.12-2.19             -> Unit tests (pytest)
```

Cada nombre de entorno codifica tres piezas de informacion:

- **Tipo de test** -- `sanity`, `unit`, `integration` o `galaxy`
- **Version de Python** -- `py3.12`, `py3.13`, etc.
- **Version de Ansible** -- `2.19`, `2.20`, etc.

El plugin los encuentra buscando:

| Tipo de test | El plugin busca |
|--------------|-----------------|
| **sanity** | Cualquier estructura de coleccion (`galaxy.yml`) |
| **unit** | Directorio `tests/unit/` con archivos de test Python |
| **integration** | Directorio `extensions/molecule/` con escenarios |
| **galaxy** | `galaxy.yml` en la raiz de la coleccion |

### Ejecutando Tests

Ejecutar todos los tests:

```bash
tox --ansible -c tox-ansible.ini
```

Ejecutar tipos de test especificos:

```bash
# Solo tests de sanity
tox --ansible -c tox-ansible.ini -e sanity-py3.12-2.19

# Solo tests unitarios
tox --ansible -c tox-ansible.ini -e unit-py3.12-2.19

# Solo tests de integracion
tox --ansible -c tox-ansible.ini -e integration-py3.12-2.19

# Construir y validar el artefacto de la coleccion
tox --ansible -c tox-ansible.ini -e galaxy
```

Para cada entorno, tox:

1. Crea un entorno virtual limpio
2. Instala las versiones requeridas de Python y Ansible
3. Instala dependencias de test
4. Ejecuta el comando de test apropiado
5. Reporta resultados

Este es el mismo flujo de trabajo que se ejecuta en pipelines CI/CD. Si pasa localmente, pasara en CI.

!!! note "Siempre pasa `--ansible` y `-c tox-ansible.ini`"
    Sin `--ansible`, el plugin no se activa y ninguno de los entornos auto-generados aparecera. Sin `-c tox-ansible.ini`, tox busca `tox.ini` y no encontrara la lista de skip.

### La Interfaz Unificada

El poder de `tox-ansible` es la interfaz unificada. En lugar de recordar:

```bash
ansible-lint                                    # Lint
pytest tests/                                   # Tests unitarios
molecule test -s integration_webserver          # Tests de integracion
ansible-galaxy collection build                 # Construir artefacto
```

Ejecutas:

```bash
tox --ansible -c tox-ansible.ini
```

Un comando. Todos los tipos de test. Entornos consistentes. Esto es lo que la CoP configura como el chequeo requerido de CI/CD para cada pull request.

## Ejercicios

### Ejercicio 1: Ejecutar ansible-lint

Navega a la coleccion y ejecuta el linter:

```bash
cd ansible/collections/parasoltech/infrastructure
ansible-lint
```

Si hay violaciones, examina la salida cuidadosamente. Cada violacion incluye el archivo, numero de linea, ID de regla y descripcion. Intenta corregir los problemas manualmente, luego ejecuta `ansible-lint --fix` para ver que puede manejar la auto-correccion.

### Ejercicio 2: Escribir una Nueva Asercion

Abre `extensions/molecule/integration_webserver/verify.yml` y agrega una nueva asercion que verifique que el directorio document root tiene los permisos correctos (modo `0755`). Usa la variable `__verify_docroot_stat` que ya esta registrada.

??? example "Solucion"
    ```yaml
    - name: Assert document root has correct permissions
      ansible.builtin.assert:
        that:
          - __verify_docroot_stat.stat.mode == '0755'
        fail_msg: >-
          Los permisos del document root son
          {{ __verify_docroot_stat.stat.mode }}, se esperaba 0755.
        success_msg: >-
          El document root tiene los permisos correctos (0755).
    ```

### Ejercicio 3: Agregar un Test Unitario

Abre `tests/unit/test_webserver_defaults.py` y agrega un test que verifique que `webserver_port` tiene un valor por defecto dentro de un rango de puertos valido (1-65535).

??? example "Solucion"
    ```python
    def test_port_in_valid_range(self, defaults):
        """webserver_port debe estar entre 1 y 65535."""
        port = defaults["webserver_port"]
        assert 1 <= port <= 65535, (
            f"webserver_port ({port}) esta fuera del rango valido 1-65535"
        )
    ```

### Ejercicio 4: Ejecutar el Ciclo de Vida Completo del Test

Ejecuta el ciclo de vida completo de Molecule para el rol webserver:

```bash
cd ansible/collections/parasoltech/infrastructure/extensions
molecule test -s integration_webserver
```

Observa la salida e identifica cada etapa del ciclo de vida. Si alguna etapa falla, lee el mensaje de error y corrige el problema.

### Ejercicio 5: Explorar tox-ansible

Lista los entornos de test auto-descubiertos:

```bash
cd ansible/collections/parasoltech/infrastructure
tox --ansible -c tox-ansible.ini list
```

Ejecuta los tests unitarios a traves de tox y compara la salida con ejecutar `pytest` directamente. Observa como tox crea un entorno virtual aislado para la ejecucion del test.

## Resumen

En este modulo:

- Aprendiste la piramide de testing de Ansible -- lint, unit e integracion forman capas de comprobacion creciente y costo
- Configuraste `ansible-lint` con un perfil de produccion, aprendiste a leer su salida y usaste auto-correccion para resolver violaciones automaticamente
- Creaste un escenario de Molecule para el rol webserver con un driver delegado, un playbook converge que aplica el rol y un playbook verify con verificaciones basadas en aserciones
- Entendiste el ciclo de vida de diez etapas de Molecule y cuando usar etapas individuales (`converge`, `verify`) versus el ciclo de vida completo (`test`)
- Escribiste tests unitarios `pytest-ansible` que validan defaults del rol, variables internas y consistencia de argument specs sin ejecutar ningun codigo Ansible
- Configuraste `tox-ansible` para auto-descubrir y orquestar todos los tipos de test a traves de un unico comando con convencion sobre configuracion

La CoP en Parasol Tech ahora tiene controles de calidad: `ansible-lint` detecta violaciones de estilo, los tests unitarios detectan problemas estructurales y los tests de integracion de Molecule detectan fallos en tiempo de ejecucion. Cada pull request a la coleccion `parasoltech.infrastructure` pasa por `tox --ansible` antes de poder fusionarse.

## Proximos Pasos

Siguiente: [Modulo 8 -- Empaquetado y Despliegue](8-packaging-and-deployment.md)
