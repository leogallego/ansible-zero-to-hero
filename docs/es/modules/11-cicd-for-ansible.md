# Módulo 11: CI/CD para Contenido Ansible

## Objetivos de Aprendizaje

Al finalizar este módulo serás capaz de:

- Explicar por qué CI/CD para Ansible prueba tu código de automatización, no tu infraestructura, y cómo esto difiere de usar Ansible en pipelines de CI/CD de aplicaciones
- Crear un workflow de GitHub Actions que ejecute `ansible-lint` en cada pull request usando la acción compuesta oficial `ansible/ansible-lint`
- Crear un workflow de GitHub Actions que ejecute tests de integración con Molecule en CI con salida a color y carga de artefactos en caso de fallo
- Configurar `tox-ansible` para producir una matriz de tests compatible con CI usando `--gh-matrix` y ejecutar la suite completa de tests de la colección en un pipeline de GitHub Actions
- Gestionar secretos en CI para contraseñas de Ansible Vault y tokens de Galaxy usando secretos de repositorio de GitHub
- Agregar badges de estado al README de la colección y comprender la protección de ramas como buena práctica para imponer puertas de calidad

## La Historia Hasta Ahora

La CoP ha estado creciendo. Seis equipos ahora contribuyen roles a `parasoltech.infrastructure`, y la colección se ha expandido de un rol a cuatro. El proceso es claro: ejecutar `ansible-lint`, ejecutar `molecule test`, ejecutar `tox --ansible` antes de fusionar. Todos conocen las reglas.

Entonces un merge del viernes por la tarde rompe todo.

Jordan revisa un PR del equipo de networking, examina el código visualmente, pero no ejecuta la suite de tests -- el cambio parece lo suficientemente simple. Para el lunes por la mañana, los despliegues a staging fallan en tres equipos. El culpable: un error tipográfico en un template de Jinja2 que `ansible-lint` habría detectado en segundos.

"El problema no es el proceso," dice Lionel en la reunión de la CoP. "El problema es que el proceso depende de que la gente recuerde. Necesitamos que las máquinas lo impongan."

El equipo acuerda automatizar sus puertas de calidad: cada pull request debe pasar linting, tests de integración y verificaciones de sanidad antes de poder fusionarse. Sin excepciones. Al final de la semana, el repositorio de la colección tiene tres nuevos archivos de workflow en `.github/workflows/`. Una marca verde significa que el cambio es seguro para fusionar. Una X roja significa que no lo es. Nadie necesita recordar ejecutar los tests -- GitHub lo hace por ellos.

## CI/CD para Contenido Ansible vs CI/CD con Ansible

Antes de escribir cualquier workflow, es importante entender qué significa CI/CD en el contexto del contenido Ansible.

Hay dos usos muy diferentes de la frase "CI/CD y Ansible":

| | CI/CD *para* Ansible | CI/CD *con* Ansible |
|---|---|---|
| **Qué significa** | Probar tu código de automatización | Usar Ansible para desplegar aplicaciones |
| **Qué se ejecuta** | ansible-lint, molecule, ansible-test, tox-ansible | ansible-playbook contra infraestructura real |
| **Dónde se ejecuta** | Runner efímero de CI (GitHub Actions, GitLab CI) | AAP Controller, AWX, o SSH directo |
| **Qué valida** | Calidad del código, sintaxis, comportamiento de roles | Estado de la infraestructura |
| **Se cubre en** | Este módulo | Módulo 12 (AAP) |

Este módulo cubre la primera columna: probar código de automatización en un runner efímero. Nada toca producción. El runner de CI aplica tu rol a localhost, verifica los resultados y se destruye. El Módulo 12 cubre la segunda columna -- usar Ansible Automation Platform para ejecutar automatización contra infraestructura real con RBAC, registros de auditoría e integración con webhooks.

!!! info "CI para Ansible prueba tu código, no tu infraestructura"
    Esta es la distinción más importante de este módulo. Si te llevas una sola cosa, que sea esta: CI para contenido Ansible valida tu código de automatización en un runner desechable. Nunca toca la infraestructura de producción.

### La Pirámide de Tests en CI

