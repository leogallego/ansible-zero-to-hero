# Module 7: Testing Your Automation

## Learning Objectives

By the end of this module you will be able to:

- Run `ansible-lint` for static analysis and configure auto-fix rules
- Write and run Molecule integration tests with assertion-based verification
- Create functional tests with `pytest-ansible`
- Orchestrate test matrices with `tox-ansible`
- Describe the Ansible test pyramid (lint → unit → integration)

## The Story So Far

The CoP at Parasol Tech has its first collection -- `parasoltech.infrastructure` with a `webserver` role that installs packages, deploys configuration from templates, and manages the service lifecycle. Teams are starting to adopt it.

Then something breaks. The monitoring team overrides `webserver_port` with a string instead of an integer, and the template renders garbage. Jordan catches it during a code review, but it was already deployed to staging.

"We got lucky," Lionel says. "Next time it might be production."

The CoP holds an emergency meeting. The outcome: **no untested automation goes to production.** Every role needs automated tests. Every pull request must pass linting, unit tests, and integration tests before it can be merged. The team agrees on a testing strategy using four tools from the `ansible-dev-tools` suite: `ansible-lint`, Molecule, `pytest-ansible`, and `tox-ansible`.

## The Ansible Test Pyramid

Testing is not one thing -- it is a spectrum of checks at different levels of abstraction and cost. The Ansible test pyramid organizes these levels from cheapest and fastest at the bottom to most thorough and slowest at the top:

```text
          /\
         /  \
        / In \         Integration tests (Molecule)
       / tegr \        Apply role to real hosts, verify postconditions
      / ation  \
     /----------\
    /   Unit     \     Unit tests (pytest-ansible)
   /   Tests      \    Validate individual components in isolation
  /----------------\
 /  Static Analysis  \ Linting (ansible-lint)
/  (ansible-lint)     \Fast, cheap, catches style and syntax errors
/______________________\
```

| Level | Tool | What it catches | Speed |
|-------|------|-----------------|-------|
| **Lint** | `ansible-lint` | Syntax errors, deprecated modules, naming violations, missing FQCNs | Seconds |
| **Unit** | `pytest-ansible` | Incorrect defaults, broken argument specs, module logic errors | Seconds |
| **Integration** | Molecule | Role failures on real systems, missing templates, service misconfigurations | Minutes |

The principle is simple: catch as much as possible at the lower levels, because those tests are fast, cheap, and run on every save. Reserve integration tests for things that can only be validated by actually applying the role.

## Static Analysis with ansible-lint

`ansible-lint` checks your Ansible content against a comprehensive set of rules -- everything from YAML formatting to deprecated module usage to naming conventions. It is the first line of defense and catches the most common mistakes before you even run a playbook.

### Configuration

The collection includes an `.ansible-lint` file at its root:

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

Key settings:

- **`profile: production`** -- Uses the strictest built-in rule set. Other options are `min`, `basic`, `moderate`, `safety`, and `shared`, each adding more rules.
- **`strict: true`** -- Warnings are treated as errors. If `ansible-lint` finds anything, the exit code is non-zero.
- **`enable_list`** -- Explicitly enables rule categories for auto-fix support.
- **`skip_list`** -- Suppresses specific rules that do not apply (in this case, the `galaxy[version-incorrect]` rule that flags versions not published to Galaxy).

### Running ansible-lint

From the collection root:

```bash
cd ansible/collections/parasoltech/infrastructure
ansible-lint
```

If there are no violations, the output is clean. If there are problems, `ansible-lint` shows the file, line number, rule ID, and a description:

```text
roles/webserver/tasks/main.yml:5: fqcn[action-core]
  Use FQCN for builtin module actions.

roles/webserver/handlers/main.yml:8: name[casing]
  All names should start with an uppercase letter.
```

### Auto-fix

Many rules support automatic fixing. Instead of manually editing every file, run:

```bash
ansible-lint --fix
```

`ansible-lint` rewrites the files in place, fixing what it can. Common auto-fixes include:

- Replacing short module names with FQCNs (`copy` becomes `ansible.builtin.copy`)
- Converting `yes`/`no` to `true`/`false`
- Fixing YAML formatting (trailing spaces, indentation)

After auto-fix, review the changes with `git diff` before committing. Not every auto-fix is perfect -- always verify.

!!! tip "IDE integration"
    `ansible-lint` integrates with VS Code through the Ansible extension. Violations appear as squiggly underlines in the editor, and auto-fix is available through the quick-fix menu (Ctrl+.). This gives you instant feedback as you write.

### Rule Categories

`ansible-lint` organizes rules into categories:

| Category | Examples |
|----------|----------|
| **fqcn** | Use FQCNs for all modules |
| **name** | Task names must start with uppercase, use imperative form |
| **args** | Required arguments missing, deprecated arguments used |
| **yaml** | Indentation errors, trailing spaces, truthy values |
| **no-changed-when** | `command`/`shell` tasks without `changed_when` |
| **risky-file-permissions** | File tasks without explicit `mode` |
| **role-name** | Role names with dashes or invalid characters |
| **galaxy** | Collection metadata issues |

Each category maps to rules you have already learned in this course. `ansible-lint` enforces them automatically instead of relying on code review.

## Integration Testing with Molecule

While `ansible-lint` catches static problems, Molecule catches dynamic ones -- problems that only appear when you actually apply a role to a system. Does the template render correctly? Does the service start? Does the configuration file end up in the right place?

Molecule provides a framework for integration testing Ansible content. It creates test environments, applies your roles, runs verification assertions, and tears everything down.

### Molecule Scenarios

A **scenario** is a complete test definition. Each scenario lives in its own directory under `extensions/molecule/` and contains at minimum a `molecule.yml` configuration file. Most scenarios also include a `converge.yml` playbook and a `verify.yml` playbook.

The collection's scenario for the webserver role lives at:

```text
extensions/molecule/integration_webserver/
  molecule.yml    # Scenario configuration
  converge.yml    # Playbook that applies the role
  verify.yml      # Assertion-based verification
```

#### molecule.yml

The scenario configuration defines the test environment and lifecycle:

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

Key sections:

- **`driver: delegated`** -- Uses the delegated driver instead of containers. This means Molecule runs everything on localhost without needing Docker or Podman. It is simpler for learning and works in any environment.
- **`platforms`** -- Defines the test hosts. With the delegated driver, `localhost` is the only platform.
- **`provisioner`** -- Configures how Ansible runs. The inventory section sets connection variables for localhost.
- **`verifier: ansible`** -- Uses Ansible playbooks for verification instead of a separate tool like Testinfra.
- **`scenario.test_sequence`** -- The ordered list of stages that `molecule test` executes.

#### converge.yml

The converge playbook applies the role under test:

```yaml
---
- name: Converge — apply the webserver role
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

Notice the test-specific overrides:

- **Port 8080** instead of 80 (avoids needing root privileges)
- **`/tmp/molecule-webserver`** as the document root (writable without root)
- **`webserver_service_enabled: false`** (no actual httpd service needed for verification)

These overrides make the test portable -- it runs anywhere without elevated privileges or installed services.

### Writing Assertions

The `verify.yml` playbook contains assertion tasks that check postconditions -- things that should be true after the role has run:

```yaml
---
- name: Verify — assert webserver role postconditions
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
          The document root {{ __verify_document_root }} does not
          exist or is not a directory.
        success_msg: >-
          Document root {{ __verify_document_root }} exists.

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
          The index.html does not contain the expected server name.
        success_msg: >-
          index.html contains the correct server name.

    - name: Assert index page contains the ansible_managed header
      ansible.builtin.assert:
        that:
          - >-
            'Ansible managed' in
            (__verify_index_content.content | b64decode)
        fail_msg: >-
          The index.html is missing the ansible_managed header.
        success_msg: >-
          index.html contains the ansible_managed header.
