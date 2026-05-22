# Module 3: Managing Inventory

## Learning Objectives

By the end of this module you will be able to:

- Create structured inventory directories with groups and nested groups
- Define host variables and group variables in dedicated files
- Target specific hosts using patterns and `--limit`
- Explain the difference between static and dynamic inventory

## The Story So Far

Lionel has three working playbooks, but they all target `localhost`. In the real world, Parasol Tech has dozens of servers spread across three environments (development, staging, and production) running different services. Web servers, database servers, application servers: each environment has its own set.

Lionel needs a way to tell Ansible about all of these hosts, organize them logically, and assign different configuration values depending on the environment and the server's role. This is what the **inventory** does.

## What is an Inventory?

An inventory is the list of hosts that Ansible manages, along with metadata about those hosts (which groups they belong to, what variables apply to them). Without an inventory, Ansible has no idea what machines exist or how to reach them.

In Module 1, we used a minimal inventory with a single entry:

```yaml
---
all:
  hosts:
    localhost:
      ansible_connection: local
```

That was enough to get started, but Parasol Tech's infrastructure looks more like this:

```text
Parasol Tech Infrastructure
├── Development
│   ├── web01.dev.parasol.example
│   ├── web02.dev.parasol.example
│   └── db01.dev.parasol.example
├── Staging
│   ├── web01.staging.parasol.example
│   ├── web02.staging.parasol.example
│   └── db01.staging.parasol.example
└── Production
    ├── web01.prod.parasol.example
    ├── web02.prod.parasol.example
    ├── web03.prod.parasol.example
    ├── db01.prod.parasol.example
    └── db02.prod.parasol.example
```

Let's learn how to represent this in Ansible.

## Static Inventory Formats

A **static inventory** is a file you write and maintain by hand. Ansible supports two formats: INI and YAML. Both achieve the same result; the choice is a matter of preference.

=== "YAML format (recommended)"

    ```yaml
    ---
    all:
      hosts:
        localhost:
          ansible_connection: local

      children:
        webservers:
          hosts:
            web01.dev.parasol.example:
            web02.dev.parasol.example:
        dbservers:
          hosts:
            db01.dev.parasol.example:
    ```

    YAML inventories use the same syntax as playbooks. Groups are nested under `children:`, and hosts are listed under `hosts:`. The trailing colon after each hostname is required: it marks the host as a key with no inline values.

=== "INI format"

    ```ini
    localhost ansible_connection=local

    [webservers]
    web01.dev.parasol.example
    web02.dev.parasol.example

    [dbservers]
    db01.dev.parasol.example
    ```

    INI inventories use section headers in square brackets for groups and list hosts one per line. Variables are added inline after the hostname.

!!! tip "Which format should you use?"
    This course uses YAML for all inventories. YAML is more explicit, supports deeper nesting naturally, and uses the same syntax you already know from playbooks. INI format is simpler for very small inventories but becomes harder to read as complexity grows.

### The `all` Group

Every host in an Ansible inventory automatically belongs to the `all` group. You do not need to add hosts to it explicitly; any host defined anywhere in the inventory is a member of `all`. This makes `all` useful for variables that should apply to every host (we will see this shortly with `group_vars/all.yml`).

There is also an `ungrouped` group that contains hosts which are not members of any other group (besides `all`).

## Groups and Nested Groups

Groups let you organize hosts so you can target them selectively. Instead of running a playbook against every single host, you can target just `webservers` or just `production`.

### Simple Groups

The most basic grouping puts hosts into categories by function:

```yaml
---
all:
  children:
    webservers:
      hosts:
        web01.dev.parasol.example:
        web02.dev.parasol.example:
    dbservers:
      hosts:
        db01.dev.parasol.example:
```

Now you can run a playbook against `hosts: webservers` and it will target only the web servers, or against `hosts: dbservers` for only the database servers.

### Nested Groups (Groups of Groups)

Real infrastructure needs to be organized along multiple dimensions. Parasol Tech's servers belong to both an **environment** (dev, staging, production) and a **function** (webservers, dbservers). Nested groups handle this by letting a group contain other groups as children.

Here is how the course inventory (`ansible/inventory/hosts.yml`) is structured:

```yaml
---
all:
  hosts:
    localhost:
      ansible_connection: local

  children:
    # Environment groups
    dev:
      children:
        dev_webservers:
          hosts:
            web01.dev.parasol.example:
            web02.dev.parasol.example:
        dev_dbservers:
          hosts:
            db01.dev.parasol.example:

    staging:
      children:
        staging_webservers:
          hosts:
            web01.staging.parasol.example:
            web02.staging.parasol.example:
        staging_dbservers:
          hosts:
            db01.staging.parasol.example:

    production:
      children:
        prod_webservers:
          hosts:
            web01.prod.parasol.example:
            web02.prod.parasol.example:
            web03.prod.parasol.example:
        prod_dbservers:
          hosts:
            db01.prod.parasol.example:
            db02.prod.parasol.example:

    # Functional groups (span all environments)
    webservers:
      children:
        dev_webservers:
        staging_webservers:
        prod_webservers:

    dbservers:
      children:
        dev_dbservers:
        staging_dbservers:
        prod_dbservers:
```

This structure gives Lionel maximum flexibility:

| Target | Hosts reached |
|--------|--------------|
| `hosts: all` | Every host |
| `hosts: production` | All production hosts (web + db) |
| `hosts: webservers` | All web servers across all environments |
| `hosts: prod_webservers` | Only production web servers |
| `hosts: dev` | All dev hosts |

!!! info "A host can belong to multiple groups"
    `web01.dev.parasol.example` is a member of `dev_webservers`, `dev`, `webservers`, and `all`, all at the same time. This is by design. The group hierarchy creates overlapping sets that let you target hosts from different angles.

### Group Naming Convention

Notice the naming pattern: `dev_webservers`, `staging_dbservers`, `prod_webservers`. Using underscores and consistent prefixes keeps group names predictable and makes it easy to construct patterns. Never use dashes in group names; they can cause issues with variable resolution.

## Host Variables and Group Variables

Variables let you assign different configuration values to different hosts or groups of hosts. Ansible provides a clean separation through two mechanisms: **host variables** and **group variables**.

### The Rule: No Variables in the Hosts File

A critical best practice: **never put variable definitions in the inventory hosts file**. The hosts file should contain only hosts and groups. Variables belong in separate files.

This separation has practical benefits:

- Variables are easier to find, read, and review
- You can change variables without touching the host list
- It encourages organizing variables by scope (all hosts vs. one group vs. one host)
- Version control diffs are cleaner: you can see that a variable changed without wading through the host list

### Group Variables (`group_vars/`)

Group variables apply to every host in a group. They are defined in files inside a `group_vars/` directory, with one file per group.

For Parasol Tech's inventory, the `group_vars/` directory looks like this:

```text
ansible/inventory/
├── hosts.yml
├── group_vars/
│   ├── all.yml          # Applies to every host
│   ├── dev.yml          # Applies to the dev group
│   ├── staging.yml      # Applies to the staging group
│   └── production.yml   # Applies to the production group
└── host_vars/
    ├── db01.prod.parasol.example.yml
    └── db02.prod.parasol.example.yml
```

**`group_vars/all.yml`**: variables for every host:

```yaml
---
parasol_organization: "Parasol Tech"
parasol_ntp_server: "ntp.parasol.example"
parasol_dns_servers:
  - "10.0.0.10"
  - "10.0.0.11"
parasol_admin_email: "platform-team@parasol.example"
```

**`group_vars/dev.yml`**: variables for the dev environment only:

```yaml
---
parasol_environment: "dev"
parasol_log_level: "debug"
parasol_monitoring_enabled: false
parasol_backup_schedule: "weekly"
```

**`group_vars/production.yml`**: variables for the production environment:

```yaml
---
parasol_environment: "production"
parasol_log_level: "warning"
parasol_monitoring_enabled: true
parasol_backup_schedule: "hourly"
```

When Ansible runs against `web01.dev.parasol.example`, it merges variables from `all.yml` and `dev.yml`. The host gets both `parasol_organization` (from `all`) and `parasol_log_level: debug` (from `dev`). A production host gets `parasol_log_level: warning` instead.

### Host Variables (`host_vars/`)

Host variables apply to a single host. They are defined in files named after the host inside a `host_vars/` directory.

**`host_vars/db01.prod.parasol.example.yml`**:

```yaml
---
parasol_db_role: "primary"
parasol_db_max_connections: 500
parasol_db_backup_retention_days: 30
```

**`host_vars/db02.prod.parasol.example.yml`**:

```yaml
---
parasol_db_role: "replica"
parasol_db_max_connections: 200
parasol_db_backup_retention_days: 7
```