La pirámide de tests del Módulo 9 se mapea directamente a las etapas de CI:

```text
         ┌─────────────┐
         │ Integración  │  Molecule      -- minutos
         │  (Molecule)  │
        ┌┴─────────────┴┐
        │   Tests Unit   │  pytest        -- segundos
        │  (pytest)      │
       ┌┴───────────────┴┐
       │  Tests Sanidad   │  ansible-test  -- segundos
       │  (ansible-test)  │
      ┌┴─────────────────┴┐
      │   Lint             │  ansible-lint  -- segundos
      │   (ansible-lint)   │
      └───────────────────┘
```

Se ejecuta de abajo hacia arriba: lint primero (rápido, barato), integración al final (lento, exhaustivo). Falla rápido en la capa más barata. Cada herramienta aquí es la misma que configuraste en el Módulo 9 -- la única diferencia es que ahora una máquina las ejecuta en cada pull request en lugar de depender de que un desarrollador recuerde hacerlo.

### Fundamentos de GitHub Actions

GitHub Actions es la plataforma de CI/CD integrada en GitHub. Los conceptos clave:

| Concepto | Descripción |
|----------|-------------|
| **Workflow** | Un archivo YAML en `.github/workflows/` que define un proceso automatizado |
| **Trigger** | El evento que inicia el workflow (`push`, `pull_request`, `schedule`) |
| **Job** | Un conjunto de pasos que se ejecutan en el mismo runner |
| **Step** | Un comando o acción individual dentro de un job |
| **Runner** | La máquina virtual que ejecuta el job (`ubuntu-24.04`) |
| **Action** | Una unidad de trabajo reutilizable (`actions/checkout@v4`, `ansible/ansible-lint@v26`) |
| **Secret** | Un valor cifrado almacenado en el repositorio, inyectado en tiempo de ejecución |

Los workflows se basan en eventos. Cuando un desarrollador abre un pull request, GitHub detecta que el evento coincide con un trigger de workflow y arranca un runner nuevo para ejecutar los jobs definidos.

## Linting en CI con ansible-lint

La primera y más rápida puerta de calidad es el linting. La acción oficial de GitHub `ansible/ansible-lint` envuelve la herramienta `ansible-lint` en una acción compuesta que maneja la configuración de Python, la instalación y la ejecución en un solo paso.

### El Archivo de Workflow

Crea `.github/workflows/ansible-lint.yml`:

```yaml
---
name: Ansible Lint

on:
  push:
    branches: [main]
    paths:
      - 'ansible/**'
  pull_request:
    branches: [main]
    paths:
      - 'ansible/**'

jobs:
  lint:
    name: Ansible Lint
    runs-on: ubuntu-24.04
    steps:
      - name: Check out code
        uses: actions/checkout@v4

      - name: Run ansible-lint
        uses: ansible/ansible-lint@v26
        with:
          working_directory: ansible/collections/parasoltech/infrastructure
```

!!! tip "Fijación de versiones"
    La etiqueta `@v26` es una versión mayor continua -- siempre apunta a la última versión `v26.x.x`. Esto es conveniente para un curso, pero para workflows de producción debes fijar una versión específica (por ejemplo, `@v26.6.0`) para evitar comportamientos inesperados cuando la acción se actualice.

Recorramos cada sección:

**Triggers (`on:`)**

- `push: branches: [main]` -- se ejecuta cuando se hace push de código directamente a la rama `main`
- `pull_request: branches: [main]` -- se ejecuta cuando se abre o actualiza un PR contra `main`

Juntos, aseguran que tanto el PR como el resultado del merge sean validados.

**Runner (`runs-on: ubuntu-24.04`)**

El job se ejecuta en una máquina virtual Ubuntu 24.04 LTS. Siempre especifica la versión explícitamente -- `ubuntu-latest` es un objetivo móvil que puede cambiar sin aviso.

**Steps**

1. **Checkout**: `actions/checkout@v4` clona el repositorio en el runner
2. **Lint**: `ansible/ansible-lint@v26` instala y ejecuta `ansible-lint`. La entrada `working_directory` le indica dónde encontrar la colección -- esencial para layouts de monorepo donde el contenido Ansible no está en la raíz del repositorio