```

The pattern for each assertion is:

1. **Gather a fact** -- use `ansible.builtin.stat`, `ansible.builtin.slurp`, or another read-only module to capture state
2. **Assert the condition** -- use `ansible.builtin.assert` with `that:`, `fail_msg:`, and `success_msg:`

!!! warning "Use `ansible.builtin.slurp` instead of `command: cat`"
    `ansible.builtin.slurp` is idempotent and works correctly in check mode. `command: cat` reports `changed` by default and fails in check mode unless you add `changed_when: false` and `check_mode: false`. For reading file contents in tests, always prefer `slurp`.

### The Test Lifecycle

When you run `molecule test -s integration_webserver`, Molecule executes ten stages in sequence:

| Stage | What happens |
|-------|-------------|
| **1. Dependency** | Install required collections from `requirements.yml` |
| **2. Cleanup** | Run a cleanup playbook (if defined) |
| **3. Destroy** | Tear down any existing test environment |
| **4. Syntax** | Validate playbook syntax (like `ansible-playbook --syntax-check`) |
| **5. Create** | Create the test environment (with delegated driver, this is a no-op) |
| **6. Prepare** | Run a prepare playbook to set up prerequisites (if defined) |
| **7. Converge** | Run the converge playbook -- this applies the role |
| **8. Verify** | Run the verify playbook -- this checks assertions |
| **9. Cleanup** | Clean up test resources |
| **10. Destroy** | Tear down the test environment |

For iterative development, you do not need to run the full lifecycle every time. Use individual stages:

```bash
# Run only converge (apply the role) — keeps the environment
molecule converge -s integration_webserver

# Run only verify (check assertions) — reuses existing environment
molecule verify -s integration_webserver

# Run the full lifecycle from clean state
molecule test -s integration_webserver

# List all available scenarios
molecule list

# Destroy the test environment when done
molecule destroy -s integration_webserver
```

!!! tip "Iterative workflow"
    During development, use `molecule converge` and `molecule verify` separately. This is much faster than running the full `molecule test` lifecycle, which destroys and recreates the environment on every run. Only run `molecule test` when you want a clean-slate validation (for example, in CI/CD).

## Functional Testing with pytest-ansible

Molecule tests the role as a whole -- it applies the role to a system and checks the results. But sometimes you need finer-grained tests that validate individual pieces in isolation. That is where `pytest-ansible` comes in.

`pytest-ansible` is a pytest plugin that bridges Python's `pytest` framework and Ansible. It provides fixtures for running Ansible modules directly from Python test code, making it possible to write fast, isolated tests for modules, plugins, and role internals.

### Test Structure

The collection's test files live under `tests/`:

```text
tests/
  conftest.py                      # pytest configuration
  unit/
    __init__.py
    test_webserver_defaults.py     # Unit tests for the webserver role
```

#### conftest.py

The `conftest.py` file sets up the environment so `pytest-ansible` can find the collection's modules:

```python
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)

# Point Ansible at the plugins/modules directory
MODULES_PATH = os.path.join(PROJECT_ROOT, "plugins", "modules")
os.environ.setdefault("ANSIBLE_LIBRARY", MODULES_PATH)

# Point Ansible at the editable-install symlink tree
COLLECTIONS_PATH = os.path.join(PROJECT_ROOT, "collections")
os.environ.setdefault("ANSIBLE_COLLECTIONS_PATH", COLLECTIONS_PATH)
```

This runs before any test is collected. Without it, Ansible cannot locate custom modules or resolve FQCNs, resulting in "module not found" errors.

#### Unit Tests

The unit tests validate the role's YAML files without executing any Ansible code. They parse the YAML and check structural properties:

```python
import os
import yaml
import pytest

ROLE_DIR = os.path.join(COLLECTION_ROOT, "roles", "webserver")
DEFAULTS_FILE = os.path.join(ROLE_DIR, "defaults", "main.yml")

@pytest.fixture
def defaults():
    """Load and return the role defaults as a dictionary."""
    with open(DEFAULTS_FILE, "r") as fh:
        return yaml.safe_load(fh)

