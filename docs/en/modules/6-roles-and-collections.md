# Module 6: Roles and Collections

## Learning Objectives

By the end of this module you will be able to:

- Describe the role directory structure and naming conventions
- Explain when to use `defaults/main.yml` vs `vars/main.yml`
- Scaffold roles and collections using `ansible-creator`
- Manage development environments with `ade`
- Create argument validation with `meta/argument_specs.yml`
- Use Fully Qualified Collection Names (FQCNs)

## The Story So Far

Lionel and Jordan have been writing playbooks, managing inventory across environments, using variables and facts, and deploying configuration files with templates and handlers. The automation works well -- but it lives in a growing pile of playbooks inside one directory, and other teams at Parasol Tech are starting to ask for access.

"The database team wants our nginx setup," Lionel says. "And the monitoring team keeps copying our template tasks into their own playbooks. Every copy drifts a little."

Jordan nods. "We need to package this. One source of truth for the web server configuration that any team can consume without copying files around."

This week, Parasol Tech's leadership sponsors a **Community of Practice (CoP)** -- a cross-team group dedicated to automation standards. The CoP's first decision: all reusable automation must be packaged as **roles** inside **collections**. No more copy-pasted playbooks.

## What Are Roles?

A role is a self-contained unit of automation with a standardized directory structure. Instead of putting everything in a single playbook, you split the automation into well-defined directories -- tasks, variables, templates, handlers, metadata -- each in its own file. Ansible knows how to assemble these pieces automatically.

Think of a role as a function in programming. It takes inputs (variables), does work (tasks), and can be called from any playbook. The directory structure is the interface contract -- anyone reading the role knows exactly where to find each piece.

## Role Directory Structure

Every role follows a standard layout. Here is the structure of the `webserver` role we will build in this module:

```text
roles/webserver/
  defaults/
    main.yml          # User-facing variables with default values
  vars/
    main.yml          # Internal constants (not for users)
  tasks/
    main.yml          # The main task list
  handlers/
    main.yml          # Handler definitions
  templates/
    webserver.conf.j2 # Jinja2 templates
    index.html.j2
  files/              # Static files (none in this role)
  meta/
    main.yml          # Role metadata and dependencies
    argument_specs.yml # Input validation
  README.md           # Documentation
```

Not every directory is required. Ansible only uses the directories that exist. But the naming is strict -- `tasks/main.yml`, not `tasks/install.yml` -- because Ansible looks for `main.yml` by convention.

Each directory has a specific purpose:

| Directory | Purpose |
|-----------|---------|
| `defaults/` | User-facing variables with default values. Lowest precedence. |
| `vars/` | Internal variables and constants. High precedence -- hard to override. |
| `tasks/` | The task list that the role executes. |
| `handlers/` | Handlers that tasks can notify. |
| `templates/` | Jinja2 templates deployed by `ansible.builtin.template`. |
| `files/` | Static files deployed by `ansible.builtin.copy`. |
| `meta/` | Role metadata, dependencies, and argument validation. |

### Splitting Tasks into Components

When a role grows large, you split `tasks/main.yml` into component files and include them:

```yaml
# tasks/main.yml
- name: Install packages
  ansible.builtin.include_tasks:
    file: "{{ role_path }}/tasks/install.yml"

- name: Configure the service
  ansible.builtin.include_tasks:
    file: "{{ role_path }}/tasks/configure.yml"

- name: Manage the service lifecycle
  ansible.builtin.include_tasks:
    file: "{{ role_path }}/tasks/service.yml"
```

Notice the `{{ role_path }}` prefix. This is critical -- it ensures the path resolves to the correct role, even when one role includes another. Never use relative paths like `tasks/install.yml` without it.

!!! warning "Always use `{{ role_path }}` for file references"
    Relative paths in `include_tasks`, `include_vars`, and `template` resolve against the *including* role, not necessarily your role. Use `{{ role_path }}/tasks/`, `{{ role_path }}/vars/`, and `{{ role_path }}/templates/` to be explicit.

