# Module 4: Variables and Facts

## Learning Objectives

By the end of this module you will be able to:

- Define variables at different precedence levels and predict which value wins
- Access Ansible facts using bracket notation (`ansible_facts['key']`)
- Use registered variables and `set_fact` for dynamic data
- Debug variables with `ansible.builtin.debug` and `ansible-navigator`

## The Story So Far

Lionel's teammate Jordan joins the Parasol Tech platform team. Together they look at the playbooks from Module 2 and the inventory from Module 3. Everything works, but there is a problem: configuration values are hardcoded. The same playbook needs to install different packages in dev and production, use different log levels, and toggle monitoring on or off depending on the environment.

"We need to parameterize everything," Jordan says. "One playbook, multiple environments. The variable system is how Ansible does this."

## Variable Types and Where to Define Them

Variables in Ansible are key-value pairs that let you parameterize your automation. Instead of hardcoding a package name or a file path, you reference a variable -- and the value comes from whatever context the playbook is running in.

### Where Variables Come From

There are several places you can define variables, each with a different scope and purpose:

| Location | Scope | When to use |
|----------|-------|-------------|
| `defaults/main.yml` (in a role) | Role defaults | Lowest precedence -- safe defaults that users can override |
| `group_vars/*.yml` | All hosts in a group | Environment- or function-specific values |
| `host_vars/*.yml` | A single host | Per-host overrides (DB primary vs. replica, etc.) |
| `vars/main.yml` (in a role) | Role internals | Constants and magic values that users should not change |
| `vars:` in a play | Play scope | Values specific to that play |
| `vars:` in a task | Task scope | Values specific to that task |
| `set_fact` | Host scope (runtime) | Computed or dynamic values |
| `register` | Host scope (runtime) | Captured output from a task |
| Extra vars (`-e`) | Global | Overrides from the command line -- highest precedence |

You already used several of these in Module 3 without thinking about it. The `group_vars/all.yml` file defines `parasol_organization`, `parasol_ntp_server`, and `parasol_dns_servers` for every host. The `group_vars/dev.yml` file sets `parasol_environment: "dev"` and `parasol_log_level: "debug"` for all dev hosts.

### Variable Naming Conventions

Good variable names prevent collisions and make the source obvious:

- **Prefix with context**: `parasol_ntp_server`, not just `ntp_server`. If you later add a role called `ntp`, an unprefixed `ntp_server` would collide with the role's own variables.
- **Use snake_case**: `parasol_backup_schedule`, not `parasolBackupSchedule` or `parasol-backup-schedule`.
- **No special characters** other than underscores -- dashes and dots break variable resolution.

When working inside a role (Module 6), you will prefix every variable with the role name. For now, Parasol Tech prefixes everything with `parasol_` as an organizational namespace.

## Variable Precedence

When the same variable name is defined in multiple places, Ansible needs a rule to decide which value wins. This rule is the **precedence chain**.

### The Simplified Chain

Ansible's full precedence list has over 20 levels, but in practice you only need to think about these six tiers (from lowest to highest precedence):

```text
1. Role defaults        (defaults/main.yml)           -- lowest
2. Inventory variables  (group_vars/, host_vars/)
3. Play vars / role vars
4. Task vars / block vars
5. set_fact / registered vars
6. Extra vars (-e)                                     -- highest (ALWAYS WIN)
```

Each tier overrides the one above it. If the same variable appears at multiple levels, the highest-precedence definition wins.

### Seeing Precedence in Action

The companion playbook `variable-precedence.yml` demonstrates this. It defines `demo_message` at the play level and uses `set_fact` to override it:

```yaml
- name: Demonstrate variable precedence
  hosts: localhost
  connection: local
  gather_facts: false

  vars:
    demo_message: "Defined in play vars"

  tasks:
    - name: Display the winning value of demo_message
      ansible.builtin.debug:
        msg: "demo_message = {{ demo_message }}"
        verbosity: 0
```

Run it:

```bash
cd ansible
ansible-navigator run playbooks/module-04/variable-precedence.yml --mode stdout
```

Now run it again, passing an extra var:

```bash
ansible-navigator run playbooks/module-04/variable-precedence.yml \
  --mode stdout -e "demo_message='Extra vars win!'"
```

The output changes because extra vars sit at the top of the precedence chain. This is why extra vars are reserved for overrides and troubleshooting -- they bypass every other definition.

### Precedence Rules to Remember

!!! warning "Keep it simple"
    The single most common source of confusion in Ansible is variable precedence. Minimize the number of levels you use. A good rule of thumb:

    - **Role defaults** for safe defaults
    - **Inventory variables** for environment-specific desired state
    - **Role vars** for internal constants
    - **Extra vars** for troubleshooting overrides

    If you find yourself using more than four levels for the same variable, your design needs simplification.