class TestWebserverDefaults:
    def test_all_defaults_prefixed(self, defaults):
        """Every key in defaults must start with 'webserver_'."""
        for key in defaults:
            assert key.startswith("webserver_"), (
                f"Variable '{key}' is missing the 'webserver_' prefix"
            )

    def test_port_is_integer(self, defaults):
        """webserver_port must be an integer."""
        assert isinstance(defaults["webserver_port"], int)

    def test_service_enabled_is_boolean(self, defaults):
        """webserver_service_enabled must be a boolean."""
        assert isinstance(defaults["webserver_service_enabled"], bool)

    def test_document_root_is_absolute_path(self, defaults):
        """webserver_document_root must be an absolute path."""
        assert defaults["webserver_document_root"].startswith("/")
```

These tests run in milliseconds. They validate conventions that are easy to violate accidentally -- a new variable without the role prefix, a default that should be an integer but is a string, a path that should be absolute but is relative.

The full test file in the companion code also checks:

- **Internal variables** (`vars/main.yml`) are all prefixed with `__webserver_`
- **Argument specs** (`meta/argument_specs.yml`) cover every variable in defaults
- **Type consistency** between defaults and argument specs

### Running pytest

From the collection root:

```bash
cd ansible/collections/parasoltech/infrastructure
pytest tests/ -v
```

Output:

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

Useful pytest flags:

| Flag | Purpose |
|------|---------|
| `-v` | Verbose -- show each test name and result |
| `-s` | No capture -- show print statements and debug output |
| `-x` | Stop on first failure |
| `--tb=short` | Short tracebacks for cleaner output |
| `-k "pattern"` | Run only tests matching the pattern |

## Test Orchestration with tox-ansible

You now have three testing tools: `ansible-lint` for static analysis, `pytest` for unit tests, and Molecule for integration tests. Running them separately works, but it is tedious -- especially when you need to test against multiple Python and Ansible versions.

`tox-ansible` solves this. It is a tox plugin (included in `ansible-dev-tools`) that scans your collection structure and **automatically generates test environments** for linting, unit tests, sanity tests, and integration tests. No manual environment definitions needed.

### Configuration

The configuration file is `tox-ansible.ini` (not `tox.ini` -- this keeps tox-ansible separate from any standard tox configuration):

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

That is the entire configuration. The `skip` list excludes Python versions and Ansible versions that are not available in your environment. Everything else is convention over configuration -- the plugin discovers what to test by scanning the collection structure.

### Auto-Discovery

The plugin scans the collection and generates test environments based on what it finds:

```bash
cd ansible/collections/parasoltech/infrastructure
tox --ansible -c tox-ansible.ini list
```

Output:

```text
default environments:
galaxy                       -> Build and validate collection artifact
integration-py3.12-2.19      -> Integration tests (Molecule scenarios)
sanity-py3.12-2.19           -> Sanity tests (ansible-test sanity)
unit-py3.12-2.19             -> Unit tests (pytest)
```

Each environment name encodes three pieces of information:

- **Test type** -- `sanity`, `unit`, `integration`, or `galaxy`
- **Python version** -- `py3.12`, `py3.13`, etc.
- **Ansible version** -- `2.19`, `2.20`, etc.

The plugin finds these by looking for:

| Test type | Plugin looks for |
|-----------|-----------------|
| **sanity** | Any collection structure (`galaxy.yml`) |
| **unit** | `tests/unit/` directory with Python test files |
| **integration** | `extensions/molecule/` directory with scenarios |
| **galaxy** | `galaxy.yml` at collection root |

### Running Tests

Run all tests:

```bash
tox --ansible -c tox-ansible.ini
```

Run specific test types:

```bash
# Sanity tests only
tox --ansible -c tox-ansible.ini -e sanity-py3.12-2.19

# Unit tests only
tox --ansible -c tox-ansible.ini -e unit-py3.12-2.19

# Integration tests only
tox --ansible -c tox-ansible.ini -e integration-py3.12-2.19