La acción de `ansible-lint` lee el archivo de configuración `.ansible-lint` del Módulo 9 automáticamente. No se necesita configuración adicional.

### Instalación de Dependencias de Colección

Si tu colección depende de otras colecciones (listadas en `requirements.yml`), la acción las instala antes del linting. La acción `ansible/ansible-lint` maneja esto de forma transparente a través de la resolución de dependencias integrada de `ansible-lint`.

## Tests de Integración con Molecule en CI

El linting detecta problemas estáticos. Molecule detecta los dinámicos -- problemas que solo aparecen cuando realmente aplicas un rol. En CI, Molecule se ejecuta sin terminal interactivo, sin Docker-in-Docker y sin nadie observando la salida.

### El Archivo de Workflow

Crea `.github/workflows/molecule.yml`:

```yaml
---
name: Molecule Tests

on:
  pull_request:
    branches: [main]
    paths:
      - 'ansible/**'
      - '.github/workflows/molecule.yml'

jobs:
  molecule:
    name: Molecule - ${{ matrix.scenario }}
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: ansible/collections/parasoltech/infrastructure
    strategy:
      fail-fast: false
      matrix:
        scenario:
          - integration_webserver
    env:
      PY_COLORS: '1'
      ANSIBLE_FORCE_COLOR: 'true'
    steps:
      - name: Check out code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install ansible-dev-tools

      - name: Run Molecule tests
        run: molecule test -s ${{ matrix.scenario }}

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: molecule-logs-${{ matrix.scenario }}
          path: ansible/collections/parasoltech/infrastructure/extensions/molecule/${{ matrix.scenario }}/.molecule/
```

Este workflow introduce varios conceptos nuevos:

**Filtrado por rutas (`paths:`)**

La clave `paths` limita el workflow a cambios dentro de `ansible/` o el archivo de workflow en sí. Un cambio solo de documentación no dispara una ejecución de Molecule, ahorrando minutos de CI.

**Estrategia de matriz (`strategy.matrix`)**

La matriz ejecuta el job una vez por escenario. Con un escenario (`integration_webserver`), hay un job. Cuando la CoP agregue un segundo rol con su propio escenario Molecule, agregan una línea a la matriz y CI se encarga del resto.

Configurar `fail-fast: false` asegura que todos los escenarios se ejecuten hasta completarse aunque uno falle. De esta forma ves el panorama completo, no solo el primer fallo.

**Salida a color**

Los runners de CI no tienen terminal, por lo que Ansible y Python desactivan la salida a color por defecto. Configurar `PY_COLORS: '1'` y `ANSIBLE_FORCE_COLOR: 'true'` como variables de entorno restaura el color en los logs de CI, haciendo los fallos mucho más fáciles de leer.

**Carga de artefactos en caso de fallo**

La condición `if: failure()` en el paso de carga significa que solo se ejecuta cuando el test falla. Sube el directorio `.molecule/` de Molecule, que contiene los logs de ansible, como un artefacto descargable. Cuando un test falla a las 2 AM, la información de depuración está esperando en la pestaña de Actions a la mañana siguiente.

!!! tip "DIY vs acción oficial"
    A diferencia de `ansible-lint`, no existe una acción oficial de Molecule. Este workflow toma el enfoque DIY: configurar Python, instalar `ansible-dev-tools` (que incluye Molecule) y ejecutar `molecule test`. Esto te da control total sobre la versión de Python, dependencias y configuración de Molecule.

## Testing de Colecciones con tox-ansible

`tox-ansible` orquesta todos los tipos de tests -- lint, sanidad, unitarios e integración -- a través de una interfaz única. Su flag `--gh-matrix` produce salida JSON que GitHub Actions puede consumir para crear una matriz de tests dinámica.

### El Patrón de Dos Jobs

El workflow usa dos jobs:

1. **`matrix-gen`**: Ejecuta `tox --ansible --gh-matrix` para descubrir todos los entornos de test y produce el JSON como salida
2. **`test`**: Lee el JSON y ejecuta cada entorno de test en paralelo