!!! danger "Never put defaults in `vars/main.yml`"
    Variables in `vars/main.yml` (role vars) have higher precedence than inventory variables. If you put a default value there, users cannot override it from `group_vars/` or `host_vars/` -- the role var always wins. User-facing defaults belong in `defaults/main.yml`.

## Ansible Facts

**Facts** are variables that Ansible discovers automatically about the target system. They describe what the system *is* -- its operating system, IP addresses, CPU count, memory, disk layout, and more. Facts represent **as-is information** (what is true right now), as opposed to variables, which represent **to-be information** (what you want the system to become).

### Accessing Facts

Facts are stored in the `ansible_facts` dictionary. You access them using **bracket notation**:

```yaml
ansible_facts['distribution']        # "Fedora", "Ubuntu", "RedHat", etc.
ansible_facts['os_family']           # "RedHat", "Debian", "Suse", etc.
ansible_facts['distribution_version'] # "42", "24.04", "9.4", etc.
ansible_facts['memtotal_mb']         # Total RAM in megabytes
ansible_facts['hostname']            # Short hostname
ansible_facts['default_ipv4']        # Default IPv4 address info (dict)
```

!!! warning "Always use bracket notation"
    You will see older code and tutorials using `ansible_distribution` or `ansible_facts.distribution` (dot notation). **Always use `ansible_facts['distribution']`** -- bracket notation is explicit, unambiguous, and the recommended practice.

### Common Fact Categories

| Category | Example keys | What they tell you |
|----------|-------------|-------------------|
| OS info | `distribution`, `os_family`, `distribution_version` | What OS is running |
| Hardware | `architecture`, `processor_count`, `memtotal_mb` | CPU, memory, arch |
| Network | `hostname`, `fqdn`, `default_ipv4`, `all_ipv4_addresses` | Network config |
| Storage | `mounts`, `devices` | Disk and filesystem info |
| Date/time | `date_time` | Current date and time on the target |

### The Facts Demo Playbook

The companion playbook `facts-demo.yml` gathers facts and displays them:

```yaml
- name: Gather and display system facts
  hosts: localhost
  connection: local

  tasks:
    - name: Display operating system information
      ansible.builtin.debug:
        msg:
          - "Distribution: {{ ansible_facts['distribution'] }}"
          - "Major version: {{ ansible_facts['distribution_major_version'] }}"
          - "Full version: {{ ansible_facts['distribution_version'] }}"
          - "OS family: {{ ansible_facts['os_family'] }}"
        verbosity: 0
```

Run it:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml --mode stdout
```

## Gathering Facts

### How Fact Gathering Works

When a play starts and `gather_facts` is `true` (the default), Ansible runs the `ansible.builtin.setup` module on each target host. This module collects system information and populates the `ansible_facts` dictionary. This happens before any tasks in the play execute.

```yaml
# Default behavior -- facts are gathered automatically
- name: Play with facts
  hosts: all
  # gather_facts: true  (this is the default, you don't need to write it)

  tasks:
    - name: Use a fact
      ansible.builtin.debug:
        msg: "Running on {{ ansible_facts['distribution'] }}"
        verbosity: 0
```

### Disabling Fact Gathering

If your play does not need facts, you can disable gathering to speed things up:

```yaml
- name: Play without facts
  hosts: all
  gather_facts: false

  tasks:
    - name: Do something that does not need facts
      ansible.builtin.debug:
        msg: "No facts needed here"
        verbosity: 0
```

This is especially useful when targeting many hosts -- fact gathering runs on every host and can add significant time to playbook execution.

### Minimal Fact Subsets

Sometimes you need *some* facts but not all of them. The `ansible.builtin.setup` module accepts a `gather_subset` parameter that lets you choose which categories to collect:

```yaml
- name: Gather only network and hardware facts
  hosts: localhost
  connection: local
  gather_facts: false

  tasks:
    - name: Gather a minimal subset
      ansible.builtin.setup:
        gather_subset:
          - "!all"
          - "!min"
          - network
          - hardware
```

The `!all` removes the default full set, `!min` removes the minimum set (which is collected by default even when you exclude `all`), and then you add back only what you need. Common subsets include: `min`, `network`, `hardware`, `virtual`, `ohai`, and `facter`.

The companion playbook `facts-demo.yml` includes a second play that demonstrates minimal subset gathering.

## Registered Variables and set_fact

Sometimes you need data that is not available until runtime -- the output of a command, the existence of a file, or a value computed from other variables. Ansible provides two mechanisms for this: `register` and `set_fact`.

### Registering Task Output

The `register` keyword captures the full result of a task into a variable:

```yaml
- name: Check if a configuration file exists
  ansible.builtin.stat:
    path: /etc/myapp.conf
  register: __myapp_config

