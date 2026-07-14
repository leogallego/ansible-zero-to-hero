# Module 6: Protecting Your Data

## Learning Objectives

By the end of this module you will be able to:

- Encrypt sensitive variables using `ansible-vault encrypt_string` and embed them in plaintext YAML files
- Encrypt entire files with `ansible-vault encrypt` and manage them with `edit`, `view`, `rekey`, and `decrypt`
- Manage vault passwords using password files and environment variables
- Run vault-protected playbooks with `ansible-navigator`
- Use lookup plugins (`ansible.builtin.file`, `ansible.builtin.env`, `ansible.builtin.pipe`, `ansible.builtin.password`) to source data from outside playbooks
- Protect sensitive task output from logs using `no_log: true`

## The Story So Far

Lionel's team has been productive. They have parameterized playbooks with variables, deployed templated configuration files, and set up handlers to restart services when configurations change. The Parasol Tech platform playbooks are checked into the team's Git repository, and everyone is contributing.

Then it happens. During a routine code review, Jordan notices that `group_vars/production.yml` contains the production database password in plaintext: `parasol_db_password: "Sup3rS3cret!"`. Worse, the file has been in version control for three weeks. The security team flags it during an audit. Even though the password is rotated immediately, the plaintext value is permanently baked into the Git history. "We need to treat secrets differently from regular variables," Lionel says. "Passwords, API keys, certificates -- none of these belong in plaintext, even in a private repository."

Jordan pulls up the Ansible documentation. "Ansible has this built in. It is called Vault. We can encrypt individual values right inside our existing variable files, or encrypt entire files. Either way, the secrets live alongside our code but are protected at rest. And there are lookup plugins to pull secrets from files, environment variables, or external commands -- so we are not limited to hardcoding anything." The team spends an afternoon learning Vault and locking down every secret in the repository. By the end of the day, the security team signs off.

## The Problem: Secrets in Plaintext

Before diving into solutions, it is worth understanding why plaintext secrets are dangerous -- even in a private repository.

Consider this line in `group_vars/production.yml`:

```yaml
parasol_db_password: "Sup3rS3cret!"
```

The moment this file is committed, the password exists in Git history forever. Running `git rm` or overwriting the file does not help -- anyone with repository access can run `git log -p` and find the plaintext value. Rotating the password fixes the immediate risk, but the leaked value remains in the history.

Secrets fall into the category of **data at rest** when they sit in files on disk or in version control. Ansible Vault protects data at rest by encrypting it with AES-256, the same standard used by governments and financial institutions. But there is a second category -- **data in use** -- that Vault alone does not cover. When Ansible decrypts a value and passes it to a task, the plaintext may appear in logs, callback output, or task results. Protecting data in use requires `no_log: true`, which we will cover later in this module.

!!! warning "Data at rest vs. data in use"
    Ansible Vault protects secrets **at rest** -- encrypted on disk and in version control. Once Ansible decrypts a value and uses it in a task, the plaintext exists in memory and may appear in logs or artifacts. Vault does not prevent runtime leaks. Always combine vault encryption with `no_log: true` on tasks that handle sensitive values.

## Ansible Vault: Encrypting Variables

The most common real-world pattern is encrypting individual variable values while keeping the rest of the YAML file readable. This is called **variable-level encryption**, and the tool for it is `ansible-vault encrypt_string`.

### Encrypting a Single Value

To encrypt a string value and assign it to a variable name:

```bash
ansible-vault encrypt_string \
  --vault-password-file .vault_password \
  'Sup3rS3cret!' \
  --name 'parasol_db_password'
```

This produces output like:

```yaml
parasol_db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          63306536653963613135303839343061383532316130623562653463623437376665
          3738633237343963643339353833396533626562373934340a626431646537363633
          ...
```

The `!vault |` tag tells Ansible this value is encrypted. You paste this block into any YAML variable file, and the surrounding plaintext remains readable.