Este patrón significa que nunca actualizas manualmente la matriz de CI. Agrega un nuevo escenario de Molecule o un nuevo archivo de test, y `tox-ansible` lo descubre automáticamente en la siguiente ejecución.

### El Archivo de Workflow

Crea `.github/workflows/collection-test.yml`:

```yaml
---
name: Collection Tests

on:
  push:
    branches: [main]
    paths:
      - 'ansible/**'
  pull_request:
    branches: [main]
    paths:
      - 'ansible/**'

jobs:
  matrix-gen:
    name: Generate test matrix
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: ansible/collections/parasoltech/infrastructure
    outputs:
      envlist: ${{ steps.generate-matrix.outputs.envlist }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install tox tox-ansible
      - name: Generate matrix
        id: generate-matrix
        run: python -m tox --ansible --gh-matrix --conf tox-ansible.ini

  test:
    name: ${{ matrix.entry.name }}
    needs: matrix-gen
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: ansible/collections/parasoltech/infrastructure
    strategy:
      fail-fast: false
      matrix:
        entry: ${{ fromJSON(needs.matrix-gen.outputs.envlist) }}
    env:
      PY_COLORS: '1'
      ANSIBLE_FORCE_COLOR: 'true'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install tox tox-ansible
      - run: tox --ansible -c tox-ansible.ini -e ${{ matrix.entry.name }}

  all_green:
    if: always()
    needs: [test]
    runs-on: ubuntu-24.04
    steps:
      - uses: re-actors/alls-green@release/v1
        with:
          jobs: ${{ toJSON(needs) }}
```

Desglosemos las partes clave:

**Generación de la matriz**

El job `matrix-gen` ejecuta `tox --ansible --gh-matrix --conf tox-ansible.ini` y captura la salida. El flag `--gh-matrix` le indica a `tox-ansible` que escriba un array JSON en `$GITHUB_OUTPUT` bajo la clave `envlist`. Cada entrada en el array tiene un campo `name` que corresponde a un entorno de tox como `sanity-py3.12-2.19` o `unit-py3.12-2.19`.

La sección `outputs` expone este JSON a los jobs posteriores a través de `needs.matrix-gen.outputs.envlist`.

**Consumo de la matriz dinámica**

El job `test` usa `fromJSON(needs.matrix-gen.outputs.envlist)` para parsear el array JSON en una matriz de GitHub Actions. Cada entrada genera un job paralelo separado que ejecuta el entorno de tox correspondiente.

Este es el mismo `tox --ansible` que usaste localmente en el Módulo 9. Mismo archivo de configuración, mismos comandos, mismos resultados -- solo que ejecutándose en un runner en la nube en lugar de tu portátil.

**El job de agregación `all_green`**

Con una matriz dinámica que puede producir 4, 6 o 12 jobs de test, necesitas una única verificación de estado que reporte el resultado general. El job `all_green` depende de todos los jobs de la matriz `test` y usa la acción `re-actors/alls-green` para verificar que todos hayan pasado.

!!! tip "El patrón `all_green`: una puerta para gobernarlos a todos"
    Con una matriz de 6 entornos de test, agrega un job `all_green` que dependa de todos los jobs de la matriz. Configura `all_green` como la única verificación requerida en la protección de ramas. Se adapta automáticamente cuando agregas o eliminas entornos -- sin necesidad de actualizar las reglas de protección de ramas cada vez que cambia la matriz.

El `if: always()` es crítico. Sin él, el job `all_green` se omite cuando cualquier job anterior falla -- que es exactamente cuando necesitas que reporte un fallo.

### Workflows Reutilizables

El repositorio `ansible/ansible-content-actions` proporciona workflows reutilizables de calidad producción para tareas comunes de CI de contenido Ansible. Son mantenidos por el equipo de Ansible y cubren validación de changelog, automatización de releases y más.

Por ejemplo, un workflow de validación de changelog:

```yaml
---
name: Changelog Check

on:
  pull_request:
    branches: [main]

jobs:
  changelog:
    uses: ansible/ansible-content-actions/.github/workflows/changelog.yaml@main
```