## Naming Conventions

Naming is where most role problems start. When multiple roles run in the same play, their variables share a single namespace. If two roles both define a variable called `packages`, one will overwrite the other.

The rule is simple: **prefix everything with the role name**.

### Variable Prefixing

```yaml
# defaults/main.yml — CORRECT
webserver_port: 80
webserver_document_root: /var/www/html
webserver_server_name: localhost

# defaults/main.yml — WRONG (will collide with other roles)
port: 80
document_root: /var/www/html
server_name: localhost
```

This applies to:

- All variables in `defaults/main.yml`
- All variables in `vars/main.yml`
- All registered variables (`register: webserver_config_result`)
- All custom facts (`ansible.builtin.set_fact: webserver_detected_version: ...`)
- All tags (`tags: webserver_install`)

### Internal Variable Prefix

Variables that are internal to the role -- not intended for users to override -- get a double underscore prefix:

```yaml
# vars/main.yml — internal constants
__webserver_packages_default:
  - httpd
__webserver_service_name: httpd
__webserver_config_dir: /etc/httpd/conf
```

The double underscore signals "this is an implementation detail, do not set it in your inventory." Users configure the role through `defaults/main.yml`, not through these internal variables.

### Handler Naming

Handlers also need the role prefix to avoid collisions. Use a naming convention that includes the role name:

```yaml
# handlers/main.yml
- name: Validate webserver configuration
  ansible.builtin.command:
    cmd: "httpd -t"
  changed_when: false
  listen: "webserver_validate_config"

- name: Reload webserver
  ansible.builtin.service:
    name: "{{ __webserver_service_name }}"
    state: reloaded
  listen: "webserver_reload"
```

The `listen` directive lets tasks notify handlers by topic rather than by exact name. This is especially useful in roles because the handler name can be descriptive while the `listen` value follows a strict `rolename_action` pattern.

### Role Names

Role names themselves must use underscores, never dashes:

```text
webserver     # CORRECT
web_server    # CORRECT
web-server    # WRONG — dashes break collection packaging
```

## defaults vs vars

This is one of the most important distinctions in role design, and getting it wrong causes real problems.

### `defaults/main.yml` -- The User Interface

Variables in `defaults/main.yml` have the **lowest precedence** in Ansible's variable hierarchy. This means they can be overridden by almost anything -- inventory variables, group vars, host vars, play vars, extra vars. That is exactly what you want for user-facing configuration.

Think of `defaults/main.yml` as the "API" of your role. It documents every knob the user can turn:

```yaml
# defaults/main.yml
webserver_port: 80
webserver_document_root: /var/www/html
webserver_server_name: localhost
webserver_service_enabled: true
webserver_max_connections: 256
# webserver_admin_email:
# webserver_packages:
```

Notice the commented-out variables at the bottom. These are inputs that have no safe default value (like an admin email), so the role does not set one. But by listing them here, users know these options exist. The comments serve as documentation.

### `vars/main.yml` -- Internal Constants

Variables in `vars/main.yml` have **high precedence** -- they override inventory variables, group vars, and most other sources. Only extra vars (`-e`) can override them.

This makes `vars/main.yml` the wrong place for user-facing defaults. If you put `webserver_port: 80` in `vars/main.yml`, users cannot override it from their inventory. They would need `-e webserver_port=8080` on every run, which defeats the purpose.

Use `vars/main.yml` for values that should not change:

```yaml
# vars/main.yml — internal constants
__webserver_packages_default:
  - httpd
__webserver_service_name: httpd
__webserver_config_dir: /etc/httpd/conf
__webserver_config_file: httpd.conf
```

These are implementation details -- the service name, the config directory path, the default package list. Users should not need to set these, and if they do override them by accident, bad things happen.