### Embedding Encrypted Values in Variable Files

The power of `encrypt_string` is that encrypted values live alongside plaintext variables in the same file:

```yaml
---
parasol_db_description: "Production PostgreSQL database"
parasol_db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          63306536653963613135303839343061383532316130623562653463623437376665
          ...
```

Anyone reading this file can see that `parasol_db_description` is "Production PostgreSQL database" and that `parasol_db_password` exists and is encrypted. They know the variable name, its purpose from context, and that it contains a secret -- without seeing the actual value. This is the ideal balance of transparency and security.

### Using Encrypted Variables in Playbooks

Encrypted variables are completely transparent to playbooks. Ansible decrypts them automatically when the vault password is provided:

```yaml
- name: Display the decrypted database password
  ansible.builtin.debug:
    msg: "Database password is {{ parasol_db_password }}"
    verbosity: 0
```

Without the vault password, Ansible refuses to run:

```text
ERROR! Attempting to decrypt but no vault secrets found
```

## Ansible Vault: Encrypting Files

Sometimes it makes more sense to encrypt an entire file rather than individual values. This is appropriate when every variable in a file is sensitive (e.g., a file full of API credentials) or when you want to encrypt non-YAML content like certificates or license keys.

### Encrypting a File

Start with a plaintext file:

```yaml
---
parasol_api_key: "l9bTqfBlbXTQiDaJMqgPJ1VdeFLfId98"
parasol_api_secret: "k8mPq2nRtYwXzA3bC5dE7fG9hJ1lN4oQ"
```

Encrypt it in place:

```bash
ansible-vault encrypt \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml
```

The file is now opaque:

```text
$ANSIBLE_VAULT;1.1;AES256
36313338626336336233626231663835643435393434623535613530636365363034
...
```

### Managing Encrypted Files

Ansible Vault provides four commands for working with encrypted files:

| Command | What it does |
|---------|-------------|
| `ansible-vault view` | Decrypt and display contents without modifying the file |
| `ansible-vault edit` | Decrypt into a temporary file, open in `$EDITOR`, re-encrypt on save |
| `ansible-vault rekey` | Change the encryption password without decrypting to plaintext |
| `ansible-vault decrypt` | Remove encryption entirely (use with caution) |

```bash
# View without modifying
ansible-vault view \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml

# Edit in place
ansible-vault edit \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml

# Change the password
ansible-vault rekey \
  --vault-password-file .vault_password \
  --new-vault-password-file .vault_password_new \
  playbooks/module-06/vars/api_credentials.yml
```

### Variable vs. File Encryption

| Aspect | Variable encryption (`encrypt_string`) | File encryption (`encrypt`) |
|--------|---------------------------------------|----------------------------|
| Readability | Plaintext context preserved | Entire file is opaque |
| Searchability | `grep` finds variable names | `grep` finds nothing useful |
| Granularity | Mix secrets and non-secrets in one file | All-or-nothing |
| Version control diffs | Meaningful diffs for plaintext portions | Diffs are opaque binary blobs |
| Best for | A few secrets among many variables | Files where everything is sensitive |

In practice, most teams use variable-level encryption for inventory and role variables, and file-level encryption for certificates, license keys, and credential bundles.

## Managing Vault Passwords

Vault encryption is only as strong as your password management. There are several ways to provide the vault password to Ansible.

### Password Files

The simplest approach is a file containing the password:

```bash
echo 'parasol-vault-password' > .vault_password
chmod 600 .vault_password
```

Use it with the `--vault-password-file` flag:

```bash
ansible-vault encrypt_string \
  --vault-password-file .vault_password \
  'my-secret' --name 'my_variable'
```

!!! danger "Never commit vault password files"
    Vault password files (`.vault_password`, `.vault_password_dev`, etc.) must NEVER be committed to version control. Add them to `.gitignore` immediately. If you commit a vault password alongside vault-encrypted files, anyone with repository access can decrypt everything -- defeating the entire purpose of encryption.

