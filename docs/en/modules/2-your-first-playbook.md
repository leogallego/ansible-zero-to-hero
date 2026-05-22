# Module 2: Your First Playbook

## Learning Objectives

By the end of this module you will be able to:

- Describe the anatomy of a playbook (plays, tasks, modules)
- Write and run a simple playbook
- Use `ansible-navigator` to run and inspect playbook runs
- Explain idempotency and verify it with check mode and diff mode

## The Story So Far

Lionel has run a few ad-hoc commands and sees the potential. But one-off commands aren't repeatable -- if Lionel needs to install the same three packages on a new server next month, the exact commands will have to be recalled from memory or a wiki page. What's needed is a way to define a set of tasks once and run them reliably, every time.

It's time to write a playbook.

## Playbook Anatomy

A **playbook** is a YAML file that describes the desired state of one or more systems. It is the fundamental unit of reusable automation in Ansible.

A playbook contains one or more **plays**. Each play targets a set of hosts and defines an ordered list of **tasks** to execute on those hosts. Each task calls a **module** -- the same modules you used with ad-hoc commands in Module 1.

Here is the structure at a glance:

```text
Playbook (YAML file)
  └── Play 1
  │     ├── hosts: which machines to target
  │     ├── become: whether to escalate privileges
  │     └── tasks:
  │           ├── Task 1 → calls a module
  │           ├── Task 2 → calls a module
  │           └── Task 3 → calls a module
  └── Play 2
        ├── hosts: a different set of machines
        └── tasks:
              └── Task 1 → calls a module
```

Key terminology:

| Term | Definition |
|------|-----------|
| **Playbook** | A YAML file containing one or more plays |
| **Play** | A mapping of hosts to tasks -- "on these hosts, do these things" |
| **Task** | A single action that calls a module with specific parameters |
| **Module** | A unit of code that performs a specific operation (install a package, copy a file, manage a service) |

!!! info "One play vs. many plays"
    Simple playbooks often contain a single play. As your automation grows, you will use multiple plays to target different host groups in the same playbook -- for example, one play to configure the database server and another to configure the web servers.

## YAML Basics for Ansible

