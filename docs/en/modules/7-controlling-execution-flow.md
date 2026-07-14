# Module 7: Controlling Execution Flow

## Learning Objectives

By the end of this module you will be able to:

- Use `block`, `rescue`, and `always` to handle task errors gracefully and implement rollback logic
- Control task status reporting with `changed_when` and `failed_when`, and understand when `ignore_errors` is appropriate versus when it is not
- Organize playbook tasks with tags and apply the safety rule: every tag must be safe to run standalone
- Delegate tasks to other hosts with `delegate_to` and `run_once` for cross-host coordination
- Distinguish between `include_tasks` (dynamic) and `import_tasks` (static), and choose the right one for each situation
- Use `ansible.builtin.assert` to validate preconditions before proceeding with risky operations

## The Story So Far

Lionel and Jordan run their web server deployment playbook against the staging environment. The playbook installs packages, deploys configuration files, runs a database migration, and restarts services. The database migration fails on the second of four servers. Ansible stops on that host but continues on the others. The result: two servers have the new schema, one is stuck mid-migration, and one never started. The team spends the next two hours manually fixing the inconsistency.

"We need to handle errors," Jordan says. "If the migration fails, the playbook should roll back the config changes and leave the server in a known state -- not an in-between state. And we need a way to run just the migration step by itself for debugging, without re-running the whole playbook."

Lionel agrees: "I also want to run a health check on the load balancer from the control node during the deployment, not from the web servers themselves."

In this module, Lionel and Jordan learn structured error handling with blocks, fine-grained task control, tags for selective execution, delegation for cross-host tasks, and how to split their growing playbooks into reusable task files. These techniques transform their brittle, all-or-nothing playbooks into resilient, surgical automation -- and set the stage for extracting reusable roles in Module 8.

## Blocks, Rescue, and Always

A **block** groups multiple tasks under a single directive. Blocks serve two purposes: applying shared attributes (like `when`, `become`, or `tags`) to a set of tasks, and handling errors with `rescue` and `always`.

### Grouping Tasks

At its simplest, a block lets you apply a condition or privilege escalation to several tasks at once instead of repeating it on each one:

```yaml
- name: Install and configure the application
  block:
    - name: Install application packages
      ansible.builtin.package:
        name: "{{ parasol_app_packages }}"
        state: present

    - name: Deploy application configuration
      ansible.builtin.template:
        src: app.conf.j2
        dest: /etc/myapp/app.conf
        mode: "0644"
        backup: true
  when: parasol_app_enabled | default(true)
  become: true
```

Both tasks inherit the `when` condition and `become: true` from the block. Without the block, you would need to repeat both directives on every task.

### Error Handling: The Try/Catch/Finally Pattern

The real power of blocks is error handling. A block with `rescue` and `always` works like try/catch/finally in programming languages:

- **block** -- the tasks to attempt (the "try")
- **rescue** -- runs only if a task in the block fails (the "catch")
- **always** -- runs regardless of success or failure (the "finally")

```yaml
- name: Deploy application with error handling
  block:
    - name: Deploy configuration file
      ansible.builtin.copy:
        content: "version={{ parasol_app_version | default('1.0') }}\n"
        dest: "{{ parasol_demo_dir }}/app/config.ini"
        mode: "0644"

    - name: Run database migration
      ansible.builtin.command:
        cmd: /bin/false
      changed_when: false
      when: parasol_simulate_failure | default(true)

  rescue:
    - name: Report the failure
      ansible.builtin.debug:
        msg: >-
          Deployment failed at task '{{ ansible_failed_task.name }}'.
          Rolling back.
        verbosity: 0

    - name: Roll back configuration
      ansible.builtin.file:
        path: "{{ parasol_demo_dir }}/app/config.ini"
        state: absent

  always:
    - name: Record deployment attempt
      ansible.builtin.lineinfile:
        path: "{{ parasol_demo_dir }}/deploy.log"
        line: "{{ ansible_date_time.iso8601 }} - Deployment attempt completed"
        create: true
        mode: "0644"
```

When the migration task fails, Ansible skips the remaining block tasks and jumps to `rescue`. Inside rescue, two special variables are available:

| Variable | Contains |
|----------|----------|
| `ansible_failed_task` | The full task object that failed (use `.name` to get its name) |
| `ansible_failed_result` | The result object from the failed task (use `.rc`, `.msg`, `.stderr`) |

The `always` section runs after both the block and rescue (or after the block alone if nothing failed). Use it for cleanup tasks like logging, closing connections, or removing temporary files.

### Flushing Handlers in Rescue

In Module 5 you learned that handlers run at the end of the play. But what if a handler was notified before a failure, and you need it to run during rescue? Use `meta: flush_handlers` to force pending handlers to execute immediately:

```yaml
rescue:
  - name: Flush pending handlers before rollback
    ansible.builtin.meta: flush_handlers

  - name: Roll back configuration
    ansible.builtin.file:
      path: /etc/myapp/app.conf
      state: absent
```

### Early Exit with `meta`

Sometimes an error is unrecoverable and you want to stop the entire play or remove a host from further processing:

- **`meta: end_play`** -- stops the current play for all hosts. Use this in rescue when the failure affects the entire deployment.
- **`meta: end_host`** -- removes just the current host from the play. Other hosts continue.
- **`meta: clear_host_errors`** -- resets a host's error state so it participates in subsequent plays.

```yaml
rescue:
  - name: This host cannot continue
    ansible.builtin.meta: end_host
```

!!! tip "Blocks are not loops"
    Blocks group tasks for shared directives and error handling. Every task in a block executes in sequence. You cannot loop over a block. If you need to repeat a set of tasks, use `ansible.builtin.include_tasks` with a `loop` -- covered later in this module.

## Fine-Grained Task Control

Once you can catch errors with blocks, the next question is: what counts as an error? And what counts as a change? Ansible provides several directives to control task status reporting.

### `changed_when` -- Controlling Change Reporting

The `ansible.builtin.command` and `ansible.builtin.shell` modules always report `changed`, even when they perform a read-only operation. This is misleading and triggers handlers unnecessarily. Use `changed_when` to tell Ansible when a task actually changed something:

```yaml
- name: Check application version
  ansible.builtin.command:
    cmd: cat {{ parasol_demo_dir }}/app/config.ini
  register: parasol_version_check
  changed_when: false
```

Setting `changed_when: false` means "this task never changes anything." You can also use expressions:

```yaml
- name: Initialize the database
  ansible.builtin.command:
    cmd: myapp-cli db init
  register: parasol_db_init
  changed_when: "'Created' in parasol_db_init.stdout"
```

Now the task only reports `changed` when the output contains "Created." On subsequent runs where the database already exists, it reports `ok`.

!!! danger "Always add `changed_when` to command and shell tasks"
    This is not optional. Without `changed_when`, command and shell tasks always show as changed, making your playbook non-idempotent. The ansible-lint rule `no-changed-when` enforces this -- you will see it in Module 9.

### `failed_when` -- Redefining Failure

Some commands use non-zero exit codes for non-error conditions. `grep` returns exit code 1 when it finds no matches -- that is not a failure, it is an expected result. Use `failed_when` to define what actually constitutes a failure:

```yaml
- name: Check for deprecated configuration entries
  ansible.builtin.command:
    cmd: grep -c "deprecated" {{ parasol_demo_dir }}/app/config.ini
  register: parasol_deprecated_check
  failed_when: parasol_deprecated_check.rc > 1
  changed_when: false
```

Here the task only fails if `grep` itself errors (exit code 2+), not when it simply finds no matches (exit code 1).

### `ansible.builtin.assert` -- Precondition Checks

Before running a risky operation, validate that the prerequisites are met. The `assert` module fails with a clear message if conditions are not satisfied:

```yaml
- name: Validate deployment preconditions
  ansible.builtin.assert:
    that:
      - parasol_app_version is defined
      - parasol_app_version is version('1.0', '>=')
    fail_msg: >-
      parasol_app_version must be defined and >= 1.0.
      Got: '{{ parasol_app_version | default('undefined') }}'.
    success_msg: "Preconditions met: deploying version {{ parasol_app_version }}"
```

Assert is a much better alternative to silently skipping tasks with `when`. If a variable is missing, you want to know immediately -- not discover later that half the playbook was skipped.

### `ignore_errors` -- Use with Caution