!!! danger "Never put user-facing defaults in `vars/main.yml`"
    The high precedence of `vars/` makes variables nearly impossible to override from inventory. Always use `defaults/main.yml` for anything users should be able to customize.

### Quick Reference

| | `defaults/main.yml` | `vars/main.yml` |
|---|---|---|
| **Precedence** | Lowest (easily overridden) | High (hard to override) |
| **Purpose** | User-facing configuration | Internal constants |
| **Naming** | `rolename_variable` | `__rolename_variable` |
| **Can users override?** | Yes, from inventory/group_vars | Only with `-e` extra vars |
| **Contains** | Sensible defaults, documented options | Service names, paths, magic values |

## What Are Collections?

A collection is a distribution package for Ansible content. It bundles roles, plugins, modules, and documentation into a single artifact with a namespace, a version, and declared dependencies.

Before collections, sharing Ansible content meant distributing standalone roles through Ansible Galaxy. This worked, but it had problems: no namespacing (two people could create a role named `nginx`), no dependency management between roles, and no way to bundle roles with custom modules or plugins.

Collections solve all of these. A collection has a **namespace** and a **name** -- like `parasoltech.infrastructure` -- which guarantees uniqueness. It includes a `galaxy.yml` manifest that declares dependencies and versioning. And it can contain any combination of roles, modules, plugins, and documentation.

### Collection Structure

```text
parasoltech/infrastructure/
  galaxy.yml            # Collection manifest (name, version, deps)
  README.md             # Collection documentation
  LICENSE               # License file
  meta/
    runtime.yml         # Minimum Ansible version requirement
  plugins/              # Custom modules, filters, etc.
  roles/
    webserver/          # Roles live here
      defaults/main.yml
      tasks/main.yml
      ...
  tests/                # Collection-level tests
  docs/                 # Additional documentation
```

The key file is `galaxy.yml` -- it is the identity card of the collection.

## Scaffolding with ansible-creator

You do not need to create all these directories and files by hand. The `ansible-creator` CLI tool generates the entire scaffolding for you.

### Creating a Collection

```bash
ansible-creator init collection parasoltech.infrastructure \
  ~/ansible/collections/parasoltech/infrastructure
```

This creates the full directory structure with template files for `galaxy.yml`, `README.md`, `LICENSE`, `meta/runtime.yml`, and placeholder directories for plugins, roles, and tests.

The general syntax is:

```text
ansible-creator init collection <namespace>.<name> <destination-path>
```

!!! tip "VS Code integration"
    If you use the Ansible VS Code extension, you can also scaffold collections through a graphical wizard. Click the Ansible icon in the sidebar, then select **Collection project**. The wizard calls `ansible-creator` behind the scenes and produces the same result.

### Creating a Role Inside a Collection

To add a role to an existing collection:

```bash
cd ~/ansible/collections/parasoltech/infrastructure
ansible-creator init role webserver --path roles/webserver
```

This creates the role directory structure inside the collection's `roles/` directory, including `defaults/main.yml`, `tasks/main.yml`, `handlers/main.yml`, `meta/main.yml`, and template placeholders.

### What ansible-creator Produces

After scaffolding, the collection looks like this:

```text
parasoltech/infrastructure/
  galaxy.yml
  README.md
  LICENSE
  meta/
    runtime.yml
  plugins/
  roles/
    webserver/
      defaults/
        main.yml
      handlers/
        main.yml
      meta/
        main.yml
      tasks/
        main.yml
      templates/
      vars/
        main.yml
      README.md
  tests/
  docs/
```

All files come with sensible defaults that you customize for your use case. The `galaxy.yml` needs your namespace and description; the role's `defaults/main.yml` needs your variables; the `tasks/main.yml` needs your automation logic.

## Configuring galaxy.yml

The `galaxy.yml` file is the manifest for your collection. Here is the one for `parasoltech.infrastructure`:

```yaml
---
namespace: parasoltech
name: infrastructure
version: 1.0.0
readme: README.md
authors:
  - Parasol Tech Platform Team <platform@parasol.example>
description: Infrastructure automation collection for Parasol Tech
license_file: LICENSE
tags:
  - infrastructure
  - linux
dependencies:
  "ansible.posix": ">=1.0.0"
build_ignore:
  - .gitignore
  - .venv
  - collections
  - .tox
  - .ade
```

Each field has a specific purpose:

| Field | Purpose |
|-------|---------|
| `namespace` | The organization or team name. Immutable after publishing. |
| `name` | The collection name. Together with namespace, forms the FQCN. |
| `version` | Semantic version (see [Semantic Versioning](#semantic-versioning) below). |
| `readme` | Path to the README file. |
| `authors` | List of authors with optional email. |
| `description` | Short description for Galaxy/Hub search results. |
| `license_file` | Path to the license file. |
| `tags` | Discovery tags for Galaxy/Hub. Available tags include `application`, `cloud`, `database`, `infrastructure`, `linux`, `monitoring`, `networking`, `security`, `tools`, `windows`, and others. |
| `dependencies` | Other collections this one requires, with version constraints. |
| `build_ignore` | Files and directories to exclude when building the collection artifact. |

### Dependencies

The `dependencies` field declares which other collections yours needs. Version constraints use pip-style syntax:

```yaml
dependencies:
  "ansible.posix": ">=1.0.0"       # 1.0.0 or higher
  "ansible.utils": "*"             # any version
  "community.general": ">=5.0,<7"  # 5.x or 6.x, not 7.x
```

When someone installs your collection, `ansible-galaxy` automatically installs these dependencies too.

### Build Ignore

The `build_ignore` field keeps development artifacts out of the published package. When `ade` manages your collection, it creates `.venv`, `collections`, and `.ade` directories inside the collection root. These are useful during development but should never be included in the distributed tarball:

```yaml
build_ignore:
  - .gitignore
  - .venv
  - collections
  - .tox
  - .ade
```

## Managing Dependencies with ade

The **Ansible Development Environment** tool (`ade`) manages your collection's development workspace. It handles:

- Creating isolated Python virtual environments
- Installing your collection in **editable mode** (changes take effect immediately)
- Resolving and installing collection dependencies declared in `galaxy.yml`
- Installing Python dependencies from `requirements.txt` and `test-requirements.txt`
- Tracking system-level package requirements

### Installing Your Collection for Development

Navigate to your collection root and run:

```bash
cd ~/ansible/collections/parasoltech/infrastructure
ade install -e .
```

The `-e .` flag means **editable install** -- `ade` creates a symlink from the virtual environment into your working directory. When you edit files in the collection, the changes are immediately visible to Ansible without reinstalling.

Typical output looks like this:

```text
$ ade install -e .
    Note: Created virtual environment: .venv
    Note: Installed collections include: ansible.posix and parasoltech.infrastructure
    Note: All python requirements are installed.
    Note: All required system packages are installed.
```

!!! note "Editable vs regular install"
    Without `-e`, `ade install .` copies the collection into the virtual environment. Changes to your source files are not reflected until you reinstall. Always use `-e` during development.

### Viewing the Dependency Tree

To see what `ade` has installed and the full dependency graph:

```bash
ade tree -v
```

This shows your collection, its dependencies, and their dependencies -- useful for understanding what gets pulled in and for troubleshooting version conflicts.

### Handling System Dependencies

Some collections require system-level packages (C libraries, Python bindings compiled from C, etc.). When `ade` detects missing system packages, it tells you what to install:

```text
$ ade install -e .
 Warning: Required system packages are missing. Please use the system
          package manager to install them.
          - python3-cffi
          - python3-cryptography
```

Install the listed packages with your system package manager (`dnf install`, `apt install`, etc.), then re-run `ade install -e .`.

## Argument Validation

Every role should validate its inputs. If a user passes `webserver_port: "eighty"` instead of an integer, the role should fail immediately with a clear message -- not halfway through, when a template renders `Listen eighty` and the web server refuses to start.

Ansible provides argument validation through `meta/argument_specs.yml`. This file declares the type, default value, and constraints for every role input.

### Writing argument_specs.yml

Here is the argument specification for the `webserver` role:

```yaml
---
argument_specs:
  main:
    short_description: Install and configure a web server
    description:
      - Install web server packages, deploy configuration from
        a template, deploy a default index page, and manage the
        service lifecycle.
    options:
      webserver_port:
        type: int
        default: 80
        description: The HTTP port the web server listens on.
      webserver_document_root:
        type: str
        default: /var/www/html
        description: >-
          The document root directory where web content is served from.
      webserver_server_name:
        type: str
        default: localhost
        description: >-
          The server name used in the virtual host configuration.
      webserver_service_enabled:
        type: bool
        default: true
        description: >-
          Whether to start and enable the web server service.
      webserver_max_connections:
        type: int
        default: 256
        description: >-
          The maximum number of simultaneous client connections.
      webserver_admin_email:
        type: str
        required: false
        description: >-
          The admin email shown in server error pages.
          If not set, the server default is used.
      webserver_packages:
        type: list
        elements: str
        required: false
        description: >-
          List of packages to install. If not provided, the role
          uses platform-specific defaults.
```

The `main` key matches the entrypoint -- `tasks/main.yml`. If your role has multiple entrypoints (e.g., `tasks/install.yml` and `tasks/configure.yml` called separately), each gets its own entry under `argument_specs`.

### What Validation Catches

When Ansible loads a role with argument specs, it checks:

- **Type**: Is `webserver_port` actually an integer? Is `webserver_service_enabled` a boolean?
- **Required**: Is `webserver_port` provided? (If no default exists and `required: true`)
- **Choices**: Is the value one of an allowed set? (Use `choices: [a, b, c]`)
- **Elements**: For list types, what type should each element be?

If validation fails, Ansible stops before running any tasks and reports the error. This is fail-fast behavior -- catching errors at the top instead of midway through the role.

### The Connection to defaults/main.yml

Notice that the defaults in `argument_specs.yml` match `defaults/main.yml`. They should always agree. The `argument_specs.yml` is the formal contract; `defaults/main.yml` is where the values are actually set. If they diverge, the behavior becomes confusing.

!!! tip "Keep defaults and argument specs in sync"
    When you add a new variable to `defaults/main.yml`, add the matching entry to `meta/argument_specs.yml`. When you change a default, update both files.

## Fully Qualified Collection Names (FQCNs)

A Fully Qualified Collection Name identifies any piece of content within a collection. The format is:

```text
<namespace>.<collection>.<content_name>
```

For modules:

```yaml
# FQCN — always correct, never ambiguous
- name: Install packages
  ansible.builtin.package:
    name: httpd
    state: present

# Short name — works only if ansible.builtin is in the search path
- name: Install packages
  package:
    name: httpd
    state: present
```

For roles:

```yaml
# Using a collection role with FQCN
- name: Deploy web servers
  hosts: webservers

  roles:
    - role: parasoltech.infrastructure.webserver
```

### Why FQCNs Matter

Short names like `copy`, `template`, or `package` work because Ansible searches a default set of collections (starting with `ansible.builtin`). But when you add community or custom collections, short names become ambiguous. If both `ansible.builtin` and `community.general` provide a module with the same name, which one runs?

FQCNs eliminate this ambiguity. `ansible.builtin.copy` always means the copy module from `ansible.builtin`. `community.general.filesystem` always means the filesystem module from `community.general`. There is never any doubt.

Throughout this course we have used FQCNs from the start -- `ansible.builtin.template`, `ansible.builtin.service`, `ansible.builtin.debug`. This is intentional. It is a habit worth building early, even when short names would work.

## Semantic Versioning

Collections use **semantic versioning** (SemVer) to communicate the impact of changes. The version number has three parts:

```text
MAJOR.MINOR.PATCH
  1  .  0  .  0
```

| Part | When to increment | Example |
|------|-------------------|---------|
| **MAJOR** | Breaking changes (removed variables, changed behavior) | 1.0.0 -> 2.0.0 |
| **MINOR** | New features (new roles, new variables, new modules) | 1.0.0 -> 1.1.0 |
| **PATCH** | Bug fixes (no new features, no breaking changes) | 1.0.0 -> 1.0.1 |

For the `parasoltech.infrastructure` collection:

- Adding a new `database` role? Bump MINOR: `1.0.0` -> `1.1.0`
- Fixing a template bug in the `webserver` role? Bump PATCH: `1.0.0` -> `1.0.1`
- Renaming `webserver_port` to `webserver_listen_port`? That is a breaking change. Bump MAJOR: `1.0.0` -> `2.0.0`

Semantic versioning lets consumers specify dependency constraints with confidence. If your collection is at `1.3.2`, a consumer declaring `"parasoltech.infrastructure": ">=1.0.0,<2.0.0"` knows they will get bug fixes and new features but never breaking changes.

## Ansible Galaxy and Automation Hub

**Ansible Galaxy** ([galaxy.ansible.com](https://galaxy.ansible.com)) is the public community registry for Ansible collections. Anyone can browse, download, and publish collections.

**Automation Hub** is the enterprise equivalent -- a curated, supported registry included with the Ansible Automation Platform. Organizations use private Automation Hub instances to distribute internal collections (like `parasoltech.infrastructure`).

### Installing Collections from Galaxy

```bash
# Install a specific collection
ansible-galaxy collection install community.general

# Install a specific version
ansible-galaxy collection install community.general:9.0.0

# Install from a requirements file
ansible-galaxy collection install -r requirements.yml
```

A `requirements.yml` file lists multiple collections with version constraints:

```yaml
---
collections:
  - name: ansible.posix
    version: ">=1.0.0"
  - name: community.general
    version: ">=9.0.0"
```

### Building a Collection for Distribution

To build your collection into an installable tarball:

```bash
cd ~/ansible/collections/parasoltech/infrastructure
ansible-galaxy collection build
```

This produces a file like `parasoltech-infrastructure-1.0.0.tar.gz` that can be installed with `ansible-galaxy collection install` or uploaded to Galaxy or Automation Hub.

### Publishing to Galaxy

```bash
# Publish to Galaxy (requires an API key from galaxy.ansible.com)
ansible-galaxy collection publish parasoltech-infrastructure-1.0.0.tar.gz
```

For internal distribution at Parasol Tech, the CoP publishes to a private Automation Hub instead. The workflow is similar -- build the tarball, then push it to the Hub.

## Building the webserver Role

Now let us build the `parasoltech.infrastructure.webserver` role step by step. This role installs a web server, deploys a configuration file from a template, creates a default index page, and manages the service lifecycle.

### defaults/main.yml

The user-facing variables define what consumers of the role can customize:

```yaml
---
# The HTTP port the web server listens on
webserver_port: 80

# The document root where web content is served from
webserver_document_root: /var/www/html

# The server name used in the virtual host configuration
webserver_server_name: localhost

# Whether to start and enable the web server service
webserver_service_enabled: true

# The maximum number of simultaneous client connections
webserver_max_connections: 256

# The admin email shown in server error pages
# webserver_admin_email:

# Packages to install (overridable per platform via vars/)
# webserver_packages:
```

Every variable has the `webserver_` prefix. The two commented-out variables (`webserver_admin_email`, `webserver_packages`) have no safe default, so they are listed but not set. Users know these options exist by reading this file.

### vars/main.yml

Internal constants that should not be overridden:

```yaml
---
__webserver_packages_default:
  - httpd
__webserver_service_name: httpd
__webserver_config_dir: /etc/httpd/conf
__webserver_config_file: httpd.conf
```

The double underscore prefix marks these as internal. The service name, config directory, and default packages are implementation details that users should not need to change.

### tasks/main.yml

The task list ties everything together. Notice how it uses patterns from every previous module -- package management (Module 2), templates with backup (Module 5), handlers (Module 5), and variable-driven logic (Module 4):

```yaml
---
- name: Install web server packages
  ansible.builtin.package:
    name: "{{ webserver_packages | default(__webserver_packages_default) }}"
    state: present

- name: Ensure document root exists
  ansible.builtin.file:
    path: "{{ webserver_document_root }}"
    state: directory
    owner: root
    group: root
    mode: "0755"

- name: Deploy web server configuration
  ansible.builtin.template:
    src: "{{ role_path }}/templates/webserver.conf.j2"
    dest: "{{ __webserver_config_dir }}/{{ __webserver_config_file }}"
    owner: root
    group: root
    mode: "0644"
    backup: true
  notify:
    - webserver_validate_config
    - webserver_reload

- name: Deploy default index page
  ansible.builtin.template:
    src: "{{ role_path }}/templates/index.html.j2"
    dest: "{{ webserver_document_root }}/index.html"
    owner: root
    group: root
    mode: "0644"
    backup: true

- name: Ensure web server service is in the desired state
  ansible.builtin.service:
    name: "{{ __webserver_service_name }}"
    state: "{{ webserver_service_enabled | ternary('started', 'stopped') }}"
    enabled: "{{ webserver_service_enabled }}"
```

Key patterns to notice:

- **`{{ role_path }}/templates/`** for explicit template paths
- **`backup: true`** on every template/copy task
- **FQCNs** throughout (`ansible.builtin.package`, not `package`)
- **Handler notification** uses the `listen` topics (`webserver_validate_config`, `webserver_reload`)
- **`| default(__webserver_packages_default)`** lets users override packages while providing a built-in fallback

### handlers/main.yml

```yaml
---
- name: Validate webserver configuration
  ansible.builtin.command:
    cmd: "httpd -t"
  changed_when: false
  listen: "webserver_validate_config"

- name: Reload webserver
  ansible.builtin.service:
    name: "{{ __webserver_service_name }}"
    state: reloaded
  listen: "webserver_reload"

- name: Restart webserver
  ansible.builtin.service:
    name: "{{ __webserver_service_name }}"
    state: restarted
  listen: "webserver_restart"
```

Notice `changed_when: false` on the validation command -- it is a read-only check, so it should never report a change.

### Templates

The web server configuration template (`webserver.conf.j2`) uses patterns from Module 5:

```jinja
{{ ansible_managed | comment }}
#
# Web server configuration for {{ webserver_server_name }}

Listen {{ webserver_port }}

ServerName {{ webserver_server_name }}
DocumentRoot "{{ webserver_document_root }}"

MaxRequestWorkers {{ webserver_max_connections }}

{% if webserver_admin_email is defined %}
ServerAdmin {{ webserver_admin_email }}
{% endif %}

<Directory "{{ webserver_document_root }}">
    AllowOverride None
    Require all granted
</Directory>

ErrorLog "logs/error_log"
CustomLog "logs/access_log" combined
```

And a simple `index.html.j2`:

```jinja
{{ ansible_managed | comment('<!--', '-->') }}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ webserver_server_name }}</title>
</head>
<body>
    <h1>Welcome to {{ webserver_server_name }}</h1>
    <p>This page is managed by Ansible.</p>
    <p>Served by the <code>parasoltech.infrastructure.webserver</code> role.</p>
</body>
</html>
```

Notice how `{{ ansible_managed | comment('<!--', '-->') }}` uses custom comment delimiters for HTML. The `| comment` filter accepts arguments to change the comment syntax from the default `#`.

### Using the Role in a Playbook

A playbook that uses this role is short -- the complexity is inside the role:

```yaml
---
- name: Deploy web servers
  hosts: webservers

  roles:
    - role: parasoltech.infrastructure.webserver
      vars:
        webserver_port: 8080
        webserver_server_name: web.parasol.example
        webserver_document_root: /var/www/parasol
        webserver_admin_email: admin@parasol.example
```

The playbook is a list of roles, not a list of tasks. All the logic -- installing packages, deploying templates, managing services -- lives inside the role. The playbook just says *what* to apply and *where*.

## Exercises

### Exercise 1: Explore the Collection Structure

Navigate to the companion collection and examine the structure:

```bash
cd ansible/collections/parasoltech/infrastructure
find . -type f | sort
```

Open the key files and verify:

1. `galaxy.yml` has the correct namespace, name, and version
2. `roles/webserver/defaults/main.yml` has all variables prefixed with `webserver_`
3. `roles/webserver/vars/main.yml` has internal variables prefixed with `__webserver_`
4. `roles/webserver/meta/argument_specs.yml` matches the defaults

### Exercise 2: Scaffold a New Collection with ansible-creator

Create a second collection using `ansible-creator`:

```bash
ansible-creator init collection parasoltech.monitoring \
  ~/ansible/collections/parasoltech/monitoring
```

Explore the generated files. Compare the structure to the `parasoltech.infrastructure` collection. Notice how `ansible-creator` generates the same layout every time -- consistent scaffolding means consistent collections.

### Exercise 3: Use ade for Dependency Management

Install the `parasoltech.infrastructure` collection in editable mode:

```bash
cd ansible/collections/parasoltech/infrastructure
ade install -e .
```

Check the dependency tree:

```bash
ade tree -v
```

You should see `ansible.posix` listed as a dependency (declared in `galaxy.yml`).

### Exercise 4: Add Argument Validation

Add a new variable to the `webserver` role:

1. Add `webserver_log_level` to `defaults/main.yml` with a default of `warn`
2. Add the matching entry to `meta/argument_specs.yml` with `type: str` and `choices: [debug, info, notice, warn, error, crit]`
3. Use the new variable in the `webserver.conf.j2` template

Test that validation works by passing an invalid value:

```bash
ansible-playbook -e "webserver_log_level=invalid" your-playbook.yml
```

Ansible should reject the value before running any tasks.

### Exercise 5: Build the Collection

Build the collection into a distributable tarball:

```bash
cd ansible/collections/parasoltech/infrastructure
ansible-galaxy collection build
```

Examine the resulting `.tar.gz` file. Notice that the directories listed in `build_ignore` (`.venv`, `collections`, `.tox`, `.ade`) are not included in the archive.

## Summary

In this module you:

- Learned the role directory structure and how Ansible assembles tasks, defaults, vars, handlers, templates, and metadata into a reusable unit
- Understood the critical difference between `defaults/main.yml` (user-facing, low precedence) and `vars/main.yml` (internal, high precedence)
- Applied naming conventions: prefix all role variables with the role name, prefix internal variables with double underscores, never use dashes in role names
- Created argument validation with `meta/argument_specs.yml` to fail fast on bad input
- Scaffolded a collection and role with `ansible-creator` and managed the development environment with `ade`
- Configured `galaxy.yml` with metadata, dependencies, version, and build ignore rules
- Used Fully Qualified Collection Names to reference content unambiguously
- Understood semantic versioning and how it communicates the impact of changes

The CoP at Parasol Tech now has a standard: all reusable automation goes into the `parasoltech.infrastructure` collection with properly named, validated, documented roles. The database team installs the collection and uses the `webserver` role without copying a single file. When the platform team fixes a bug, they bump the patch version and every consumer gets the fix on their next install.

## Next Steps

Next: [Module 7 -- Testing Your Automation](7-testing-your-automation.md)
