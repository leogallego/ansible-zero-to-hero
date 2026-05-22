# Module 5: Templates and Handlers

## Learning Objectives

By the end of this module you will be able to:

- Write Jinja2 templates with variables, filters, loops, and conditionals
- Use `{{ ansible_managed | comment }}` and `backup: true` in template tasks
- Configure handler chains with `notify` and understand when handlers run
- Explain why templates should not include timestamps or dates

## The Story So Far

Alex and Jordan have parameterized the Parasol Tech playbooks with variables and facts. Every environment reads its own values from `group_vars/`, and playbooks adapt dynamically using `when` conditions. But there is a new problem.

"We need to deploy configuration files," Alex says. "Nginx config, MOTD banners, application settings -- each one needs different values per environment. I could use `ansible.builtin.copy` with a static file, but then I need a separate file for dev, staging, and production. That does not scale."

"That is exactly what templates are for," Jordan replies. "You write one template with placeholders, and Ansible fills in the values at deploy time. And when the config changes, handlers restart the service automatically."

## Jinja2 Template Basics

Ansible uses the **Jinja2** templating engine. A Jinja2 template is a text file -- any format (YAML, INI, TOML, XML, plain text) -- with special delimiters that Ansible evaluates at runtime.

### The Three Delimiters

| Delimiter | Purpose | Example |
|-----------|---------|---------|
| `{{ ... }}` | Output a variable or expression | `server_name {{ parasol_nginx_server_name }};` |
| `{% ... %}` | Execute logic (loops, conditionals) | `{% if parasol_nginx_ssl_enabled %}` |
| `{# ... #}` | Comment (not included in output) | `{# This line is ignored #}` |

### Variables in Templates

Any variable available to the play -- inventory variables, facts, registered variables, `set_fact` values -- is available inside templates:

```jinja
# Simple variable substitution
server_name {{ parasol_nginx_server_name }};
listen {{ parasol_nginx_http_port | default(80) }};
```

The `| default(80)` is a **filter** -- it provides a fallback value if the variable is not defined. Filters are one of Jinja2's most useful features.

### Filters

Filters transform variable values using the pipe (`|`) syntax. Here are the filters you will use most often:

| Filter | What it does | Example |
|--------|-------------|---------|
| `default(value)` | Provide a fallback if undefined | `{{ port | default(8080) }}` |
| `upper` / `lower` | Change case | `{{ env | upper }}` produces `PRODUCTION` |
| `int` / `float` | Type conversion | `{{ count | int }}` |
| `join(sep)` | Join a list into a string | `{{ servers | join(', ') }}` |
| `comment` | Wrap text in comment syntax | `{{ ansible_managed | comment }}` |
| `regex_replace` | Regex substitution | `{{ path | regex_replace('/tmp', '/var') }}` |
| `length` | Count items in a list or string | `{{ items | length }}` |

The companion template `motd.j2` uses several of these:

```jinja
{{ ansible_managed | comment }}

=============================================
  Welcome to {{ inventory_hostname }}
  Organization: {{ parasol_organization | default('Unknown') }}
  Environment:  {{ parasol_environment | default('unknown') | upper }}
{% if parasol_admin_email is defined %}
  Contact:      {{ parasol_admin_email }}
{% endif %}
=============================================
```

Notice how `upper` is chained after `default` -- filters can be piped together. The `| comment` filter on `ansible_managed` wraps the managed-by string in the appropriate comment syntax for the file format.

### Conditionals in Templates

Use `{% if %}`, `{% elif %}`, and `{% endif %}` to include or exclude sections:

```jinja
{% if parasol_nginx_ssl_enabled | default(false) %}
    listen 443 ssl;
    ssl_certificate     {{ parasol_nginx_ssl_cert }};
    ssl_certificate_key {{ parasol_nginx_ssl_key }};
{% else %}
    listen 80;
{% endif %}
```

You can also test whether a variable exists:

```jinja
{% if parasol_admin_email is defined %}
  Contact: {{ parasol_admin_email }}
{% endif %}
```

### Loops in Templates

Use `{% for %}` and `{% endfor %}` to iterate over lists:

```jinja
upstream app_backend {
{% for server in parasol_nginx_upstream_servers %}
    server {{ server.address }}:{{ server.port | default(8080) }};
{% endfor %}
}
```

This is one of the most powerful template features. The companion template `nginx.conf.j2` uses a loop to generate an upstream block dynamically from a list of backend servers defined in inventory variables.

You can also access loop metadata:

| Variable | Description |
|----------|-------------|
| `loop.index` | Current iteration (1-indexed) |
| `loop.index0` | Current iteration (0-indexed) |
| `loop.first` | `true` on the first iteration |
| `loop.last` | `true` on the last iteration |
| `loop.length` | Total number of items |