The `ignore_errors: true` directive makes a task continue regardless of failure. It has its place, but it is overused:

```yaml
- name: Remove optional cache directory
  ansible.builtin.file:
    path: "{{ parasol_demo_dir }}/cache"
    state: absent
  ignore_errors: true
```

!!! warning "`ignore_errors` is a code smell"
    `ignore_errors: true` silences **all** errors on a task, including unexpected ones. Prefer `failed_when` to define exactly what constitutes failure, or use `block`/`rescue` to handle errors explicitly. Reserve `ignore_errors` for tasks where you genuinely do not care about the outcome -- like removing an optional file that may not exist. If you find yourself using it frequently, your playbook likely has a design problem.

### Batch Failure Control

For deployments across many hosts, you may not want to stop entirely when one host fails. Two play-level settings control this:

- **`any_errors_fatal: true`** -- if any host fails, all hosts stop. Use this for changes that must be all-or-nothing (like database migrations).
- **`max_fail_percentage: 25`** -- the play continues as long as fewer than 25% of hosts have failed. Useful for rolling updates where a few failures are acceptable.

## Tags

Tags let you run a subset of your playbook without executing everything. They are labels you attach to tasks, blocks, plays, or roles, and then select at the command line.

### Adding Tags

```yaml
- name: Install application packages
  ansible.builtin.package:
    name: "{{ parasol_app_packages }}"
    state: present
  tags:
    - install

- name: Deploy configuration
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/myapp/app.conf
    mode: "0644"
  tags:
    - configure
```

Run just the install tasks:

```bash
ansible-navigator run deploy.yml --mode stdout --tags install
```

### Special Tags

Ansible provides two built-in special tags:

- **`always`** -- tasks tagged with `always` run regardless of which tags you select. Use this for status checks or logging that should always happen.
- **`never`** -- tasks tagged with `never` only run when you explicitly request the tag. Use this for debug dumps or destructive operations.

```yaml
- name: Show deployment status
  ansible.builtin.debug:
    msg: "Deployment in progress"
    verbosity: 0
  tags:
    - always

- name: Dump all variables for debugging
  ansible.builtin.debug:
    var: vars
    verbosity: 0
  tags:
    - never
    - debug
```

The debug dump only runs with `--tags debug`. It never runs in normal operation.

### Previewing Tags

Before running with tags, preview what will happen:

```bash
# List all available tags
ansible-navigator run deploy.yml --mode stdout --list-tags

# List tasks that would run with specific tags
ansible-navigator run deploy.yml --mode stdout --list-tasks --tags configure
```

### Tag Inheritance

Tags on `ansible.builtin.import_tasks` flow down to every task inside the imported file. Tags on `ansible.builtin.include_tasks` apply only to the include statement itself -- the tasks inside do not inherit them. This distinction matters and is covered in the Include vs Import section below.

!!! danger "The tag safety rule"
    Every tag **must** be safe to run standalone. If running `--tags deploy` without also running `--tags install` would break something, your tag design is wrong. Tags are for selecting subsets of a well-structured playbook, not for imposing execution order.

### Tags and Blocks

When you tag a block, the tag applies to all tasks in `block`, `rescue`, and `always`. But be careful: if you run with `--tags` and the block is tagged but `rescue`/`always` are not, the error handling might not execute. Always ensure that if a block has tags, the rescue and always sections either share those tags or use the `always` special tag.

## Delegation and Run Once

Sometimes a task needs to run on a different host than the one being configured. For example, removing a web server from a load balancer before deploying to it -- that action runs on the load balancer (or the control node), not on the web server.

### `delegate_to`

The `delegate_to` directive runs a task on a specified host while still operating in the context of the current host:

```yaml
- name: Remove host from load balancer
  ansible.builtin.debug:
    msg: "Removing {{ inventory_hostname }} from load balancer pool"
    verbosity: 0
  delegate_to: localhost

- name: Deploy application
  ansible.builtin.copy:
    content: "version={{ parasol_app_version }}\n"
    dest: "{{ parasol_demo_dir }}/app/release.txt"
    mode: "0644"

- name: Add host back to load balancer
  ansible.builtin.debug:
    msg: "Adding {{ inventory_hostname }} back to load balancer pool"
    verbosity: 0
  delegate_to: localhost
```