- name: Display whether the config file exists
  ansible.builtin.debug:
    msg: "Config file exists: {{ __myapp_config.stat.exists }}"
    verbosity: 0
```

The registered variable (`__myapp_config`) is a dictionary containing the module's return values. Different modules return different structures -- check the module documentation to see what keys are available.

!!! tip "Naming registered variables"
    Prefix internal (non-user-facing) registered variables with double underscore: `__myapp_config`, not `myapp_config`. This signals that the variable is an implementation detail, not something a user should set or override.

### Common Registered Variable Fields

Most registered variables share these standard fields:

| Field | Description |
|-------|------------|
| `changed` | Whether the task made a change (`true`/`false`) |
| `failed` | Whether the task failed |
| `rc` | Return code (for `command`/`shell` modules) |
| `stdout` | Standard output as a single string |
| `stdout_lines` | Standard output as a list of lines |
| `stderr` | Standard error output |
| `skipped` | Whether the task was skipped |

### Using `set_fact`

The `ansible.builtin.set_fact` module creates or overrides a variable at runtime. Unlike `register`, which captures task output, `set_fact` lets you compute and assign arbitrary values:

```yaml
- name: Set a computed variable
  ansible.builtin.set_fact:
    app_base_url: "https://{{ ansible_facts['fqdn'] }}:{{ app_port | default(8443) }}"

- name: Display the computed URL
  ansible.builtin.debug:
    msg: "Application URL: {{ app_base_url }}"
    verbosity: 0
```

Facts set with `set_fact` have higher precedence than play vars and inventory vars, and they persist for the rest of the play (and across plays if `cacheable: true` is set).

### When to Use Each

| Mechanism | Use when |
|-----------|----------|
| `register` | You need the output of a task (command result, file status, API response) |
| `set_fact` | You need to compute a value from other variables or facts |

## Debugging Variables

When a playbook does not behave as expected, you need ways to inspect variables and understand what values Ansible is actually using.

### The `ansible.builtin.debug` Module

The `debug` module prints messages or variable values during playbook execution. It is Ansible's equivalent of a `print()` statement.

```yaml
# Print a message
- name: Display a status message
  ansible.builtin.debug:
    msg: "Processing host {{ inventory_hostname }}"
    verbosity: 0

# Print an entire variable
- name: Display the full registered result
  ansible.builtin.debug:
    var: __myapp_config
    verbosity: 1
```

### The `verbosity` Parameter

Every `debug` task should include a `verbosity:` parameter. This controls the minimum verbosity level at which the message is displayed:

| Verbosity | When it shows | Use for |
|-----------|--------------|---------|
| `0` | Always (default run) | Output that is the point of the playbook (demos, reports) |
| `1` | `-v` | Basic troubleshooting information |
| `2` | `-vv` | Detailed internal state |
| `3` | `-vvv` | Deep debugging (full variable dumps) |

```yaml
# Always visible -- this debug IS the output (teaching/demo context)
- name: Display the result
  ansible.builtin.debug:
    msg: "Environment: {{ parasol_environment }}"
    verbosity: 0

# Only with -v -- for troubleshooting
- name: Show intermediate state
  ansible.builtin.debug:
    var: __intermediate_result
    verbosity: 1

# Only with -vv -- verbose internals
- name: Dump full variable for deep debugging
  ansible.builtin.debug:
    var: hostvars[inventory_hostname]
    verbosity: 2
```

!!! tip "Rule of thumb for verbosity"
    In production playbooks, set `verbosity: 1` or higher on all debug tasks so they are silent during normal runs. In teaching and demo playbooks (like the companion code for this course), `verbosity: 0` is appropriate because showing the output *is* the purpose.

### Inspecting Variables in `ansible-navigator`

When you run a playbook in `ansible-navigator`'s interactive mode (the default, without `--mode stdout`), you can drill into task results and inspect variables visually:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml
```

In interactive mode:

1. The main screen shows the play list -- press a number to select a play
2. Each play shows its tasks -- press a number to select a task
3. The task detail screen shows the full result, including all registered variables and facts
4. Press `0` to see the host detail with all variable values

This is often faster than adding `debug` tasks, especially when you are not sure which variable you need to inspect.

### Viewing All Host Variables

You can also use `ansible-navigator` to inspect all variables assigned to a host without running a playbook:

```bash
ansible-navigator inventory --host localhost --mode stdout
```

This displays every variable that Ansible would assign to that host, including group vars, host vars, and built-in special variables.

## Conditionals with `when`

Variables and facts become truly powerful when you use them to make decisions. The `when` keyword lets you conditionally execute a task based on the value of a variable, a fact, or a registered result.

### Basic `when` with Facts