# Build and validate the collection artifact
tox --ansible -c tox-ansible.ini -e galaxy
```

For each environment, tox:

1. Creates a fresh virtual environment
2. Installs the required Python and Ansible versions
3. Installs test dependencies
4. Runs the appropriate test command
5. Reports results

This is the same workflow that runs in CI/CD pipelines. If it passes locally, it will pass in CI.

!!! note "Always pass `--ansible` and `-c tox-ansible.ini`"
    Without `--ansible`, the plugin does not activate and none of the auto-generated environments will appear. Without `-c tox-ansible.ini`, tox looks for `tox.ini` and will not find the skip list.

### The Unified Interface

The power of `tox-ansible` is the unified interface. Instead of remembering:

```bash
ansible-lint                                    # Lint
pytest tests/                                   # Unit tests
molecule test -s integration_webserver          # Integration tests
ansible-galaxy collection build                 # Build artifact
```

You run:

```bash
tox --ansible -c tox-ansible.ini
```

One command. All test types. Consistent environments. This is what the CoP configures as the required CI/CD check for every pull request.

## Exercises

### Exercise 1: Run ansible-lint

Navigate to the collection and run the linter:

```bash
cd ansible/collections/parasoltech/infrastructure
ansible-lint
```

If there are violations, examine the output carefully. Each violation includes the file, line number, rule ID, and description. Try fixing any issues manually, then run `ansible-lint --fix` to see what auto-fix can handle.

### Exercise 2: Write a New Assertion

Open `extensions/molecule/integration_webserver/verify.yml` and add a new assertion that checks the document root directory has the correct permissions (mode `0755`). Use the `__verify_docroot_stat` variable that is already registered.

??? example "Solution"
    ```yaml
    - name: Assert document root has correct permissions
      ansible.builtin.assert:
        that:
          - __verify_docroot_stat.stat.mode == '0755'
        fail_msg: >-
          Document root permissions are
          {{ __verify_docroot_stat.stat.mode }}, expected 0755.
        success_msg: >-
          Document root has correct permissions (0755).
    ```

### Exercise 3: Add a Unit Test

Open `tests/unit/test_webserver_defaults.py` and add a test that verifies `webserver_port` has a default value within a valid port range (1-65535).

??? example "Solution"
    ```python
    def test_port_in_valid_range(self, defaults):
        """webserver_port must be between 1 and 65535."""
        port = defaults["webserver_port"]
        assert 1 <= port <= 65535, (
            f"webserver_port ({port}) is outside the valid range 1-65535"
        )
    ```

### Exercise 4: Run the Full Test Lifecycle

Run the complete Molecule test lifecycle for the webserver role:

```bash
cd ansible/collections/parasoltech/infrastructure/extensions
molecule test -s integration_webserver
```

Watch the output and identify each stage of the lifecycle. If any stage fails, read the error message and fix the issue.

### Exercise 5: Explore tox-ansible

List the auto-discovered test environments:

```bash
cd ansible/collections/parasoltech/infrastructure
tox --ansible -c tox-ansible.ini list
```

Run the unit tests through tox and compare the output to running `pytest` directly. Notice how tox creates an isolated virtual environment for the test run.

## Summary

In this module you:

- Learned the Ansible test pyramid -- lint, unit, and integration tests form layers of increasing thoroughness and cost
- Configured `ansible-lint` with a production profile, learned to read its output, and used auto-fix to resolve violations automatically
- Created a Molecule scenario for the webserver role with a delegated driver, a converge playbook that applies the role, and a verify playbook with assertion-based checks
- Understood the ten-stage Molecule lifecycle and when to use individual stages (`converge`, `verify`) versus the full lifecycle (`test`)
- Wrote `pytest-ansible` unit tests that validate role defaults, internal variables, and argument spec consistency without executing any Ansible code
- Configured `tox-ansible` to auto-discover and orchestrate all test types through a single command with convention over configuration

The CoP at Parasol Tech now has quality gates: `ansible-lint` catches style violations, unit tests catch structural problems, and Molecule integration tests catch runtime failures. Every pull request to the `parasoltech.infrastructure` collection runs through `tox --ansible` before it can be merged.

## Next Steps

Next: [Module 8 -- Packaging and Deployment](8-packaging-and-deployment.md)