### Environment Variables

Set `ANSIBLE_VAULT_PASSWORD_FILE` to avoid passing `--vault-password-file` on every command:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-vault encrypt_string 'my-secret' --name 'my_variable'
```

This is especially useful in CI/CD pipelines and shared development environments where the password file path is standardized.

### Password Scripts

For dynamic password retrieval (from a password manager, secrets service, or hardware token), point `--vault-password-file` at an executable script:

```bash
#!/bin/bash
# .vault_password_script.sh
# Retrieve vault password from a secrets manager
pass show ansible/vault-password 2>/dev/null
```

```bash
chmod 700 .vault_password_script.sh
ansible-vault view \
  --vault-password-file .vault_password_script.sh \
  playbooks/module-06/vars/api_credentials.yml
```

Ansible detects that the file is executable and runs it, using its standard output as the password. This lets teams integrate vault with any secrets management tool.

### Vault IDs (Preview)

When a project grows to manage multiple environments, you may need different vault passwords for dev, staging, and production. Vault IDs provide this capability. We will cover vault IDs in depth in Module 10 when we discuss packaging and deployment. For now, know that the pattern exists and that all the single-password techniques you learn here extend naturally to multi-password setups.

## Running Vault with ansible-navigator

Throughout this course, you have been using `ansible-navigator` to run playbooks. Vault integrates smoothly, but there are a few patterns specific to navigator.

### Method 1: Environment Variable (Recommended)

The simplest approach is to set the environment variable before running navigator:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-navigator run playbooks/module-06/vault-string-demo.yml --mode stdout
```

The `ANSIBLE_VAULT_PASSWORD_FILE` environment variable is automatically passed through to the execution environment, so this works identically whether navigator runs locally or inside a container.

### Method 2: Passthrough Arguments

You can pass vault arguments directly to the underlying `ansible-playbook` command using `--` as a separator:

```bash
ansible-navigator run playbooks/module-06/vault-string-demo.yml \
  --mode stdout -- --vault-password-file .vault_password
```

Everything after `--` is passed through to `ansible-playbook` unchanged.

### Vault Commands Through Navigator

You can run vault commands inside the execution environment using `ansible-navigator exec`:

```bash
ansible-navigator exec -- ansible-vault encrypt_string \
  --vault-password-file .vault_password 'my-secret' --name 'my_variable'
```

This ensures you are using the same Ansible version inside the execution environment as the one that will run your playbooks.

!!! warning "Interactive prompts do not work with navigator"
    The `--ask-vault-pass` flag does NOT work with `ansible-navigator` in default mode because interactive prompts are disabled. Always use password files or environment variables with navigator.

## Lookup Plugins: Sourcing Data from Outside

Vault is not the only way to handle sensitive data. **Lookup plugins** let you pull values from external sources at runtime -- files, environment variables, commands, or generated passwords. Lookups complement vault by keeping secrets out of variable files entirely.

### `ansible.builtin.file` -- Read a File

Read the contents of a file on the control node:

```yaml
- name: Read the MOTD banner from a file
  ansible.builtin.debug:
    msg: "{{ lookup('ansible.builtin.file', 'files/motd_banner.txt') }}"
    verbosity: 0
```

This is useful for certificates, license keys, or any content that already exists as a file and should not be duplicated into variables.

### `ansible.builtin.env` -- Read an Environment Variable

Read an environment variable from the control node:

```yaml
- name: Read the deploy token from the environment
  ansible.builtin.debug:
    msg: "Deploy token: {{ lookup('ansible.builtin.env', 'PARASOL_DEPLOY_TOKEN') }}"
    verbosity: 0
```

If the variable is not set, the lookup returns an empty string by default. You can make it fail on a missing variable:

```yaml
msg: "{{ lookup('ansible.builtin.env', 'PARASOL_DEPLOY_TOKEN', default=undef()) }}"
```

