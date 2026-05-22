# webserver

Install and configure a web server.

## Requirements

- Target hosts must be running a supported platform (RHEL/CentOS 8+, Fedora).
- The `ansible.posix` collection is required for POSIX-specific functionality.

## Role Variables

### User-facing variables (`defaults/main.yml`)

| Variable | Default | Description |
|----------|---------|-------------|
| `webserver_port` | `80` | HTTP port the server listens on |
| `webserver_document_root` | `/var/www/html` | Directory for web content |
| `webserver_server_name` | `localhost` | Virtual host server name |
| `webserver_service_enabled` | `true` | Whether to start and enable the service |
| `webserver_max_connections` | `256` | Maximum simultaneous connections |
| `webserver_admin_email` | _(undefined)_ | Admin email for error pages |
| `webserver_packages` | _(undefined)_ | Override default package list |

### Internal variables (`vars/main.yml`)

These are not intended for user override:

| Variable | Description |
|----------|-------------|
| `__webserver_packages_default` | Platform default packages |
| `__webserver_service_name` | System service name |
| `__webserver_config_dir` | Configuration directory path |
| `__webserver_config_file` | Main configuration file name |

## Dependencies

None.

## Example Playbook

```yaml
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

## Idempotency

This role is fully idempotent. Running it twice with the same variables
produces no changes on the second run. The web server is only reloaded
when the configuration file actually changes.

## Rollback

Set `webserver_service_enabled: false` to stop and disable the service.
Configuration file backups are created automatically via `backup: true`.

## License

Apache-2.0

## Author Information

Parasol Tech Platform Team <platform@parasol.example>
