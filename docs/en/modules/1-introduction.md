# Module 1: Introduction to Ansible

## Learning Objectives

By the end of this module you will be able to:

- Explain what Ansible is and why automation matters
- Set up your development environment (devcontainer or Red Hat sandbox)
- Verify your Ansible Development Tools installation
- Run ad-hoc commands against localhost
- Navigate the Ansible module index

## The Story So Far

Lionel is a platform engineer at **Parasol Tech**, the infrastructure division of Parasol Insurance Corp. Every week, Lionel spends hours repeating the same tasks: provisioning servers, installing packages, configuring services, and verifying that everything is consistent across environments. The work is tedious, error-prone, and impossible to scale.

One afternoon, a colleague drops by Lionel's desk. "You're still doing all of that by hand? You should look into Ansible." That evening, Lionel opens a terminal and starts exploring.

This is where your journey begins too.

## What is Ansible?

Ansible is an open source automation engine that lets you describe the desired state of your systems and then makes it happen. Instead of writing scripts that execute step-by-step commands, you declare *what* the system should look like, and Ansible figures out *how* to get there.

Four properties make Ansible stand out:

**Agentless**: Ansible does not require any software to be installed on the machines it manages. It connects over standard SSH (or WinRM for Windows) and executes tasks remotely. No daemons, no agents, no extra infrastructure.

**Declarative**: You describe the desired state ("this package should be installed", "this service should be running") rather than the steps to get there. Ansible modules handle the implementation details.

**Idempotent**: Running the same automation twice produces the same result. If a package is already installed, Ansible skips the step. If a file already has the right content, Ansible leaves it alone. This means you can safely re-run your automation without fear of breaking things.

**Simple**: Ansible uses YAML for its configuration language. If you can read a YAML file, you can read an Ansible playbook. There is no custom programming language to learn.

!!! info "How Ansible connects"
    For Linux/Unix targets, Ansible uses SSH. It copies small Python programs (called modules) to the remote host, executes them, collects the results, and cleans up. The managed host only needs Python and SSH -- nothing else.

## Why Automation?

Lionel's manual workflow has several problems that automation solves:

| Manual Approach | With Automation |
|----------------|-----------------|
| Steps live in Lionel's head or a wiki that gets outdated | The playbook *is* the documentation, always current |
| Each server is configured slightly differently | Every server gets the exact same configuration |
| Takes 45 minutes per server | Takes seconds, runs in parallel across dozens of servers |
| Mistakes are discovered days later in production | Check mode catches issues before they happen |
| Only Lionel knows how to do it | Anyone on the team can read and run the playbook |

Automation turns tribal knowledge into code that can be versioned, reviewed, tested, and shared. When Lionel writes a playbook, it becomes a living document that describes exactly how Parasol Tech's infrastructure is configured.

## Ansible Development Tools (adt)

Red Hat provides a bundled suite of command-line tools called **Ansible Development Tools** (`adt`). Think of `adt` as the complete toolbox for developing, testing, and packaging Ansible content. You will use many of these tools throughout the course.

Here is what the bundle includes:

| Tool | Purpose | First Used |
|------|---------|------------|
| `ansible-core` | The core engine: `ansible-playbook`, `ansible-galaxy`, ad-hoc commands | This module |
| `ansible-navigator` | TUI for running and inspecting playbook runs | Module 2 |
| `ansible-creator` | Scaffolding for roles, collections, and playbook projects | Module 6 |
| `ade` | Development environment management (install, dependency trees) | Module 6 |
| `ansible-lint` | Static analysis and auto-fix for Ansible content | Module 7 |
| `molecule` | Integration testing for roles and collections | Module 7 |
| `pytest-ansible` | Functional testing of modules and plugins | Module 7 |
| `tox-ansible` | Test orchestration and matrix management | Module 7 |
| `ansible-builder` | Execution Environment (container image) creation | Module 8 |
| `ansible-sign` | Content signing for supply chain security | Module 8 |

!!! tip "You don't need to memorize this"
    You will learn each tool when it becomes relevant in the course. For now, just know that `adt` installs everything you need in one shot.

## Setting Up Your Environment