### `ansible.builtin.pipe` -- Run a Command

Execute a command on the control node and use its standard output:

```yaml
- name: Get the current user
  ansible.builtin.debug:
    msg: "Running as: {{ lookup('ansible.builtin.pipe', 'whoami') }}"
    verbosity: 0
```

This is useful for extracting secrets from CLI tools like `pass`, `aws secretsmanager`, or `vault` (HashiCorp).

### `ansible.builtin.password` -- Generate or Retrieve a Password

Generate a random password and optionally store it in a file:

```yaml
- name: Generate a random password
  ansible.builtin.debug:
    msg: "Generated: {{ lookup('ansible.builtin.password', '/dev/null length=20 chars=ascii_letters,digits') }}"
    verbosity: 0
```

Using `/dev/null` as the path generates a new password each time without saving it. To persist the password across runs, specify a file path:

```yaml
parasol_app_secret: "{{ lookup('ansible.builtin.password', 'credentials/app_secret length=32') }}"
```

Ansible creates the file on first run and reads the stored password on subsequent runs, ensuring the value stays consistent.

### `lookup()` vs. `query()`

You will see two syntaxes for calling lookup plugins:

```yaml
# lookup() returns a string (comma-separated for multiple results)
msg: "{{ lookup('ansible.builtin.file', 'file1.txt', 'file2.txt') }}"

# query() returns a list (useful in loops)
loop: "{{ query('ansible.builtin.file', 'file1.txt', 'file2.txt') }}"
```

Use `lookup()` when you need a single string value. Use `query()` when you need a list, especially in `loop:` constructs.

!!! info "Lookups run on the control node"
    All lookup plugins execute on the Ansible control node, not on target hosts. The `ansible.builtin.env` lookup reads environment variables from the machine running Ansible. If you need to read a file or environment variable from a remote host, use the `ansible.builtin.slurp` module or `ansible.builtin.command` with `register` instead.

## Protecting Sensitive Output: `no_log`

Vault protects secrets at rest, but what about runtime? When Ansible runs a task, it logs the task parameters and results to the console, log files, and callback plugins. If a task handles a password, the plaintext value may appear in the output.

The `no_log: true` directive suppresses all output for a task:

```yaml
- name: Create application database user
  community.postgresql.postgresql_user:
    name: "parasol_app"
    password: "{{ parasol_db_password }}"
    state: present
  no_log: true
```

With `no_log: true`, Ansible replaces the task output with `censored`:

```text
TASK [Create application database user] ****
ok: [db-01] => {"censored": "the output has been hidden due to the fact
that 'no_log: true' was specified for this result"}
```

Without it, the password appears in the output:

```text
TASK [Create application database user] ****
ok: [db-01] => {"changed": false, "password": "Sup3rS3cret!", ...}
```

### When to Use `no_log`

Use `no_log: true` on any task that handles sensitive values:

- Tasks that pass passwords as parameters
- Tasks that set API keys or tokens in configuration
- Tasks using `ansible.builtin.uri` with authentication headers
- Tasks that loop over a list containing secrets

!!! tip "ansible-lint catches missing no_log"
    The `ansible-lint` tool (which you will learn in Module 9) includes a rule called `no-log-password` that flags tasks with password parameters missing `no_log: true`. This is an automated safety net -- but understanding why `no_log` matters is more important than relying on the linter to catch it.

### The Debugging Trade-off

`no_log: true` makes debugging harder because you cannot see task parameters or results. When troubleshooting a failing task, you may need to temporarily remove `no_log` in a dev environment, diagnose the issue, and then restore it. Never leave `no_log` disabled in production playbooks.

## Best Practices: What to Vault, What Not to Vault

Not everything needs encryption. Over-vaulting creates friction (every developer needs the vault password to run any playbook), and under-vaulting leaves secrets exposed.

