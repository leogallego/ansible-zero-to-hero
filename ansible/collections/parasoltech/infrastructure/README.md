# Parasol Tech Infrastructure Collection

Infrastructure automation collection for Parasol Tech.

## Description

This collection provides roles for managing common infrastructure components
at Parasol Tech, including web servers, configuration management, and service
deployment.

## Included Roles

| Role | Description |
|------|-------------|
| `parasoltech.infrastructure.webserver` | Install and configure a web server |

## Requirements

- Ansible >= 2.15
- `ansible.posix` collection >= 1.0.0

## Installation

```bash
ansible-galaxy collection install parasoltech.infrastructure
```

For development (editable install):

```bash
ade install -e .
```

## Usage

```yaml
- name: Deploy web servers
  hosts: webservers

  roles:
    - role: parasoltech.infrastructure.webserver
      vars:
        webserver_port: 8080
        webserver_document_root: /var/www/parasol
```

## License

Apache-2.0

## Author Information

Parasol Tech Platform Team <platform@parasol.example>