You have two options for your lab environment. Both give you the same tools; choose whichever fits your workflow.

=== "Local Devcontainer"

    The repository includes a devcontainer configuration that sets up a complete development environment inside a container.

    **Prerequisites:**

    - [VS Code](https://code.visualstudio.com/) with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
    - [Docker](https://www.docker.com/) or [Podman](https://podman.io/) installed and running

    **Steps:**

    1. Clone the course repository:

        ```bash
        git clone https://github.com/leogallego/ansible-zero-to-hero.git
        cd ansible-zero-to-hero
        ```

    2. Open the folder in VS Code:

        ```bash
        code .
        ```

    3. When VS Code detects the `.devcontainer/` directory, it will prompt you to reopen in the container. Click **Reopen in Container**.

        Alternatively, open the command palette (++ctrl+shift+p++) and select **Dev Containers: Reopen in Container**.

    4. Wait for the container to build. This takes a few minutes the first time as it pulls the community development image.

    5. Once the container is ready, you will have a terminal inside VS Code with `adt` and all Ansible tools available.

    !!! note "What the devcontainer includes"
        The devcontainer uses `ghcr.io/ansible/community-ansible-dev-tools:latest`, a community-maintained container image with the full `adt` suite pre-installed. It includes `ansible-dev-tools` (the full `adt` bundle) and `podman` (for building Execution Environments later). Under the hood, `ansible-creator` is the tool that generates `.devcontainer/` configurations for Ansible projects.

=== "Red Hat Devtools Sandbox"

    The [Red Hat Developer Sandbox](https://developers.redhat.com/products/ansible/getting-started) provides a browser-based development environment with `adt` pre-installed. No local setup is needed.

    **Steps:**

    1. Go to [developers.redhat.com/products/ansible/getting-started](https://developers.redhat.com/products/ansible/getting-started).

    2. Sign in with your Red Hat account (free to create).

    3. Launch the sandbox environment. You will get a browser-based IDE with a terminal.

    4. Clone the course repository inside the sandbox:

        ```bash
        git clone https://github.com/leogallego/ansible-zero-to-hero.git
        cd ansible-zero-to-hero
        ```

    5. All `adt` tools are pre-installed. You can start working immediately.

    !!! note "Sandbox sessions"
        Sandbox sessions may have time limits. Save your work by committing and pushing to your own fork if you need to resume later.

### Verifying Your Environment

Regardless of which option you chose, verify that everything is working. Open a terminal and run:

```bash
adt --version
```

You should see output listing all the tools and their versions:

```text
ansible-builder                          3.1.1
ansible-core                             2.20.5
ansible-creator                          26.4.3
ansible-dev-environment                  26.4.0
ansible-dev-tools                        26.4.6
ansible-lint                             26.4.0
ansible-navigator                        26.4.0
ansible-sign                             0.1.5
molecule                                 26.4.0
pytest-ansible                           26.4.0
tox-ansible                              26.3.0
```

!!! tip "Version numbers may differ"
    The exact version numbers depend on when you set up your environment. The important thing is that all tools are listed without errors.

Now verify the core tools individually:

```bash
ansible --version
```

```text
ansible [core 2.20.5]
  config file = None
  configured module search path = ['/root/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /usr/local/lib/python3.13/site-packages/ansible
  ansible collection location = /root/.ansible/collections:/usr/share/ansible/collections
  executable location = /usr/local/bin/ansible
  python version = 3.13.13 (main, Apr  8 2026, 00:00:00) [GCC 15.2.1 20260123 (Red Hat 15.2.1-7)] (/usr/bin/python3)
  jinja version = 3.1.6
  pyyaml version = 6.0.3 (with libyaml v0.2.5)
```

```bash
python3 --version
```

```text
Python 3.13.13
```

If all three commands run without errors, your environment is ready.

## Your First Ad-Hoc Commands

An **ad-hoc command** is a one-liner that runs a single Ansible module against one or more hosts. It is the quickest way to do something with Ansible (no playbook needed).

The general syntax is:

```bash
ansible <host-pattern> -m <module> -a "<module-arguments>"
```

Let's try a few commands against `localhost`, the machine you are working on.

### Ping

The `ansible.builtin.ping` module is not an ICMP ping. It verifies that Ansible can connect to the target and that Python is available:

```bash
ansible localhost -m ansible.builtin.ping
```

```text
localhost | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

Two things to notice:

- **`changed: false`**: the ping module does not modify anything, so it reports no changes. This is idempotency in action.
- **`ping: pong`**: the module ran successfully and returned a result.

### Gather Facts

The `ansible.builtin.setup` module collects detailed information (called **facts**) about the target system: OS, network, memory, CPU, and much more:

```bash
ansible localhost -m ansible.builtin.setup
```

The output is long. Here is a small excerpt:

```json
localhost | SUCCESS => {
    "ansible_facts": {
        "ansible_distribution": "Fedora",
        "ansible_distribution_version": "42",
        "ansible_hostname": "ansible-dev-container",
        "ansible_os_family": "RedHat",
        "ansible_python_version": "3.13.13",
        ...
    }
}
```

!!! tip "Filtering facts"
    You can filter the output to show only specific facts: `ansible localhost -m ansible.builtin.setup -a "filter=ansible_distribution*"`. This is handy when you need just one piece of information.

### Run a Command

The `ansible.builtin.command` module runs a shell command on the target:

```bash
ansible localhost -m ansible.builtin.command -a "uname -n"
```

```text
localhost | CHANGED => {
    "changed": true,
    "cmd": ["uname", "-n"],
    "rc": 0,
    "stdout": "ansible-dev-container",
    "stdout_lines": ["ansible-dev-container"]
}
```

Notice that `changed` is `true` here. The `command` module always reports changed because it cannot know whether the command actually modified the system. In a playbook, you would add a `changed_when:` clause to make this accurate, but that is a topic for later modules.

!!! warning "command vs shell"
    The `ansible.builtin.command` module does not process the command through a shell, so pipes (`|`), redirects (`>`), and environment variables do not work. If you need shell features, use `ansible.builtin.shell` instead, but prefer `command` when you can because it is safer.

## Understanding Modules

Every ad-hoc command and playbook task in Ansible uses a **module**. A module is a unit of code that Ansible runs on the target host to perform a specific action: install a package, copy a file, start a service, create a user.

Ansible ships with hundreds of built-in modules (the `ansible.builtin` collection), and thousands more are available through community and vendor collections on [Ansible Galaxy](https://galaxy.ansible.com/).

### Fully Qualified Collection Names (FQCNs)

Every module has a **Fully Qualified Collection Name** that uniquely identifies it:

```text
namespace.collection.module_name
```

For example:

| FQCN | What It Does |
|------|-------------|
| `ansible.builtin.copy` | Copies files to remote hosts |
| `ansible.builtin.yum` | Manages packages with yum |
| `ansible.builtin.service` | Manages system services |
| `ansible.builtin.user` | Manages user accounts |
| `ansible.builtin.file` | Manages files and directories |

!!! info "Always use FQCNs"
    You might see older tutorials using short names like `copy` or `yum`. While this still works for built-in modules, it is ambiguous when multiple collections provide modules with the same name. Throughout this course, we will always use the fully qualified name.

### Finding Modules

You can browse the complete list of built-in modules in the [Ansible documentation](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/index.html). To search from the command line:

```bash
ansible-doc -l | grep -i file
```

This lists all modules with "file" in their name or description. To see detailed documentation for a specific module:

```bash
ansible-doc ansible.builtin.copy
```

This shows the module's parameters, examples, and return values, all without leaving your terminal.

## Summary

In this module you:

- Learned that Ansible is agentless, declarative, idempotent, and simple
- Set up your development environment with the full `adt` toolbox
- Verified that all Ansible Development Tools are installed
- Ran ad-hoc commands to ping, gather facts, and execute commands on localhost
- Explored modules and Fully Qualified Collection Names (FQCNs)

Lionel is hooked. Running ad-hoc commands is useful, but doing things one command at a time is not much better than doing them manually. What Lionel needs is a way to define a sequence of tasks and run them repeatedly. That is exactly what playbooks are for.

## Next Steps

Next: [Module 2 -- Your First Playbook](2-your-first-playbook.md)