Ansible playbooks are written in YAML (YAML Ain't Markup Language). If you have never worked with YAML before, here are the essentials you need for Ansible.

### Indentation

YAML uses indentation to represent structure -- like Python, but with **spaces only, never tabs**. Ansible uses **2-space indentation** by convention.

```yaml
# Correct: 2-space indentation
- name: Install packages
  ansible.builtin.package:
    name: curl
    state: present
```

```yaml
# Wrong: inconsistent indentation will cause a syntax error
- name: Install packages
   ansible.builtin.package:
      name: curl
```

### Lists

Lists use a dash followed by a space (`- `). List items are indented under their parent key:

```yaml
# A list of packages
name:
  - tree
  - curl
  - jq
```

### Strings

Most strings in YAML do not need quotes. Use quotes when a value contains special characters or could be misinterpreted:

```yaml
# No quotes needed
name: Install packages

# Quotes needed: the colon would confuse the parser
message: "Status: completed"
```

### Booleans

YAML supports several boolean forms, but in Ansible we always use lowercase `true` and `false`:

```yaml
# Correct
become: true
enabled: false

# Wrong -- do not use these forms
become: yes
enabled: No
become: True
```

!!! warning "Always use `true`/`false`"
    YAML accepts `yes`, `no`, `True`, `False`, and other variants as booleans. Ansible will understand them, but `ansible-lint` will flag anything other than `true`/`false`. Be consistent from the start.

### Documents

A YAML file starts with three dashes (`---`). This marks the beginning of a YAML document:

```yaml
---
- name: My first play
  hosts: localhost
  tasks: []
```

The `---` is optional but considered good practice. You will see it at the top of every playbook in this course.

## Writing Your First Playbook

Let's walk through a real playbook line by line. Open the file `ansible/playbooks/module-02/install-packages.yml`:

```yaml
---
# Module 2 - Install common packages on localhost
# This playbook demonstrates the ansible.builtin.package module
# to install packages in a distribution-agnostic way.

- name: Install common utility packages
  hosts: localhost
  connection: local
  become: true

  tasks:
    - name: Install utility packages
      ansible.builtin.package:
        name:
          - tree
          - curl
          - jq
        state: present
```

Here is what each part does:

**`---`** -- marks the start of the YAML document.

**`# Module 2 - ...`** -- comments. YAML comments start with `#` and are ignored by Ansible.

**`- name: Install common utility packages`** -- the start of a **play**. The dash indicates this is the first item in a list (a playbook is a list of plays). The `name` gives the play a human-readable description that appears in the output when you run it.

**`hosts: localhost`** -- tells Ansible which hosts this play targets. Here we target only `localhost` -- the machine we are working on.

**`connection: local`** -- tells Ansible to run tasks directly on the local machine instead of connecting over SSH. This is what you want when targeting localhost.

**`become: true`** -- tells Ansible to escalate privileges (equivalent to `sudo`). Installing packages requires root access, so we need this.

**`tasks:`** -- begins the list of tasks for this play.

**`- name: Install utility packages`** -- the start of a **task**. Every task should have a descriptive name in imperative form -- it tells you what the task does when you read the output.

**`ansible.builtin.package:`** -- the **module** this task uses. `ansible.builtin.package` is a generic package manager module that works across different Linux distributions (it calls `dnf` on Fedora/RHEL, `apt` on Debian/Ubuntu, and so on). Notice we use the Fully Qualified Collection Name.

**`name:` (under the module)** -- a parameter of the `package` module specifying which packages to install. We pass a list of three packages.

**`state: present`** -- another module parameter. `present` means "make sure these packages are installed". If they are already installed, Ansible does nothing. If they are missing, Ansible installs them.

!!! tip "Why `ansible.builtin.package` instead of `ansible.builtin.dnf`?"
    The `package` module automatically detects the system's package manager and calls the right one. This makes your playbook portable across distributions. Use distribution-specific modules (`dnf`, `apt`) only when you need features specific to that package manager.

### The Other Companion Playbooks

The `ansible/playbooks/module-02/` directory contains two more playbooks for practice:

**`create-files.yml`** -- demonstrates creating directories and files:

```yaml
---
- name: Create directories and files
  hosts: localhost
  connection: local

  tasks:
    - name: Create project directory
      ansible.builtin.file:
        path: /tmp/ansible-demo
        state: directory
        mode: "0755"

    - name: Create logs subdirectory
      ansible.builtin.file:
        path: /tmp/ansible-demo/logs
        state: directory
        mode: "0755"

    - name: Create a welcome file
      ansible.builtin.copy:
        dest: /tmp/ansible-demo/README.txt
        content: |
          Welcome to Ansible!
          This file was created by an Ansible playbook.
        mode: "0644"

    - name: Create an application config file
      ansible.builtin.copy:
        dest: /tmp/ansible-demo/app.conf
        content: |
          # Application configuration
          app_name=demo
          log_level=info
          log_dir=/tmp/ansible-demo/logs
        mode: "0644"
```

Notice that this playbook does not use `become: true` -- creating files in `/tmp` does not require root privileges.

The `ansible.builtin.file` module manages files and directories. With `state: directory`, it creates a directory. The `ansible.builtin.copy` module creates files with specific content using the `content` parameter.

**`manage-service.yml`** -- demonstrates managing system services:

```yaml
---
- name: Manage the chronyd service
  hosts: localhost
  connection: local
  become: true

  tasks:
    - name: Ensure chronyd is installed
      ansible.builtin.package:
        name: chrony
        state: present

    - name: Ensure chronyd is started and enabled
      ansible.builtin.service:
        name: chronyd
        state: started
        enabled: true
```

The `ansible.builtin.service` module manages system services. `state: started` ensures the service is running, and `enabled: true` ensures it starts automatically on boot.

!!! warning "Container limitations"
    The `manage-service.yml` playbook requires `systemd` to be running, which is not the case in most containers. If you are working in the devcontainer, this playbook will fail with an error about the service manager. That is expected -- this playbook is designed to work on a virtual machine or bare-metal system. You can still read through it and understand the concepts. The `install-packages.yml` and `create-files.yml` playbooks will work in the devcontainer.

## Running Playbooks with ansible-navigator

In Module 1 you ran ad-hoc commands with `ansible`. For playbooks, we will use **`ansible-navigator`** -- a tool that provides a rich text user interface (TUI) for running and inspecting Ansible content.

### Why ansible-navigator?

`ansible-navigator` replaces the older `ansible-playbook` command and adds:

- An interactive TUI for exploring play and task results
- The ability to run playbooks inside Execution Environments (container images with all dependencies bundled)
- A standard way to inspect automation content

You can still use `ansible-playbook` directly, and `ansible-navigator` calls it under the hood, but the TUI makes it much easier to explore results.

### Running a Playbook

Navigate to the `ansible/` directory (where `ansible.cfg` lives) and run:

```bash
cd ansible
ansible-navigator run playbooks/module-02/install-packages.yml --mode stdout
```

The `--mode stdout` flag runs the playbook in standard output mode -- the output goes directly to your terminal, similar to `ansible-playbook`. This is the simplest way to run a playbook.

You should see output like this:

```text
PLAY [Install common utility packages] ****************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [Install utility packages] ************************************************
changed: [localhost]

PLAY RECAP *********************************************************************
localhost                  : ok=2    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Let's break down the output:

- **PLAY** -- shows the play name from your playbook
- **TASK [Gathering Facts]** -- Ansible automatically collects system information before running your tasks (you saw this with `ansible.builtin.setup` in Module 1). This is a default behavior that can be disabled.
- **TASK [Install utility packages]** -- your task ran and reports `changed`, meaning the packages were installed
- **PLAY RECAP** -- a summary showing how many tasks succeeded (`ok`), how many made changes (`changed`), and whether any failed

### Interactive TUI Mode

Now try running a playbook in interactive mode:

```bash
ansible-navigator run playbooks/module-02/create-files.yml
```

Without `--mode stdout`, `ansible-navigator` opens its TUI. You will see a screen showing the play results. From here you can:

- Press a number key to drill into a specific play or task
- Press ++esc++ to go back to the previous screen
- Press ++d++ to view the task documentation
- Press ++0++ to inspect the first (and only) play

!!! tip "Navigating the TUI"
    The TUI is a powerful exploration tool. Drill into a task to see its exact input parameters, the module output, and whether it made changes. Use it to debug when something does not behave as expected.

When you are done exploring, press ++esc++ until you exit back to your terminal, or press ++colon++ and type `quit`.

### stdout vs. interactive mode

| Mode | Command | Best For |
|------|---------|----------|
| stdout | `--mode stdout` | CI/CD pipelines, quick runs, scripting |
| interactive | (default) | Exploring results, debugging, learning |

Throughout this course we will use both modes. When showing output in the module text, we use `--mode stdout` for clarity. When you run exercises on your own, try the interactive mode to explore.

## Check Mode and Diff Mode

Before running a playbook on a real system, you often want to preview what it *would* do without actually making changes. Ansible provides two flags for this.

### Check Mode (`--check`)

Check mode is a dry run. Ansible goes through all the tasks and reports what *would* change, but does not actually apply any changes:

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout --check
```

```text
PLAY [Create directories and files] ********************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [Create project directory] ************************************************
changed: [localhost]

TASK [Create logs subdirectory] ************************************************
changed: [localhost]

TASK [Create a welcome file] ***************************************************
changed: [localhost]

TASK [Create an application config file] ***************************************
changed: [localhost]

PLAY RECAP *********************************************************************
localhost                  : ok=5    changed=4    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

The output shows `changed` for each task -- but nothing was actually changed on the system. Check mode tells you "these tasks *would* make changes if you ran them for real."

!!! info "Not all modules support check mode"
    Most Ansible modules support check mode, but some (particularly `ansible.builtin.command` and `ansible.builtin.shell`) do not by default because Ansible cannot predict what an arbitrary command would do. Well-designed modules report accurately in check mode.

### Diff Mode (`--diff`)

Diff mode shows the exact differences that would be (or were) applied. It is most useful with file-related modules:

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout --diff
```

When a file is created or modified, the output includes a diff showing the before and after:

```text
TASK [Create a welcome file] ***************************************************
--- before
+++ after: /tmp/ansible-demo/README.txt
@@ -0,0 +1,2 @@
+Welcome to Ansible!
+This file was created by an Ansible playbook.

changed: [localhost]
```

### Combining Check and Diff

The most powerful preview combines both flags:

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout --check --diff
```

This shows you exactly what *would* change without making any changes -- the safest way to preview your automation before applying it to production systems.

## Understanding Idempotency

**Idempotency** is the most important concept in Ansible. An operation is idempotent if running it multiple times produces the same result as running it once.

### Seeing Idempotency in Action

Run the `create-files.yml` playbook twice:

**First run:**

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout
```

```text
PLAY RECAP *********************************************************************
localhost                  : ok=5    changed=4    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Four tasks reported `changed` -- the directories and files were created.

**Second run (same command):**

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout
```

```text
PLAY RECAP *********************************************************************
localhost                  : ok=5    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Zero changes the second time. The directories and files already exist with the correct content and permissions, so Ansible has nothing to do. Every task reports `ok` instead of `changed`.

### Why Idempotency Matters

Idempotency means:

- **Safe re-runs** -- you can run a playbook as many times as you want without breaking anything. If a playbook run is interrupted halfway, just run it again.
- **Drift detection** -- if someone manually changes a file that Ansible manages, the next playbook run will put it back to the desired state and report `changed`.
- **Confidence** -- you know exactly what state your systems are in because the playbook defines the desired state and Ansible enforces it.

This is fundamentally different from shell scripts. A script that runs `mkdir /tmp/ansible-demo` will fail on the second run because the directory already exists. The `ansible.builtin.file` module with `state: directory` checks if the directory exists first and only creates it if needed.

!!! tip "changed=0 is the goal"
    When you run a playbook against a system that is already in the desired state, the ideal result is `changed=0`. This confirms that your automation is accurate and the system matches the declared state. If you see unexpected changes on a re-run, investigate -- something is either changing the system outside of Ansible, or a task is not truly idempotent.

## Exercises

### Exercise 1: Run the install-packages playbook

Navigate to the `ansible/` directory and run:

```bash
ansible-navigator run playbooks/module-02/install-packages.yml --mode stdout
```

Observe the output. Then run it again and confirm that the second run shows `changed=0`.

### Exercise 2: Explore with the TUI

Run the `create-files.yml` playbook in interactive mode:

```bash
ansible-navigator run playbooks/module-02/create-files.yml
```

Navigate the TUI: drill into a task, examine the module parameters and results, then exit.

### Exercise 3: Preview with check and diff

Run the `create-files.yml` playbook with both `--check` and `--diff`:

```bash
ansible-navigator run playbooks/module-02/create-files.yml --mode stdout --check --diff
```

If you have already run the playbook once, the output should show `changed=0` in check mode -- the files already exist. Delete the `/tmp/ansible-demo` directory (`rm -rf /tmp/ansible-demo`) and run the check+diff command again to see what Ansible *would* create.

### Exercise 4: Write your own playbook

Create a new playbook called `ansible/playbooks/module-02/my-playbook.yml` that:

1. Creates a directory at `/tmp/my-project`
2. Creates a file at `/tmp/my-project/hello.txt` with content of your choice
3. Creates a subdirectory at `/tmp/my-project/data`

Run it, verify the files were created, then run it again to confirm idempotency.

## Summary

In this module you:

- Learned the anatomy of a playbook: plays contain tasks, and tasks call modules
- Covered the YAML basics needed for writing playbooks (indentation, lists, booleans, strings)
- Walked through a complete playbook line by line
- Ran playbooks with `ansible-navigator` in both stdout and interactive TUI modes
- Used check mode (`--check`) and diff mode (`--diff`) to preview changes safely
- Observed idempotency in action -- running a playbook twice produces zero changes the second time

Lionel now has three playbooks that can be run repeatedly to achieve a consistent system state. But all of them target `localhost` -- what happens when Lionel needs to manage multiple servers across different environments?

## Next Steps

Next: [Module 3 -- Managing Inventory](3-managing-inventory.md)
