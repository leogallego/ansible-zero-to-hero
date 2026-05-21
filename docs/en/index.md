# Ansible Zero to Hero

Welcome to the Ansible Zero to Hero course! This progressive course teaches Ansible from first principles to production-grade automation.

## The Story

You'll follow **Alex**, a platform engineer at **Parasol Tech**, as they discover Ansible to automate repetitive infrastructure tasks, then gradually scale the practice across the division.

## Modules

| # | Module | What You'll Learn |
|---|--------|-------------------|
| 1 | [Introduction to Ansible](modules/1-introduction.md) | Environment setup, ad-hoc commands |
| 2 | [Your First Playbook](modules/2-your-first-playbook.md) | Playbook anatomy, idempotency |
| 3 | [Managing Inventory](modules/3-managing-inventory.md) | Structured inventory, groups |
| 4 | [Variables and Facts](modules/4-variables-and-facts.md) | Precedence, facts, conditionals |
| 5 | [Templates and Handlers](modules/5-templates-and-handlers.md) | Jinja2 templates, handlers |
| 6 | [Roles and Collections](modules/6-roles-and-collections.md) | Code reuse, Galaxy, `ansible-creator` |
| 7 | [Testing Your Automation](modules/7-testing-your-automation.md) | Molecule, linting, pytest |
| 8 | [Packaging and Deployment](modules/8-packaging-and-deployment.md) | Execution Environments, signing |
| 9 | [Scaling with AAP](modules/9-scaling-with-aap.md) | Controller, workflows, RBAC |

## Prerequisites

- Comfortable with the Linux command line (navigating directories, editing files, running commands)
- No prior Ansible experience required

## Lab Environment

Choose your environment:

=== "Local Devcontainer"

    Requires VS Code and Docker or Podman. Clone the repo and open in the devcontainer — everything is pre-installed.

=== "Red Hat Devtools Sandbox"

    Browser-based environment with all tools pre-installed. No local setup needed.

See [Module 1](modules/1-introduction.md) for detailed setup instructions.