Una línea en la sección `jobs` reemplaza una definición completa de workflow. La clave `uses` apunta a un archivo de workflow en otro repositorio, y GitHub Actions se encarga del resto.

!!! tip "Si pasa localmente, debe pasar en CI"
    El objetivo principal de `tox-ansible` es garantizar esto. Si un test pasa localmente pero falla en CI, algo está mal con el aislamiento de tu entorno -- y eso es un bug que vale la pena corregir.

## Secretos y Seguridad en CI

Algunas tareas de CI necesitan valores sensibles: contraseñas de Vault para variables cifradas, tokens de Galaxy para publicar colecciones, credenciales de nube para tests de integración. Estos nunca deben aparecer en el código.

### Secretos de Repositorio en GitHub

GitHub almacena los secretos cifrados y los inyecta en los workflows en tiempo de ejecución. Estos son:

- **Cifrados en reposo**: GitHub no puede leerlos después de guardarlos
- **Enmascarados en logs**: Si un valor de secreto aparece en stdout, GitHub lo reemplaza con `***`
- **Con alcance al repositorio**: Cada repositorio tiene sus propios secretos
- **No disponibles para forks**: Los pull requests de repositorios forkeados no pueden acceder a los secretos, previniendo la exfiltración

Para agregar un secreto, ve a **Settings → Secrets and variables → Actions → New repository secret**.

### Contraseña de Vault en CI

Cuando los escenarios de Molecule usan variables cifradas, el workflow de Molecule necesita la contraseña de Vault. El patrón:

1. Almacena la contraseña de Vault como un secreto de GitHub llamado `VAULT_PASSWORD`
2. En el workflow, escribe el secreto en un archivo temporal
3. Apunta Molecule al archivo a través de una variable de entorno
4. El archivo se limpia automáticamente cuando el runner se destruye

Agrega estos pasos al workflow de Molecule antes del paso `Run Molecule tests`:

```yaml
      - name: Write vault password file
        run: echo "$VAULT_PASSWORD" > .vault-password
        env:
          VAULT_PASSWORD: ${{ secrets.VAULT_PASSWORD }}

      - name: Run Molecule tests
        run: molecule test -s ${{ matrix.scenario }}
        env:
          ANSIBLE_VAULT_PASSWORD_FILE: .vault-password
```

!!! warning "Los secretos nunca pertenecen al código"
    Cada plataforma de CI proporciona un mecanismo de secretos. Almacena el secreto en la plataforma, referéncialo por nombre en el workflow, y la plataforma lo inyecta en tiempo de ejecución. Los secretos se enmascaran en los logs y no están disponibles para PRs de forks.

### Tokens de Galaxy

Publicar colecciones en Galaxy o Automation Hub requiere un token de API. Almacénalo como un secreto y referéncialo en los workflows:

```yaml
      - name: Publish collection
        run: >-
          ansible-galaxy collection publish
          parasoltech-infrastructure-*.tar.gz
          --server https://galaxy.ansible.com/
        env:
          ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN: ${{ secrets.GALAXY_TOKEN }}
```

### Seguridad de Forks

Cuando alguien forkea tu repositorio y abre un PR, el workflow se ejecuta sobre el código del fork. GitHub deliberadamente no inyecta los secretos del repositorio en estas ejecuciones. Esta es una característica de seguridad: un fork malicioso podría agregar un paso que imprima `${{ secrets.GALAXY_TOKEN }}` en los logs.

Diseña tus workflows de modo que los tests que no necesitan secretos (linting, tests de sanidad, tests unitarios) pasen sin ellos, y los tests que requieren secretos (publicación, tests de integración cifrados) se omitan o se controlen con una condición `if: github.event.pull_request.head.repo.full_name == github.repository`.

## Badges de Estado y Buenas Prácticas

### Badges de Estado

Los badges de estado son pequeñas imágenes que muestran el estado actual de un workflow: pasando o fallando. Agrégalos al README de la colección para dar a los contribuidores visibilidad instantánea sobre la salud del CI.

El formato de URL del badge es:

```text
![Nombre del Workflow](https://github.com/OWNER/REPO/actions/workflows/ARCHIVO_WORKFLOW/badge.svg)
```

Para los tres workflows de este módulo:

```markdown
![Ansible Lint](https://github.com/OWNER/REPO/actions/workflows/ansible-lint.yml/badge.svg)
![Molecule Tests](https://github.com/OWNER/REPO/actions/workflows/molecule.yml/badge.svg)
![Collection Tests](https://github.com/OWNER/REPO/actions/workflows/collection-test.yml/badge.svg)
```

Reemplaza `OWNER/REPO` con la ruta de tu repositorio en GitHub.

### Protección de Ramas

Las reglas de protección de ramas imponen puertas de calidad a nivel del repositorio. Cuando están configuradas, los pull requests no pueden fusionarse hasta que todas las verificaciones de estado requeridas pasen, sin importar quién esté fusionando.

Las configuraciones clave para un repositorio de contenido Ansible:

- **Requerir que las verificaciones de estado pasen antes de fusionar**: Selecciona el job `all_green` del workflow de tests de colección. Esta única verificación cubre todos los entornos de test.
- **Requerir revisiones de pull request**: Al menos un miembro del equipo debe aprobar antes de fusionar.
- **No permitir eludir las configuraciones anteriores**: Incluso los administradores del repositorio deben seguir las reglas.
- **Restringir force pushes**: Prevenir la reescritura del historial en `main`.

La protección de ramas se configura en **Settings → Branches → Branch protection rules** en el repositorio de GitHub. Las configuraciones específicas dependen del flujo de trabajo de tu equipo y el modelo de acceso -- comienza requiriendo la verificación de estado `all_green` e itera desde ahí.

!!! note "La protección de ramas requiere acceso de administrador"
    Configurar reglas de protección de ramas requiere permisos de administrador del repositorio y varía según el flujo de trabajo del equipo. Las configuraciones anteriores son buenas prácticas -- aplícalas según las necesidades de tu organización.

## Otras Plataformas de CI

Los workflows de este módulo usan GitHub Actions, pero las herramientas son las mismas en todas partes. Solo cambia el formato de configuración de CI.

### GitLab CI

GitLab CI usa `.gitlab-ci.yml` en lugar de `.github/workflows/`. Las mismas herramientas se ejecutan de la misma manera -- solo cambia el formato de configuración:

```yaml
---
stages:
  - lint
  - test

ansible-lint:
  stage: lint
  image: ghcr.io/ansible/community-ansible-dev-tools:latest
  script:
    - ansible-lint

collection-tests:
  stage: test
  image: ghcr.io/ansible/community-ansible-dev-tools:latest
  script:
    - tox --ansible -c tox-ansible.ini
```

### Jenkins

Para Jenkins, usa la imagen de contenedor `ghcr.io/ansible/community-ansible-dev-tools` como agente de build -- incluye `ansible-lint`, Molecule, `tox-ansible` y todas las demás herramientas de este módulo. Los mismos comandos funcionan de manera idéntica dentro de ella.

El punto clave: aprende las herramientas una vez, aplícalas en todas partes. Solo cambia el formato de configuración de CI.

## Ejercicios

### Ejercicio 1: Crear un Workflow de ansible-lint

Usando solo los conceptos de la sección "Linting en CI con ansible-lint", crea `.github/workflows/ansible-lint.yml` desde cero. Tu workflow debe:

- Dispararse en pushes y pull requests a `main`
- Usar un runner `ubuntu-24.04`
- Hacer checkout del código y ejecutar `ansible-lint` usando la acción oficial
- Apuntar `ansible-lint` al directorio de trabajo de la colección

Después de escribir tu versión, compárala con el workflow de referencia en la sección anterior. ¿Omitiste algo? ¿Agregaste algo innecesario?

### Ejercicio 2: Crear un Workflow de Tests con Molecule

Crea `.github/workflows/molecule.yml` con filtrado por rutas, una estrategia de matriz para escenarios, salida a color y carga de artefactos en caso de fallo.