The key insight: `delegate_to: localhost` runs the task on the control node, but `inventory_hostname` still refers to the target host. This is how you interact with external systems (load balancers, monitoring, DNS) during a per-host deployment.

!!! tip "Prefer `delegate_to: localhost` over `local_action`"
    The older `local_action` directive does the same thing but is deprecated by ansible-lint (`deprecated-local-action` rule). Always use `delegate_to: localhost` instead.

### `run_once`

When a task should execute only once regardless of how many hosts are in the play, use `run_once: true`:

```yaml
- name: Send deployment notification
  ansible.builtin.debug:
    msg: "Deployment notification sent for {{ ansible_play_hosts | length }} hosts"
    verbosity: 0
  run_once: true
  delegate_to: localhost
```

Without `run_once`, this notification would fire once per host. With it, the task runs on the first host in the batch and skips all others.

### `delegate_facts`

By default, facts gathered during a delegated task are assigned to the delegating host, not the delegate target. If you need the facts stored on the target instead, add `delegate_facts: true`:

```yaml
- name: Gather load balancer facts
  ansible.builtin.setup:
  delegate_to: lb01.parasol.example
  delegate_facts: true
```

### Rolling Updates with `serial`

For deploying to many hosts without downtime, use `serial` at the play level to process hosts in batches:

```yaml
- name: Rolling deployment
  hosts: webservers
  serial: 2
```

This processes two hosts at a time. Combined with `delegate_to` for load balancer management, you get a zero-downtime rolling deployment pattern.

### `reset_connection` for Mid-Play Changes

If a task changes the connection parameters mid-play (for example, switching the remote user after granting sudo access), use `meta: reset_connection` to drop and re-establish the SSH connection:

```yaml
- name: Reset connection after user change
  ansible.builtin.meta: reset_connection
```

## Include vs Import

As playbooks grow, splitting them into smaller files makes them easier to maintain. Ansible provides two mechanisms for this, and they behave differently.

### `import_tasks` -- Static (Compile Time)

`ansible.builtin.import_tasks` works like pasting the file contents into your playbook before it runs. Ansible pre-processes imports during playbook parsing:

```yaml
- name: Import application setup tasks
  ansible.builtin.import_tasks:
    file: tasks/setup-app.yml
```

### `include_tasks` -- Dynamic (Runtime)

`ansible.builtin.include_tasks` works like calling a function at runtime. Ansible processes includes during play execution:

```yaml
- name: Include application setup tasks
  ansible.builtin.include_tasks:
    file: tasks/setup-app.yml
```

### When to Use Each

| Feature | `import_tasks` | `include_tasks` |
|---------|---------------|----------------|
| Processing time | Pre-processed (static) | Runtime (dynamic) |
| `--list-tasks` visibility | Shows individual task names | Shows only the include statement |
| Tag inheritance | Tags flow down to all tasks | Tags apply only to the include itself |
| Loops | Cannot be used in loops | Can be used in loops |
| Conditionals | `when` applies to each imported task individually | `when` applies to the include itself |
| Handlers | Can notify and be notified by name | Can notify but handler names are not visible until included |

!!! tip "Import = compile time, include = runtime"
    When in doubt: use `import_tasks` for fixed task files that always run the same way. Use `include_tasks` for conditional or looped task files. The distinction matters most with tags: imported tasks inherit tags from the import statement, but included tasks do not.

### Tag Inheritance Example

This is the most common source of confusion. Consider a task file `tasks/setup-app.yml` with two tasks inside it. If you import it with a tag:

```yaml
- name: Import setup tasks
  ansible.builtin.import_tasks:
    file: tasks/setup-app.yml
  tags:
    - setup
```

Running `--tags setup` executes both tasks inside the file, because the tag flows down.

But if you include it with a tag:

```yaml
- name: Include setup tasks
  ansible.builtin.include_tasks:
    file: tasks/setup-app.yml
  tags:
    - setup
```

Running `--tags setup` triggers the include statement, which then runs the tasks inside. The difference is subtle here but becomes significant in complex playbooks: with `include_tasks`, you can also use the `apply` keyword to pass tags to the included tasks.

### Applying to Roles