```yaml
- name: Install EPEL repository on Red Hat systems
  ansible.builtin.yum_repository:
    name: epel
    description: EPEL Repository
    baseurl: https://download.example/pub/epel/$releasever/$basearch/
    gpgcheck: true
  when: ansible_facts['os_family'] == "RedHat"
```

The task only runs if the target host is a Red Hat family system (RHEL, Fedora, CentOS, etc.). On Debian-based systems, the task is skipped.

### Combining Conditions

Multiple conditions can be combined as a list (AND logic) or with `or`:

```yaml
# AND -- all conditions must be true (list syntax)
- name: Configure production monitoring
  ansible.builtin.template:
    src: monitoring.conf.j2
    dest: /etc/monitoring.conf
  when:
    - ansible_facts['os_family'] == "RedHat"
    - parasol_monitoring_enabled | default(false)

# OR -- any condition is sufficient
- name: Alert on low resources
  ansible.builtin.debug:
    msg: "Resource warning on {{ inventory_hostname }}"
    verbosity: 0
  when: >-
    ansible_facts['memtotal_mb'] < 512
    or ansible_facts['processor_count'] < 2
```

### Conditions with Registered Variables

A common pattern is to run a check, register the result, and conditionally act on it:

```yaml
- name: Check if application config exists
  ansible.builtin.stat:
    path: /etc/myapp.conf
  register: __myapp_config

- name: Create default config if missing
  ansible.builtin.copy:
    dest: /etc/myapp.conf
    content: "# Default configuration\n"
    mode: "0644"
  when: not __myapp_config.stat.exists
```

### Conditions in Loops

When you combine `when` with `loop`, the condition is evaluated for each item:

```yaml
- name: Install only required packages
  ansible.builtin.dnf:
    name: "{{ item.name }}"
    state: present
  loop:
    - name: httpd
      required: true
    - name: debug-tools
      required: false
  when: item.required
```

The companion playbook `conditionals.yml` demonstrates all of these patterns.

## Exercises

### Exercise 1: Run the Variable Precedence Demo

Run the precedence playbook and observe the output:

```bash
cd ansible
ansible-navigator run playbooks/module-04/variable-precedence.yml --mode stdout
```

Then run it again with an extra var override:

```bash
ansible-navigator run playbooks/module-04/variable-precedence.yml \
  --mode stdout -e "demo_message='I am from extra vars'"
```

Answer: What value does `demo_message` have in each run? Why?

### Exercise 2: Explore Facts

Run the facts demo playbook:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml --mode stdout
```

Then run it again in interactive mode to drill into the full fact set:

```bash
ansible-navigator run playbooks/module-04/facts-demo.yml
```

Navigate to the first play's first task and explore the `ansible_facts` dictionary. Can you find the Python version? The kernel version? The list of mounted filesystems?

### Exercise 3: Run Conditionals

Run the conditionals playbook:

```bash
ansible-navigator run playbooks/module-04/conditionals.yml --mode stdout
```

Observe which tasks are executed and which are skipped. The output depends on your system -- on a Fedora system, the Red Hat family tasks will execute and the Debian tasks will be skipped (and vice versa on Ubuntu).

### Exercise 4: Add Your Own Variables

Create a file `ansible/inventory/group_vars/webservers.yml` (if you have not already done so from Module 3's exercises) with web-server-specific variables:

```yaml
---
parasol_http_port: 8080
parasol_max_connections: 1000
parasol_document_root: "/var/www/html"
```

Then create a short playbook that displays these variables for a web server host. Use `--limit` to target a specific host and see the merged variable set.

### Exercise 5: Combine Facts and Variables

Write a playbook that:

1. Gathers facts
2. Uses `set_fact` to compute a variable (for example, `parasol_app_memory_limit` as 50% of `ansible_facts['memtotal_mb']`)
3. Displays the computed value with `ansible.builtin.debug`
4. Uses `when` to print a warning if the computed value is below a threshold

This exercise combines everything from this module: facts, `set_fact`, `debug` with `verbosity`, and `when`.

## Summary

In this module you:

- Learned where to define variables (role defaults, inventory, play vars, extra vars) and why scope matters
- Explored the variable precedence chain and proved that extra vars always win
- Accessed system facts using `ansible_facts['key']` bracket notation
- Used `gather_subset` to collect only the facts you need
- Captured task output with `register` and computed values with `set_fact`
- Debugged variables using `ansible.builtin.debug` with `verbosity` and `ansible-navigator` interactive mode
- Used `when` to conditionally execute tasks based on facts, variables, and registered results

Lionel and Jordan now have the tools to write playbooks that adapt to any environment. The same playbook reads different values from `group_vars/dev.yml` and `group_vars/production.yml`, makes decisions based on system facts, and computes values at runtime. No more hardcoded configuration.

## Next Steps

Next: [Module 5 -- Templates and Handlers](5-templates-and-handlers.md)