### What to Encrypt

- Passwords and passphrases
- API keys and tokens
- TLS/SSL private keys and certificates
- Database connection strings with credentials
- SSH private keys
- License keys

### What NOT to Encrypt

- Package names (`parasol_packages`)
- Port numbers (`parasol_http_port: 8080`)
- Feature flags (`parasol_monitoring_enabled: true`)
- File paths (`parasol_log_dir: "/var/log/parasol"`)
- Non-sensitive configuration values

The rule is simple: if the value would cause a security incident if exposed, encrypt it. Everything else stays in plaintext for readability and ease of use.

### The `vault_` Prefix Pattern

When you encrypt individual variables, the variable names remain visible and searchable. But when you encrypt entire files (like `group_vars/production/vault.yml`), `grep` cannot find anything inside them.

The recommended pattern splits variables into two files per group:

```text
group_vars/production/
    vars.yml          # Plaintext references (searchable)
    vault.yml         # Encrypted values
```

In `vault.yml` (encrypted):

```yaml
vault_parasol_db_password: "Sup3rS3cret!"
```

In `vars.yml` (plaintext):

```yaml
parasol_db_password: "{{ vault_parasol_db_password }}"
```

This way, `grep parasol_db_password` finds the reference in `vars.yml`, and the actual value is safely encrypted in `vault.yml`. Ansible automatically loads both files from the group directory and resolves the reference at runtime.

### Vault in Version Control

Vault-encrypted files are safe to commit to version control. The encrypted content is an opaque AES-256 blob -- without the vault password, it is computationally infeasible to recover the plaintext. This is the key difference from the plaintext problem we started with: encrypted secrets in Git history are not a security risk.

### Password Rotation with `rekey`

When you need to change the vault password (e.g., when a team member leaves), use `ansible-vault rekey` to re-encrypt all vault-protected files with a new password. This is the correct way to rotate vault passwords -- you do not need to decrypt and re-encrypt each file manually.

## Exercises

### Exercise 1: Encrypt a Variable with `ansible-vault encrypt_string`

Create a vault password file and encrypt a database password:

```bash
cd ansible
echo 'parasol-vault-password' > .vault_password
chmod 600 .vault_password
```

Encrypt a value:

```bash
ansible-vault encrypt_string \
  --vault-password-file .vault_password \
  'Sup3rS3cret!' \
  --name 'parasol_db_password'
```

Copy the output. Open `playbooks/module-06/vars/db_secrets.yml` and compare it to the output -- this file already has the encrypted value embedded alongside a plaintext variable.

Now run the companion playbook:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-navigator run playbooks/module-06/vault-string-demo.yml --mode stdout
```

Try running it without the vault password:

```bash
unset ANSIBLE_VAULT_PASSWORD_FILE
ansible-navigator run playbooks/module-06/vault-string-demo.yml --mode stdout
```

You should see `ERROR! Attempting to decrypt but no vault secrets found`. This confirms that the encrypted value cannot be used without the correct password.

### Exercise 2: Encrypt and Manage a Whole File

Create a plaintext secrets file:

```bash
cat > playbooks/module-06/vars/api_credentials.yml << 'EOF'
---
parasol_api_key: "l9bTqfBlbXTQiDaJMqgPJ1VdeFLfId98"
parasol_api_secret: "k8mPq2nRtYwXzA3bC5dE7fG9hJ1lN4oQ"
EOF
```

Encrypt it:

```bash
ansible-vault encrypt \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml
```

View the encrypted file with `cat` -- you should see the `$ANSIBLE_VAULT;1.1;AES256` header followed by hex-encoded data:

```bash
cat playbooks/module-06/vars/api_credentials.yml
```

Now view the decrypted contents:

```bash
ansible-vault view \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml
```

Edit the file and add a third variable (`parasol_api_endpoint: "https://api.parasol.example"`):

```bash
ansible-vault edit \
  --vault-password-file .vault_password \
  playbooks/module-06/vars/api_credentials.yml