Everything about `include_tasks` vs `import_tasks` applies to roles as well. `ansible.builtin.import_role` is static and `ansible.builtin.include_role` is dynamic. When you extract reusable task files into roles in Module 8, the same rules about tags, conditionals, and loops carry over.

## Exercises

### Exercise 1: Error Handling with Blocks

Run the error handling playbook to see block/rescue/always in action:

```bash
cd ansible
ansible-navigator run playbooks/module-07/error-handling.yml --mode stdout
```

Watch the output:

1. The block tasks execute until the simulated migration failure
2. Tasks after the failure in the block are skipped
3. Rescue runs and reports the failed task name using `ansible_failed_task.name`
4. Always runs and logs the deployment attempt

Now run it again with the failure disabled:

```bash
ansible-navigator run playbooks/module-07/error-handling.yml --mode stdout \
  -e "parasol_simulate_failure=false"
```

Notice that rescue does **not** run (no failure occurred), but always still runs. This is the try/catch/finally pattern: always means always.

### Exercise 2: Controlling Task Status

Run the task control playbook:

```bash
ansible-navigator run playbooks/module-07/task-control.yml --mode stdout
```

Observe each technique:

1. The `command` task reports `ok` (not `changed`) thanks to `changed_when: false`
2. The `failed_when` task does not fail despite `grep` returning exit code 1
3. The `assert` task validates preconditions with a clear error message
4. The `ignore_errors` task logs a warning but the playbook continues

Run it a second time -- the output should be identical, confirming idempotency.

### Exercise 3: Working with Tags

Explore the tagged deployment playbook without running it first:

```bash
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout --list-tags
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout --list-tasks --tags configure
```

Then run it with different tag selections:

```bash
# Run only install tasks
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout --tags install

# Run only verify tasks
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout --tags verify

# Run everything (no tag filter)
ansible-navigator run playbooks/module-07/tagged-deployment.yml --mode stdout
```

Notice that the `always`-tagged status task runs in every case, and the `never`-tagged debug dump only runs when explicitly requested with `--tags debug`.

### Exercise 4: Delegation and Run Once

Run the delegation playbook:

```bash
ansible-navigator run playbooks/module-07/delegation.yml --mode stdout
```

Observe the rolling deployment pattern:

1. "Remove from load balancer" runs on localhost but references `inventory_hostname`
2. Deployment tasks run on the target host
3. "Add back to load balancer" runs on localhost
4. The notification task runs only once despite multiple hosts

### Exercise 5: Include vs Import

Run the comparison playbook and explore the differences:

```bash
# First, list tasks to see the visibility difference
ansible-navigator run playbooks/module-07/include-vs-import.yml --mode stdout --list-tasks

# Run with the setup tag
ansible-navigator run playbooks/module-07/include-vs-import.yml --mode stdout --tags setup

# Run everything
ansible-navigator run playbooks/module-07/include-vs-import.yml --mode stdout
```

Compare the `--list-tasks` output: imported tasks show their individual names, while included tasks show only the include statement. Then compare the `--tags setup` run: imported tasks inherit the tag, but included tasks behave differently.

## Summary

In this module you:

- Used `block`, `rescue`, and `always` for structured error handling with rollback logic, and inspected failures with `ansible_failed_task` and `ansible_failed_result`
- Controlled task status reporting with `changed_when` (mandatory on `command`/`shell`) and `failed_when` for commands that use non-zero exit codes legitimately
- Validated preconditions with `ansible.builtin.assert` instead of silently skipping tasks
- Learned why `ignore_errors` is a code smell and when it is genuinely appropriate
- Organized playbooks with tags, including the special `always` and `never` tags, and applied the safety rule: every tag must work standalone
- Delegated tasks to other hosts with `delegate_to` and used `run_once` for notifications and cross-host coordination
- Distinguished `import_tasks` (static, compile-time, tag inheritance) from `include_tasks` (dynamic, runtime, loop-compatible) and learned when to choose each

Lionel and Jordan now handle errors gracefully -- when a migration fails, the playbook rolls back and logs the attempt instead of leaving servers in an inconsistent state. They use tags to run just the deployment or just the verification step. And their growing playbooks are split into reusable task files, ready to be extracted into roles.

## Next Steps

Next: [Module 8 -- Roles and Collections](8-roles-and-collections.md)
