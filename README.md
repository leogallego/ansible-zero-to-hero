# Ansible Zero to Hero

A progressive, bilingual course teaching Ansible from first principles to production-grade automation.

Follow **Lionel**, a platform engineer at **Parasol Tech**, as they discover Ansible, build a Community of Practice, and scale automation across the organization.

## Modules

| # | Module | What You'll Learn |
|---|--------|-------------------|
| 1 | [Introduction to Ansible](docs/en/modules/1-introduction.md) | Environment setup, ad-hoc commands, `adt` overview |
| 2 | [Your First Playbook](docs/en/modules/2-your-first-playbook.md) | Playbook anatomy, `ansible-navigator`, idempotency |
| 3 | [Managing Inventory](docs/en/modules/3-managing-inventory.md) | Structured inventory, groups, host/group vars, patterns |
| 4 | [Variables and Facts](docs/en/modules/4-variables-and-facts.md) | Precedence, facts, conditionals, debugging |
| 5 | [Templates and Handlers](docs/en/modules/5-templates-and-handlers.md) | Jinja2 templates, `ansible_managed`, handler chains |
| 6 | [Roles and Collections](docs/en/modules/6-roles-and-collections.md) | `ansible-creator`, `ade`, Galaxy, argument specs, FQCNs |
| 7 | [Testing Your Automation](docs/en/modules/7-testing-your-automation.md) | `ansible-lint`, Molecule, `pytest-ansible`, `tox-ansible` |
| 8 | [Packaging and Deployment](docs/en/modules/8-packaging-and-deployment.md) | Execution Environments, `ansible-builder`, `ansible-sign` |
| 9 | [Scaling with AAP](docs/en/modules/9-scaling-with-aap.md) | Controller, Hub, EDA, workflows, RBAC |

## Getting Started

**Prerequisites:** Comfortable with the Linux command line. No prior Ansible experience required.

Choose your lab environment:

- **Local devcontainer** — VS Code + Docker/Podman. Clone the repo, open in VS Code, and reopen in the container. See [Module 1](docs/en/modules/1-introduction.md) for setup instructions.
- **Red Hat Developer Sandbox** — Browser-based environment with all tools pre-installed. Visit [developers.redhat.com](https://developers.redhat.com/products/ansible/getting-started).

## Languages

- [English](docs/en/index.md)
- [Español](docs/es/index.md)

## Repository Layout

```
docs/           Course content (EN + ES)
ansible/        Companion Ansible code
  inventory/    Structured inventory (Module 3+)
  playbooks/    Per-module playbook examples
  templates/    Jinja2 templates (Module 5)
  collections/  parasoltech.infrastructure collection (Module 6+)
  execution-environments/  EE definitions (Module 8)
.devcontainer/  VS Code devcontainer configuration
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing content and translations.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