Usa el workflow de la sección "Tests de Integración con Molecule en CI" anterior. Después de crear el archivo, abre un pull request que introduzca un error deliberado en el rol webserver (por ejemplo, un error tipográfico en un nombre de variable en un template). Observa el fallo del CI. Corrige el error, haz push de nuevo y observa que el CI pasa.

### Ejercicio 3: Crear un Workflow de Tests de Colección con tox-ansible

Crea `.github/workflows/collection-test.yml` con el patrón de dos jobs: generación de la matriz y ejecución paralela de tests.

Usa el workflow de la sección "Testing de Colecciones con tox-ansible" anterior. Antes de hacer push, ejecuta la generación de la matriz localmente para ver la salida JSON:

```bash
cd ansible/collections/parasoltech/infrastructure
tox --ansible --gh-matrix -c tox-ansible.ini
```

Examina el JSON. Haz push del workflow y observa la matriz dinámica en la pestaña de GitHub Actions.

### Ejercicio 4: Configurar Secretos y Badges de Estado

1. Navega a tu repositorio en GitHub y agrega un secreto llamado `VAULT_PASSWORD` en **Settings → Secrets and variables → Actions**
2. Agrega el paso de contraseña de vault de la sección "Contraseña de Vault en CI" a tu workflow de Molecule, antes del paso `Run Molecule tests`
3. Agrega badges de estado para los tres workflows al README de la colección en `ansible/collections/parasoltech/infrastructure/README.md`:

    ```markdown
    ![Ansible Lint](https://github.com/OWNER/REPO/actions/workflows/ansible-lint.yml/badge.svg)
    ![Molecule Tests](https://github.com/OWNER/REPO/actions/workflows/molecule.yml/badge.svg)
    ![Collection Tests](https://github.com/OWNER/REPO/actions/workflows/collection-test.yml/badge.svg)
    ```

4. Haz push y verifica que los badges se rendericen correctamente en el README

### Ejercicio 5: Workflows Reutilizables (Bonus)

Crea `.github/workflows/changelog.yml` que llame al workflow reutilizable de `ansible/ansible-content-actions` para validación de changelog:

```yaml
---
name: Changelog Check

on:
  pull_request:
    branches: [main]

jobs:
  changelog:
    uses: ansible/ansible-content-actions/.github/workflows/changelog.yaml@main
```

Explora el [repositorio ansible-content-actions](https://github.com/ansible/ansible-content-actions) para ver qué otros workflows reutilizables están disponibles. Considera cuáles beneficiarían a la colección de la CoP.

## Resumen

En este módulo:

- Comprendiste la distinción crítica entre CI/CD *para* contenido Ansible (probar tu código de automatización en runners efímeros) y CI/CD *con* Ansible (ejecutar automatización contra infraestructura real con AAP)
- Creaste un workflow de `ansible-lint` usando la acción compuesta oficial `ansible/ansible-lint@v26`, con triggers en push y pull request
- Construiste un workflow de tests de Molecule con filtrado por rutas, estrategia de matriz para múltiples escenarios, salida a color mediante variables de entorno y carga de artefactos en caso de fallo para depuración post-mortem
- Configuraste `tox-ansible` con `--gh-matrix` para generar dinámicamente una matriz de tests en CI, y usaste el patrón de dos jobs (generación de la matriz → ejecución paralela) con un job de agregación `all_green`
- Aprendiste a gestionar secretos en CI -- contraseñas de Vault escritas en archivos temporales, tokens de Galaxy inyectados como variables de entorno, y las implicaciones de seguridad de PRs desde forks
- Agregaste badges de estado al README de la colección y comprendiste la protección de ramas como buena práctica para imponer puertas de calidad a nivel del repositorio

La CoP en Parasol Tech ahora tiene puertas de calidad automatizadas en cada pull request. El linting se ejecuta en segundos. Los tests de integración con Molecule y los tests de sanidad/unitarios con tox-ansible se ejecutan en paralelo. Un job `all_green` agrega los resultados en una señal única de pasa/falla. Nadie necesita recordar ejecutar los tests -- el pipeline de CI lo impone.

## Próximos Pasos

Siguiente: [Módulo 12 -- Escalando con AAP](12-scaling-with-aap.md)