```

Run the companion playbook:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-navigator run playbooks/module-06/vault-file-demo.yml --mode stdout
```

### Exercise 3: Vault in Inventory group_vars

This exercise uses the recommended split-file pattern for managing secrets in structured inventories.

Examine the two files that have been set up in `inventory/group_vars/production/`:

- `vars.yml` -- plaintext references
- `vault.yml` -- encrypted values

```bash
cat inventory/group_vars/production/vars.yml
ansible-vault view \
  --vault-password-file .vault_password \
  inventory/group_vars/production/vault.yml
```

Run the companion playbook:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
ansible-navigator run playbooks/module-06/vault-groupvars-demo.yml --mode stdout
```

Verify that `grep` can find the variable name in the plaintext file:

```bash
grep parasol_db_password inventory/group_vars/production/vars.yml
```

You should see the reference `parasol_db_password: "{{ vault_parasol_db_password }}"`. The actual value is encrypted in `vault.yml`, but the variable name is searchable in `vars.yml`. This is the recommended pattern for production inventories.

### Exercise 4: Lookup Plugins

Set an environment variable for the `env` lookup demo:

```bash
export PARASOL_DEPLOY_TOKEN="token-abc-123"
```

Run the lookups playbook:

```bash
ansible-navigator run playbooks/module-06/lookups-demo.yml --mode stdout
```

Observe the four lookups in action:

1. **`ansible.builtin.file`** reads the banner from `files/motd_banner.txt`
2. **`ansible.builtin.env`** reads `PARASOL_DEPLOY_TOKEN` from the environment
3. **`ansible.builtin.pipe`** runs `whoami` and captures the output
4. **`ansible.builtin.password`** generates a random 20-character password

Try unsetting the environment variable and running again:

```bash
unset PARASOL_DEPLOY_TOKEN
ansible-navigator run playbooks/module-06/lookups-demo.yml --mode stdout
```

Notice that the `env` lookup returns an empty string instead of failing. In production, you would use `default=undef()` to make a missing variable an error.

### Exercise 5: Protecting Output with `no_log`

Run the no-log demo playbook:

```bash
ansible-navigator run playbooks/module-06/no-log-demo.yml --mode stdout
```

Observe the difference between the two tasks:

1. The **unprotected** task shows the password value in the output
2. The **protected** task shows `censored` instead

Now edit `playbooks/module-06/no-log-demo.yml` and add `no_log: true` to the unprotected task. Run it again and confirm that both tasks now show `censored`.

This is the "data in use" protection that complements Vault's "data at rest" encryption. Always use `no_log: true` on tasks that handle sensitive values.

## Summary

In this module you:

- Understood why plaintext secrets in version control are dangerous -- even after deletion, they persist in Git history
- Encrypted individual variable values with `ansible-vault encrypt_string` and embedded them in readable YAML files
- Encrypted entire files with `ansible-vault encrypt` and managed them with `view`, `edit`, `rekey`, and `decrypt`
- Managed vault passwords with password files, environment variables, and executable scripts
- Ran vault-protected playbooks with `ansible-navigator` using `ANSIBLE_VAULT_PASSWORD_FILE` and passthrough arguments
- Used four lookup plugins (`file`, `env`, `pipe`, `password`) to source data from outside playbooks at runtime
- Protected sensitive task output from logs using `no_log: true`
- Applied the `vault_` prefix pattern to keep variable names searchable while values stay encrypted

Lionel and Jordan have locked down every secret in the Parasol Tech repository. Passwords are encrypted with Vault, API keys are sourced from environment variables, and `no_log` prevents sensitive values from leaking into logs. The security team is satisfied, and the team has a clear decision framework for what to encrypt and what to leave in plaintext.

## Next Steps

Next: [Module 8 -- Roles and Collections](8-roles-and-collections.md)
