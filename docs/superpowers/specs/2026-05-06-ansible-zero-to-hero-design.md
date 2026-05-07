# Ansible Zero to Hero Course Design

## Overview

A progressive, modular course teaching Ansible from first principles to production-grade automation, following the format established by the NetBox Zero to Hero course. The course integrates Ansible Development Tools (`adt`) throughout, drawing from the Red Hat Summit devtools workshop content.

## Narrative: Parasol Tech

**Parasol Tech** is the platform infrastructure and cloud provider division of **Parasol Insurance Corp.** The story follows **Alex**, a platform engineer who discovers Ansible to automate repetitive infrastructure tasks, then gradually scales the practice across the division.

| Phase | Modules | Narrative Arc |
|-------|---------|---------------|
| Solo dev | 1-3 | Alex discovers Ansible, writes first playbooks, manages inventory |
| Small team | 4-5 | Team adopts Ansible — variables, templates, and handlers for shared work |
| Structured team | 6-7 | Community of Practice (CoP) forms — roles, collections, testing, code reuse |
| Mature practice | 8-9 | Production packaging, content signing, and scaling with AAP |
| Domain tracks | 10+ | Teams specialize — optional capstone modules for specific domains |

## Target Audience

Mixed / progressive. Starts beginner-friendly (comfortable with Linux CLI but new to Ansible) and ramps up to intermediate/advanced topics by the end.

## Module Outline

### Module 1: Introduction to Ansible

**Narrative**: Alex, a Parasol Tech platform engineer, spends hours doing the same manual server setup tasks. They discover Ansible.

**Topics**:
- What is Ansible and why automation matters
- Ansible Development Tools (`adt`) overview — the bundled CLI suite
- Environment setup (Red Hat devtools sandbox OR local devcontainer)
- Installing Ansible, verifying the environment (`adt --version`)
- First ad-hoc commands against localhost
- Understanding modules and the module index

**Dev tools introduced**: `adt` (overview), development environment setup

**Companion code**: Setup playbooks/scripts for both sandbox and devcontainer environments

### Module 2: Your First Playbook

**Narrative**: Alex moves from one-off ad-hoc commands to repeatable playbooks.

**Topics**:
- Playbook anatomy: plays, tasks, modules
- YAML basics for Ansible (indentation, booleans, lists)
- Writing and running a first playbook
- Running playbooks with `ansible-navigator` (TUI mode)
- Check mode and diff mode
- Understanding idempotency

**Dev tools introduced**: `ansible-navigator` for running and inspecting playbook runs

**Companion code**: Simple playbooks (install packages, create files, manage services)

### Module 3: Managing Inventory

**Narrative**: Alex needs to manage more than localhost — multiple servers across environments.

**Topics**:
- Static inventory files (INI and YAML formats)
- Groups and nested groups
- Host variables and group variables (`host_vars/`, `group_vars/`)
- Structured inventory directories vs single-file inventories
- Targeting hosts with patterns and `--limit`
- Introduction to dynamic inventory concepts

**Companion code**: Structured inventory directory with dev/staging/prod groups

### Module 4: Variables and Facts

**Narrative**: Alex's teammate joins and they need to parameterize playbooks for different environments.

**Topics**:
- Variable types and where to define them
- Variable precedence (defaults -> inventory -> role vars -> extra vars)
- Ansible facts and `ansible_facts[]` bracket notation
- Gathering facts, minimal fact subsets
- Registered variables and `set_fact`
- Debugging with `ansible.builtin.debug` (with `verbosity:`)
- Inspecting variables with `ansible-navigator`

**Companion code**: Playbooks demonstrating variable precedence, fact usage, conditional logic

### Module 5: Templates and Handlers

**Narrative**: The team needs to generate configuration files for services and restart them when configs change.

**Topics**:
- Jinja2 template basics (variables, filters, loops, conditionals)
- The `template` module and `{{ ansible_managed | comment }}`
- Using `backup: true` for safe file deployment
- Handlers and `notify` chains
- When handlers run (end of play, `meta: flush_handlers`)
- Template best practices (no timestamps, no dates)

**Companion code**: Templates for nginx/apache configs, systemd units; playbooks with handler chains

### Module 6: Roles and Collections

**Narrative**: The CoP forms at Parasol Tech. Teams need reusable, shareable automation units.

**Topics**:
- Role directory structure and conventions
- `defaults/main.yml` vs `vars/main.yml` — when to use each
- Role naming conventions (prefix everything with role name)
- Argument validation with `meta/argument_specs.yml`
- Scaffolding roles and collections with `ansible-creator`
- Managing dev environments with `ade` (install, dependency trees)
- Ansible Galaxy — installing and publishing collections
- Fully Qualified Collection Names (FQCNs)
- Semantic versioning for collections

**Dev tools introduced**: `ansible-creator` (scaffolding), `ade` (dependency management)

**Companion code**: A scaffolded collection with roles, `galaxy.yml`, argument specs

### Module 7: Testing Your Automation

**Narrative**: The CoP establishes quality gates — no untested automation goes to production.

**Topics**:
- `ansible-lint` — static analysis, rule categories, auto-fix on save
- Molecule — integration testing lifecycle (dependency, create, converge, verify, destroy)
- Writing Molecule scenarios and assertion-based tests
- `pytest-ansible` — functional testing of modules and plugins
- `tox-ansible` — orchestrating test matrices
- The test pyramid for Ansible: lint -> unit -> integration

**Dev tools introduced**: `ansible-lint`, `molecule`, `pytest-ansible`, `tox-ansible`

**Companion code**: Molecule scenarios, pytest test files, tox configuration, lint config

### Module 8: Packaging and Deployment