```jinja
{% for server in parasol_nginx_upstream_servers %}
    # Server {{ loop.index }} of {{ loop.length }}
    server {{ server.address }}:{{ server.port | default(8080) }};
{% endfor %}
```

## The Template Module

The `ansible.builtin.template` module renders a Jinja2 template on the control node and copies the result to the target host. It works like `ansible.builtin.copy`, but processes the file through Jinja2 first.

### Basic Usage

```yaml
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    owner: root
    group: root
    mode: "0644"
    backup: true
```

Key parameters:

| Parameter | Description |
|-----------|-------------|
| `src` | Path to the Jinja2 template (relative to `templates/` in a role, or an absolute/relative path) |
| `dest` | Destination path on the target host |
| `owner` / `group` | File ownership |
| `mode` | File permissions (always quote to avoid octal interpretation) |
| `backup` | Create a backup of the existing file before overwriting |
| `validate` | Command to validate the rendered file before deploying |

### The `validate` Parameter

For configuration files that have a syntax checker, use `validate` to catch errors before deployment:

```yaml
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    mode: "0644"
    backup: true
    validate: "nginx -t -c %s"
```

The `%s` is replaced with the path to the rendered temporary file. If validation fails, the task fails and the original file is untouched. This is a safety net that prevents deploying broken configurations.

### Template Resolution in Roles

When used inside a role, the `src` path is resolved relative to the role's `templates/` directory. You do not need to specify the full path:

```yaml
# Inside a role, this looks for roles/myrole/templates/nginx.conf.j2
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
```

Outside a role (in a standalone playbook), you need to provide the path relative to the playbook or use an absolute path. The companion playbook `deploy-config.yml` uses `{{ playbook_dir }}` to build the path:

```yaml
- name: Deploy nginx configuration from template
  ansible.builtin.template:
    src: "{{ playbook_dir }}/../../templates/nginx.conf.j2"
    dest: "{{ parasol_demo_dir }}/nginx.conf"
    mode: "0644"
    backup: true
```

## Template Best Practices

### Always Include `ansible_managed`

Every template should start with the `{{ ansible_managed | comment }}` marker. This generates a comment at the top of the rendered file that warns anyone editing it directly:

```text
# Ansible managed
```

This is critical in operations. If someone opens a configuration file on a server and sees this marker, they know not to edit it by hand -- the next Ansible run will overwrite their changes.

```jinja
{{ ansible_managed | comment }}

# Application configuration
server_port={{ app_port | default(8443) }}
```

The `| comment` filter automatically uses the correct comment syntax. For most files it uses `#`, but you can customize it for formats that use different comment styles.

### Always Use `backup: true`

Always include `backup: true` in `ansible.builtin.template` and `ansible.builtin.copy` tasks:

```yaml
- name: Deploy application config
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/myapp/app.conf
    mode: "0644"
    backup: true
```

When Ansible overwrites a file, the backup is saved alongside it with a timestamp suffix (e.g., `app.conf.2026-05-21@12:30:45~`). This gives you a quick rollback path if something goes wrong.

### Never Include Timestamps or Dates

Templates must produce the same output when run with the same inputs. If you include a timestamp:

```jinja
{# BAD — breaks idempotency #}
# Generated on {{ ansible_facts['date_time']['iso8601'] }}
```

The rendered file will be different on every run, even if nothing else changed. This means the `template` task will always report `changed`, which triggers handlers unnecessarily and makes it impossible to tell whether a real configuration change occurred.

!!! danger "Timestamps break idempotency"
    Never use `ansible_facts['date_time']`, `now()`, or any time-based value in a template. The `ansible_managed` marker already tells operators the file is managed by Ansible -- that is sufficient.

### Use `mode` with Quoted Strings

Always quote the `mode` parameter:

```yaml
mode: "0644"   # Correct — string
mode: 0644     # WRONG — YAML interprets as decimal integer 420
```

YAML treats unquoted numbers starting with `0` as octal, but only if they are valid octal. `0644` happens to work, but `0755` could surprise you in edge cases. Quoting removes all ambiguity.

## Handlers and Notify

Deploying a new configuration file is only half the job. The service reading that file usually needs to be reloaded or restarted to pick up the changes. This is what **handlers** are for.

### What Handlers Are

A handler is a task that runs only when notified by another task. It is defined in the `handlers:` section of a play, and tasks trigger it using the `notify` keyword:

```yaml
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    mode: "0644"
    backup: true
  notify: Reload nginx

handlers:
  - name: Reload nginx
    ansible.builtin.systemd:
      name: nginx
      state: reloaded
```

The handler `Reload nginx` will only execute if the template task reports `changed` -- meaning the rendered file is different from what was already on disk. If the file has not changed, the handler is not notified and the service is left alone.