Even though both database servers are in the `production` group and share the same group variables, they have different roles (primary vs. replica) and different connection limits. Host variables handle these per-host differences.

### Variable Precedence (Preview)

When the same variable is defined at multiple levels, Ansible follows a precedence order. For inventory variables, the rule is simple:

**host variables override group variables, and group variables override `all` variables.**

For example, if `group_vars/all.yml` sets `parasol_log_level: info` and `group_vars/dev.yml` sets `parasol_log_level: debug`, a dev host gets `debug` because the more specific group wins.

We will cover the full variable precedence system in Module 4. For now, remember: more specific wins.

## Structured Inventory Directories

You have already seen the structure. Let's make it explicit. A **structured inventory directory** separates hosts, group variables, and host variables into their own files and directories:

```text
inventory/
├── hosts.yml              # Host and group definitions (no variables)
├── group_vars/
│   ├── all.yml            # Variables for every host
│   ├── dev.yml            # Variables for the dev group
│   ├── staging.yml        # Variables for the staging group
│   └── production.yml     # Variables for the production group
└── host_vars/
    ├── db01.prod.parasol.example.yml
    └── db02.prod.parasol.example.yml
```

### Why Not a Single File?

You *can* put everything in one file (hosts, groups, and all variables inline). But you should not, for the same reasons you don't put an entire application in a single file:

| Single file inventory | Structured directory |
|----------------------|---------------------|
| Everything in one place, hard to navigate | Organized by scope, easy to find what you need |
| One change = one big diff | Changes are isolated to specific files |
| Variable definitions mixed with host lists | Clean separation of concerns |
| Hard to share variables across inventories | `group_vars/` files can be symlinked or templated |

### Pointing Ansible to the Inventory

In `ansible.cfg`, the `inventory` setting tells Ansible where to find the inventory:

```ini
[defaults]
inventory = inventory/hosts.yml
```

When you point to a file inside a directory that also contains `group_vars/` and `host_vars/`, Ansible automatically loads variables from those directories. This is why the structured directory approach works without any extra configuration.

!!! info "Directory vs. file path"
    You can also point `inventory` at the directory itself (`inventory = inventory/`). The behavior is nearly identical: Ansible loads all valid inventory files in the directory along with `group_vars/` and `host_vars/`. Pointing to the specific file is more explicit and avoids accidentally loading unintended files.

## Targeting Hosts

Once you have an inventory with groups, you can select which hosts a playbook runs against using **host patterns** and the `--limit` flag.

### Host Patterns in Playbooks

The `hosts:` directive in a play accepts patterns, not just group names:

```yaml
# Target a single group
- hosts: webservers

# Target multiple groups (union)
- hosts: webservers:dbservers

# Target the intersection of two groups (hosts in BOTH)
- hosts: staging:&webservers

# Target a group but exclude another
- hosts: production:!dbservers
```

| Pattern | Meaning |
|---------|---------|
| `webservers` | All hosts in the webservers group |
| `webservers:dbservers` | Hosts in webservers OR dbservers |
| `staging:&webservers` | Hosts in BOTH staging AND webservers |
| `production:!dbservers` | Hosts in production but NOT in dbservers |
| `web*.prod.parasol.example` | Hosts matching the wildcard |
| `all` | Every host in the inventory |

### The `--limit` Flag

The `--limit` flag (or `-l`) narrows down which hosts a playbook targets at run time, without changing the playbook itself. This is especially useful for:

- Testing a playbook against one host before rolling it out to a group
- Running in production on a subset of hosts at a time (rolling updates)
- Troubleshooting a single host

```bash
# Run against only web01 in production
ansible-navigator run playbooks/deploy.yml --mode stdout --limit web01.prod.parasol.example

# Run against only the dev environment
ansible-navigator run playbooks/deploy.yml --mode stdout --limit dev

# Run against webservers in staging only
ansible-navigator run playbooks/deploy.yml --mode stdout --limit 'staging:&webservers'
```

!!! warning "Quote patterns with special characters"
    When using `:`, `&`, `!`, or `*` in limit patterns on the command line, wrap the pattern in quotes to prevent the shell from interpreting them.

### Listing Hosts Without Running

You can preview which hosts a playbook *would* target without running it:

```bash
# List all hosts in the inventory
ansible-navigator inventory --list --mode stdout

# List hosts in a specific group
ansible-navigator inventory --graph production --mode stdout

# Show which hosts a playbook would target
ansible-navigator run playbooks/deploy.yml --mode stdout --list-hosts
```