**Narrative**: Parasol Tech needs to package automation for production — repeatable, signed, and portable.

**Topics**:
- Execution Environments (EEs) — what they are and why they matter
- Defining `execution-environment.yml` (version 3)
- Building EEs with `ansible-builder`
- Testing EEs with `podman` and `ansible-navigator`
- Content signing with `ansible-sign` (GPG keys, MANIFEST.in, sign/verify)
- Supply chain security workflow: sign -> push -> AAP verifies
- Publishing collections to Automation Hub

**Dev tools introduced**: `ansible-builder`, `ansible-sign`

**Companion code**: EE definition files, build scripts, signing examples

### Module 9: Scaling with AAP

**Narrative**: Parasol Tech's automation outgrows CLI execution. The CoP needs governance, RBAC, and centralized orchestration.

**Topics**:
- Ansible Automation Platform overview (Controller, Hub, EDA)
- From `ansible-playbook` to Controller job templates
- Inventories and credentials in Controller
- Workflows — chaining job templates
- RBAC — teams, roles, permissions
- EE integration with Controller
- Project sync and content verification

**Companion code**: Example job template configs, workflow definitions, inventory source configs

### Module 10: [Track] Linux Systems (Optional)

**Narrative**: The Linux platform team at Parasol Tech applies everything they've learned.

**Topics**:
- User and group management at scale
- Package management across distributions (platform-specific variables pattern)
- Service management and systemd units
- Security hardening (firewall, SELinux, SSH)
- Patching and compliance workflows

**Companion code**: Roles for user management, hardening, patching

### Module 11: [Track] Network Automation (Optional)

**Narrative**: The network team at Parasol Tech joins the CoP.

**Topics**:
- Network modules and `network_cli` connection plugin
- Network facts and resource modules
- Config backup and restore patterns
- Network-specific testing considerations
- Integration with NetBox as source of truth (ties back to the NetBox Zero to Hero course)

**Companion code**: Playbooks for network device management, backup roles

## Repository Structure

```
ansible-zero-to-hero/
  README.md
  CLAUDE.md
  CNAME
  .gitignore
  modules/
    1-introduction/
      1-introduction.md
    2-your-first-playbook/
      2-your-first-playbook.md
    3-managing-inventory/
      3-managing-inventory.md
    4-variables-and-facts/
      4-variables-and-facts.md
    5-templates-and-handlers/
      5-templates-and-handlers.md
    6-roles-and-collections/
      6-roles-and-collections.md
    7-testing-your-automation/
      7-testing-your-automation.md
    8-packaging-and-deployment/
      8-packaging-and-deployment.md
    9-scaling-with-aap/
      9-scaling-with-aap.md
    10-linux-systems/
      10-linux-systems.md
    11-network-automation/
      11-network-automation.md
  ansible/
    ansible.cfg
    inventory/
      hosts.yml
      group_vars/
      host_vars/
    playbooks/
      module-02/
      module-03/
      module-04/
      module-05/
    roles/
    collections/
    templates/
    molecule/
    execution-environments/
  images/
  _includes/
```

### Key structural decisions

- **Module content** lives in `modules/` as markdown files (one per module), mirroring the NetBox course
- **Companion code** lives in `ansible/` organized by module when specific to a module, or at the top level when shared
- **Inventory** uses structured directory format from the start (the right way)
- **Roles and collections** get scaffolded progressively — module 6 creates the first collection inside `ansible/collections/` using `ansible-creator`
- **Domain track companion code** (modules 10-11) is optional and self-contained — learners who skip tracks don't miss prerequisites
- **No Postman/Python scripts directory** — this course is Ansible-native throughout

## Lab Environment

The course supports two environments:

1. **Red Hat devtools sandbox** — OpenShift Dev Spaces (Che-Code) with `adt` pre-installed, AAP available as a web service, cloud integrations available
2. **Local devcontainer** — VS Code devcontainer with `adt` installed, Podman/Docker for containers, optional local VMs

Setup playbooks/scripts are provided for both paths. The companion code is written to be environment-agnostic — inventory targets and connection methods are parameterized.

## Module Content Format

Each module follows a consistent structure (mirroring NetBox course):

1. **Learning objectives** — bullet list of what the learner will be able to do
2. **Narrative context** — what's happening at Parasol Tech that motivates this module
3. **Conceptual content** — explanations, diagrams, key concepts
4. **Hands-on exercises** — step-by-step instructions with companion code
5. **Summary** — what was covered
6. **Next steps** — link to next module

## Dev Tools Integration Map

| Tool | First Introduced | Continued Use |
|------|-----------------|---------------|
| `adt` | Module 1 (overview, version check) | Throughout |
| `ansible-navigator` | Module 2 (running playbooks) | Modules 4, 8 |
| `ansible-creator` | Module 6 (scaffolding roles/collections) | Module 8 |
| `ade` | Module 6 (dev environment management) | Module 7 |
| `ansible-lint` | Module 7 (static analysis) | Throughout after |
| `molecule` | Module 7 (integration testing) | Module 10, 11 |
| `pytest-ansible` | Module 7 (functional testing) | — |
| `tox-ansible` | Module 7 (test orchestration) | — |
| `ansible-builder` | Module 8 (EE creation) | Module 9 |
| `ansible-sign` | Module 8 (content signing) | Module 9 |

## Cross-references

- Module 11 (Network Automation) references the **NetBox Zero to Hero** course as a companion for source-of-truth integration
- The devtools workshop content from `summit-devtools-lb2236` informs modules 6, 7, and 8 — specifically the `ansible-creator`, `ade`, `molecule`, `pytest-ansible`, `ansible-builder`, and `ansible-sign` workflows