This is the key insight: **handlers make service restarts idempotent**. You do not restart nginx on every run -- only when the configuration actually changed.

### Notifying Multiple Handlers

A single task can notify multiple handlers by passing a list:

```yaml
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    mode: "0644"
    backup: true
  notify:
    - Validate nginx configuration
    - Reload nginx
```

Both handlers will be triggered if the template changes. The companion playbook `deploy-config.yml` demonstrates this pattern.

### Handler Deduplication

If multiple tasks notify the same handler, it still only runs **once**. Ansible deduplicates handler notifications:

```yaml
tasks:
  - name: Deploy main config
    ansible.builtin.template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
      mode: "0644"
      backup: true
    notify: Reload nginx

  - name: Deploy SSL config
    ansible.builtin.template:
      src: ssl.conf.j2
      dest: /etc/nginx/conf.d/ssl.conf
      mode: "0644"
      backup: true
    notify: Reload nginx
```

Even if both templates change, the `Reload nginx` handler runs only once. This is exactly what you want -- you do not want to reload nginx twice in the same play.

## When Handlers Run

Understanding handler timing is critical to writing correct playbooks.

### Default Behavior: End of Play

By default, handlers run **at the end of the play**, after all tasks have completed. They do not run immediately after the notifying task:

```text
TASK [Deploy main config]        → changed (notifies Reload nginx)
TASK [Deploy SSL config]         → changed (notifies Reload nginx)
TASK [Deploy upstream config]    → ok (no notification)
TASK [Display status message]    → ok
HANDLER [Reload nginx]           → runs once, here at the end
```

This means if a task later in the play depends on the handler having already run (e.g., a health check that needs the reloaded service), you have a problem. The handler has not run yet.

### Flushing Handlers with `meta: flush_handlers`

You can force all pending handlers to run immediately using `meta: flush_handlers`:

```yaml
tasks:
  - name: Deploy nginx configuration
    ansible.builtin.template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
      mode: "0644"
      backup: true
    notify: Reload nginx

  - name: Force handlers to run now
    ansible.builtin.meta: flush_handlers

  - name: Verify nginx is responding
    ansible.builtin.uri:
      url: "http://localhost/"
      status_code: 200
```

After `flush_handlers`, all notified handlers execute immediately. The `Verify nginx is responding` task can then safely assume the service is running with the new configuration.

The companion playbook `handler-chain.yml` demonstrates `flush_handlers` in action.

### Handler Execution Order

When multiple handlers are notified, they run in the order they are **defined** in the `handlers:` section, not in the order they were notified. This is a common source of confusion.

```yaml
tasks:
  - name: Deploy config
    ansible.builtin.copy:
      dest: /tmp/demo.txt
      content: "demo\n"
      mode: "0644"
    notify:
      - Third handler (C)    # notified first
      - First handler (A)    # notified second
      - Second handler (B)   # notified third

handlers:
  - name: First handler (A)    # runs first (defined first)
    ansible.builtin.debug:
      msg: "A"
      verbosity: 0

  - name: Second handler (B)   # runs second (defined second)
    ansible.builtin.debug:
      msg: "B"
      verbosity: 0

  - name: Third handler (C)    # runs third (defined third)
    ansible.builtin.debug:
      msg: "C"
      verbosity: 0
```

The handlers run in order A, B, C -- following the definition order in `handlers:`, not the notification order. This lets you control execution sequence by arranging handlers in the right order in the `handlers:` section.

!!! tip "Ordering handlers intentionally"
    If you need `Validate config` to run before `Reload service`, define `Validate config` first in the `handlers:` section. The notification order in `notify:` does not matter.

### Handlers and Failures

If a task fails during the play, pending handlers **do not run** by default. This is a safety measure -- if something went wrong, you probably do not want to reload the service.

You can override this behavior at the play level:

```yaml
- name: Deploy with force handlers
  hosts: webservers
  force_handlers: true
```

With `force_handlers: true`, handlers will run even if a later task fails. Use this when the handler action is safe and important (e.g., reloading a config that was successfully deployed before the failure occurred).

## Putting It All Together

The companion code for this module ties all the concepts together.

### The nginx.conf.j2 Template

This template (`ansible/templates/nginx.conf.j2`) demonstrates:

- **`{{ ansible_managed | comment }}`** at the top
- **Variables with defaults**: `{{ parasol_nginx_worker_connections | default(1024) }}`
- **Conditionals**: SSL configuration is only included when `parasol_nginx_ssl_enabled` is `true`
- **Loops**: The upstream server pool is generated from a list variable

### The motd.j2 Template

A simpler template (`ansible/templates/motd.j2`) showing:

- **Filters**: `upper` to capitalize the environment name
- **Conditionals**: A production warning only appears when the environment is `production`
- **`is defined` test**: The contact line only appears if `parasol_admin_email` is set

### The deploy-config.yml Playbook

This playbook (`ansible/playbooks/module-05/deploy-config.yml`) deploys both templates to a demo directory and demonstrates:

- Template deployment with `backup: true`
- Handler notification on change
- Multiple handlers chained to one task

### The handler-chain.yml Playbook

This playbook (`ansible/playbooks/module-05/handler-chain.yml`) focuses on handler behavior:

- Handler execution order (definition order, not notification order)
- `meta: flush_handlers` to force immediate execution
- Handler deduplication (two tasks notifying the same handler)
- Idempotency -- handlers do not fire when no change occurs

## Exercises

### Exercise 1: Deploy Configuration Files

Run the deploy-config playbook:

```bash
cd ansible
ansible-navigator run playbooks/module-05/deploy-config.yml --mode stdout
```

Examine the generated files:

```bash
cat /tmp/ansible-demo/nginx.conf
cat /tmp/ansible-demo/motd
```

Look at the top of each file. Do you see the `# Ansible managed` comment? This is the `{{ ansible_managed | comment }}` marker in action.

Run the playbook again without changing anything. Notice that the tasks report `ok` (not `changed`) and the handlers do **not** run. This is idempotency.

### Exercise 2: Explore Handler Behavior

Run the handler chain playbook:

```bash
ansible-navigator run playbooks/module-05/handler-chain.yml --mode stdout
```

Watch the output carefully:

1. The three handlers run in A, B, C order (definition order), even though they were notified in C, A, B order
2. `meta: flush_handlers` causes them to run mid-play
3. The second copy task does not trigger handlers because the content is unchanged
4. The deduplicated handler runs only once despite being notified by two tasks

### Exercise 3: Add SSL to the nginx Template

Modify the `deploy-config.yml` playbook to enable SSL:

```yaml
vars:
  parasol_nginx_ssl_enabled: true
  parasol_nginx_ssl_cert: "/etc/pki/tls/certs/parasol.crt"
  parasol_nginx_ssl_key: "/etc/pki/tls/private/parasol.key"
```

Run the playbook again and examine the generated `nginx.conf`. You should see the SSL configuration block appear, including the redirect from HTTP to HTTPS.

### Exercise 4: Write Your Own Template

Create a template for an application configuration file. For example, create `ansible/templates/app.conf.j2`:

```jinja
{{ ansible_managed | comment }}

[server]
port={{ parasol_app_port | default(8443) }}
bind_address={{ parasol_app_bind | default('0.0.0.0') }}
workers={{ parasol_app_workers | default(4) }}

[logging]
level={{ parasol_log_level | default('info') }}
file=/var/log/myapp/app.log

[database]
{% if parasol_db_host is defined %}
host={{ parasol_db_host }}
port={{ parasol_db_port | default(5432) }}
name={{ parasol_db_name | default('myapp') }}
{% else %}
# No database configured — using local SQLite
file=/var/lib/myapp/data.db
{% endif %}
```

Write a playbook that deploys this template with `backup: true` and notifies a handler when the file changes.

### Exercise 5: Environment-Specific MOTD

Run the deploy-config playbook with the production environment override:

```bash
ansible-navigator run playbooks/module-05/deploy-config.yml \
  --mode stdout -e "parasol_environment=production"
```

Compare the MOTD output with the default (dev) run. The production version includes the warning message because the template checks `parasol_environment`.

This demonstrates a key principle: **one template, multiple outputs**. The same `motd.j2` file produces different results based on the variables provided.

## Summary

In this module you:

- Learned the three Jinja2 delimiters (`{{ }}`, `{% %}`, `{# #}`) and how to use variables, filters, loops, and conditionals in templates
- Used the `ansible.builtin.template` module with `backup: true` and `validate` to deploy rendered configuration files safely
- Added `{{ ansible_managed | comment }}` to every template so operators know the file is managed by Ansible
- Understood why timestamps and dates must never appear in templates (they break idempotency)
- Configured handlers with `notify` to restart or reload services only when configuration actually changes
- Explored handler execution order (definition order, not notification order), deduplication, and `meta: flush_handlers`
- Used `force_handlers` to ensure critical handlers run even when later tasks fail

Alex and Jordan now deploy configuration files as templates. One `nginx.conf.j2` works across dev, staging, and production -- each environment fills in its own values from inventory variables. When the config changes, handlers reload the service automatically. When it does not change, nothing happens. The automation is idempotent and self-documenting.

## Next Steps

Next: [Module 6 -- Roles and Collections](6-roles-and-collections.md)