The `--graph` option shows the group hierarchy as a tree, which is a great way to verify your inventory structure.

## Dynamic Inventory Concepts

Everything we have covered so far is **static inventory**: you write the host list by hand and update it manually when hosts are added or removed. This works well for small, stable environments.

But what about cloud environments where virtual machines are created and destroyed automatically? Or large environments with hundreds of hosts managed by a CMDB (Configuration Management Database)?

This is where **dynamic inventory** comes in. A dynamic inventory is a script or plugin that queries an external source and generates the inventory on the fly.

### How Dynamic Inventory Works

Instead of pointing `inventory` at a static file, you point it at a script or configure an inventory plugin. When Ansible runs, it executes the script (or calls the plugin), which returns the host list and variables in JSON format.

Common dynamic inventory sources include:

| Source | Use Case |
|--------|----------|
| AWS EC2 | Cloud instances on Amazon Web Services |
| Azure RM | Virtual machines on Microsoft Azure |
| GCP Compute | Instances on Google Cloud Platform |
| Red Hat Satellite | Hosts managed by Satellite |
| NetBox | Hosts tracked in a network source of truth |
| ServiceNow CMDB | Enterprise IT service management |

### Static + Dynamic Together

You can combine static and dynamic inventories by pointing `inventory` at a directory that contains both a static file and a dynamic inventory script or plugin configuration. Ansible merges the results.

This is common in practice: you keep a static inventory for hosts that do not live in a dynamic source, and use a plugin for the rest.

!!! info "Dynamic inventory in this course"
    We will not set up dynamic inventory in this course because it requires access to an external service (a cloud provider, a CMDB, etc.). The important thing to understand is the concept: inventory can be generated programmatically from any source. The group and variable patterns you learn with static inventory apply equally to dynamic inventory.

## Exercises

### Exercise 1: Explore the Inventory

Navigate to the `ansible/` directory and run the inventory verification playbook:

```bash
cd ansible
ansible-navigator run playbooks/module-03/check-inventory.yml --mode stdout
```

Examine the output. You should see:

- All defined groups
- Hosts in each environment group (dev, staging, production)
- Hosts in each functional group (webservers, dbservers)
- Variables from `group_vars/all.yml`
- The total host count

### Exercise 2: View the Inventory Graph

Use `ansible-navigator` to visualize the inventory hierarchy:

```bash
ansible-navigator inventory --graph --mode stdout
```

You should see a tree showing how groups are nested. Try graphing a specific group:

```bash
ansible-navigator inventory --graph production --mode stdout
```

### Exercise 3: Practice with `--limit`

Run the check-inventory playbook with different `--limit` values and observe how the output changes:

```bash
# Target only localhost (the only host we can actually connect to)
ansible-navigator run playbooks/module-03/check-inventory.yml --mode stdout --limit localhost

# See what would happen if we targeted production
ansible-navigator run playbooks/module-03/check-inventory.yml --mode stdout --limit production --list-hosts
```

### Exercise 4: Add a Group Variable File

Create a new file `ansible/inventory/group_vars/webservers.yml` with variables specific to web servers:

```yaml
---
parasol_http_port: 8080
parasol_max_connections: 1000
parasol_document_root: "/var/www/html"
```

Run the check-inventory playbook again. Can you modify the playbook to display these new variables? (Hint: add a new `ansible.builtin.debug` task.)

### Exercise 5: Inspect Host Variables

Run the following command to see all variables that Ansible would assign to a specific host:

```bash
ansible-navigator inventory --host db01.prod.parasol.example --mode stdout
```

Notice how the output includes variables from `group_vars/all.yml`, `group_vars/production.yml`, and `host_vars/db01.prod.parasol.example.yml`, all merged together.

## Summary

In this module you:

- Learned the two static inventory formats (INI and YAML) and why YAML is preferred
- Built a structured inventory with groups nested by environment and function
- Separated variables into `group_vars/` and `host_vars/` directories, never in the hosts file
- Used host patterns and `--limit` to target specific subsets of hosts
- Saw how `ansible-navigator inventory` commands help verify and explore the inventory structure
- Understood the concept of dynamic inventory and when to use it

Lionel now has an inventory that represents Parasol Tech's entire infrastructure. Each environment has its own configuration values, and specific hosts can have unique settings. The next challenge: how to use those variables to make playbooks adapt to different hosts and environments.

## Next Steps

Next: [Module 4 -- Variables and Facts](4-variables-and-facts.md)
