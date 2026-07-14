# Module 11: CI/CD for Ansible Content

## Learning Objectives

By the end of this module you will be able to:

- Explain why CI/CD for Ansible tests your automation code, not your infrastructure, and how this differs from using Ansible in application CI/CD pipelines
- Create a GitHub Actions workflow that runs `ansible-lint` on every pull request using the official `ansible/ansible-lint` composite action
- Create a GitHub Actions workflow that runs Molecule integration tests in CI with color output and artifact upload on failure
- Configure `tox-ansible` to produce a CI-compatible test matrix using `--gh-matrix` and run the full collection test suite in a GitHub Actions pipeline
- Manage secrets in CI for Ansible Vault passwords and Galaxy tokens using GitHub repository secrets
- Add status badges to the collection README and understand branch protection as a best practice for enforcing quality gates

## The Story So Far

The CoP has been growing. Six teams now contribute roles to `parasoltech.infrastructure`, and the collection has expanded from one role to four. The process is clear: run `ansible-lint`, run `molecule test`, run `tox --ansible` before merging. Everyone knows the rules.

Then a Friday afternoon merge breaks everything.

Jordan reviews a PR from the networking team, checks the code visually, but does not run the test suite -- the change looks simple enough. By Monday morning, staging deployments fail across three teams. The culprit: a typo in a Jinja2 template that `ansible-lint` would have caught in seconds.

"The problem is not the process," Lionel tells the CoP meeting. "The problem is that the process depends on people remembering. We need machines to enforce it."

The team agrees to automate their quality gates: every pull request must pass linting, integration tests, and sanity checks before it can be merged. No exceptions. By the end of the week, the collection repository has three new workflow files in `.github/workflows/`. A green checkmark means the change is safe to merge. A red X means it is not. No one needs to remember to run the tests -- GitHub does it for them.

## CI/CD for Ansible Content vs CI/CD with Ansible

Before writing any workflows, it is important to understand what CI/CD means in the context of Ansible content.

There are two very different uses of the phrase "CI/CD and Ansible":

| | CI/CD *for* Ansible | CI/CD *with* Ansible |
|---|---|---|
| **What it means** | Testing your automation code | Using Ansible to deploy applications |
| **What runs** | ansible-lint, molecule, ansible-test, tox-ansible | ansible-playbook against real infrastructure |
| **Where it runs** | Ephemeral CI runner (GitHub Actions, GitLab CI) | AAP Controller, AWX, or direct SSH |
| **What it validates** | Code quality, syntax, role behavior | Infrastructure state |
| **Covered in** | This module | Module 12 (AAP) |

This module covers the first column: testing automation code in an ephemeral runner. Nothing touches production. The CI runner applies your role to localhost, checks results, and is destroyed. Module 12 covers the second column -- using Ansible Automation Platform to execute automation against real infrastructure with RBAC, audit trails, and webhook integration.

!!! info "CI for Ansible tests your code, not your infrastructure"
    This is the single most important distinction in this module. If you take away one thing, let it be this: CI for Ansible content validates your automation code in a disposable runner. It never touches production infrastructure.

### The CI Test Pyramid

The test pyramid from Module 9 maps directly to CI stages:

```text
         ┌─────────────┐
         │ Integration  │  Molecule      -- minutes
         │  (Molecule)  │
        ┌┴─────────────┴┐
        │   Unit Tests   │  pytest        -- seconds
        │  (pytest)      │
       ┌┴───────────────┴┐
       │  Sanity Tests    │  ansible-test  -- seconds
       │  (ansible-test)  │
      ┌┴─────────────────┴┐
      │   Lint             │  ansible-lint  -- seconds
      │   (ansible-lint)   │
      └───────────────────┘
```

Run from bottom to top: lint first (fast, cheap), integration last (slow, thorough). Fail fast at the cheapest layer. Every tool here is the same tool you configured in Module 9 -- the only difference is that now a machine runs them on every pull request instead of relying on a developer to remember.

### GitHub Actions Fundamentals

GitHub Actions is the CI/CD platform built into GitHub. The key concepts:

| Concept | Description |
|---------|-------------|
| **Workflow** | A YAML file in `.github/workflows/` that defines an automated process |
| **Trigger** | The event that starts the workflow (`push`, `pull_request`, `schedule`) |
| **Job** | A set of steps that run on the same runner |
| **Step** | A single command or action within a job |
| **Runner** | The virtual machine that executes the job (`ubuntu-24.04`) |
| **Action** | A reusable unit of work (`actions/checkout@v4`, `ansible/ansible-lint@v26`) |
| **Secret** | An encrypted value stored in the repository, injected at runtime |

Workflows are event-driven. When a developer opens a pull request, GitHub sees that the event matches a workflow trigger and spins up a fresh runner to execute the defined jobs.

## Linting in CI with ansible-lint

The first and fastest quality gate is linting. The official `ansible/ansible-lint` GitHub Action wraps the `ansible-lint` tool in a composite action that handles Python setup, installation, and execution in a single step.

### The Workflow File

Create `.github/workflows/ansible-lint.yml`:

```yaml
---
name: Ansible Lint

on:
  push:
    branches: [main]
    paths:
      - 'ansible/**'
  pull_request:
    branches: [main]
    paths:
      - 'ansible/**'

jobs:
  lint:
    name: Ansible Lint
    runs-on: ubuntu-24.04
    steps:
      - name: Check out code
        uses: actions/checkout@v4

      - name: Run ansible-lint
        uses: ansible/ansible-lint@v26
        with:
          working_directory: ansible/collections/parasoltech/infrastructure
```

!!! tip "Version pinning"
    The `@v26` tag is a rolling major version -- it always points to the latest `v26.x.x` release. This is convenient for a course, but for production workflows you should pin to a specific version (for example, `@v26.6.0`) to avoid unexpected behavior when the action updates.

Let us walk through each section:

**Triggers (`on:`)**

- `push: branches: [main]` -- runs when code is pushed directly to the `main` branch
- `pull_request: branches: [main]` -- runs when a PR is opened or updated against `main`

Together, these ensure that both the PR itself and the merge result are validated.

**Runner (`runs-on: ubuntu-24.04`)**

The job runs on an Ubuntu 24.04 LTS virtual machine. Always specify the version explicitly -- `ubuntu-latest` is a moving target that can change without warning.

**Steps**

1. **Checkout**: `actions/checkout@v4` clones the repository into the runner
2. **Lint**: `ansible/ansible-lint@v26` installs and runs `ansible-lint`. The `working_directory` input tells it where to find the collection -- essential for monorepo layouts where the Ansible content is not at the repository root

The `ansible-lint` action reads the `.ansible-lint` configuration file from Module 9 automatically. No additional configuration is needed.

### Installing Collection Dependencies

If your collection depends on other collections (listed in `requirements.yml`), the action installs them before linting. The `ansible/ansible-lint` action handles this transparently through `ansible-lint`'s built-in dependency resolution.

## Molecule Integration Tests in CI

Linting catches static problems. Molecule catches dynamic ones -- problems that only appear when you actually apply a role. In CI, Molecule runs with no interactive terminal, no Docker-in-Docker, and no human watching the output.

### The Workflow File

Create `.github/workflows/molecule.yml`:

```yaml
---
name: Molecule Tests

on:
  pull_request:
    branches: [main]
    paths:
      - 'ansible/**'
      - '.github/workflows/molecule.yml'

jobs:
  molecule:
    name: Molecule - ${{ matrix.scenario }}
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: ansible/collections/parasoltech/infrastructure
    strategy:
      fail-fast: false
      matrix:
        scenario:
          - integration_webserver
    env:
      PY_COLORS: '1'
      ANSIBLE_FORCE_COLOR: 'true'
    steps:
      - name: Check out code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install ansible-dev-tools

      - name: Run Molecule tests
        run: molecule test -s ${{ matrix.scenario }}

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: molecule-logs-${{ matrix.scenario }}
          path: ansible/collections/parasoltech/infrastructure/extensions/molecule/${{ matrix.scenario }}/.molecule/
```

This workflow introduces several new concepts:

**Path filtering (`paths:`)**

The `paths` key limits the workflow to changes inside `ansible/` or the workflow file itself. A documentation-only change does not trigger a Molecule run, saving CI minutes.

**Matrix strategy (`strategy.matrix`)**

The matrix runs the job once per scenario. With one scenario (`integration_webserver`), there is one job. When the CoP adds a second role with its own Molecule scenario, they add one line to the matrix and CI handles the rest.

Setting `fail-fast: false` ensures all scenarios run to completion even if one fails. This way you see the full picture, not just the first failure.

**Color output**

CI runners have no terminal, so Ansible and Python disable color output by default. Setting `PY_COLORS: '1'` and `ANSIBLE_FORCE_COLOR: 'true'` as environment variables restores color in the CI logs, making failures much easier to read.

**Artifact upload on failure**

The `if: failure()` condition on the upload step means it only runs when the test fails. It uploads the Molecule `.molecule/` directory, which contains ansible logs, as a downloadable artifact. When a test fails at 2 AM, the debugging information is waiting in the Actions tab the next morning.

!!! tip "DIY vs official action"
    Unlike `ansible-lint`, there is no official Molecule action. This workflow takes the DIY approach: set up Python, install `ansible-dev-tools` (which includes Molecule), and run `molecule test`. This gives you full control over the Python version, dependencies, and Molecule configuration.

## Collection Testing with tox-ansible

`tox-ansible` orchestrates all test types -- lint, sanity, unit, and integration -- through a single interface. Its `--gh-matrix` flag produces JSON output that GitHub Actions can consume to create a dynamic test matrix.

### The Two-Job Pattern

The workflow uses two jobs:

1. **`matrix-gen`**: Runs `tox --ansible --gh-matrix` to discover all test environments and outputs the JSON
2. **`test`**: Reads the JSON and runs each test environment in parallel

This pattern means you never manually update the CI matrix. Add a new Molecule scenario or a new test file, and `tox-ansible` discovers it automatically on the next run.

### The Workflow File

Create `.github/workflows/collection-test.yml`:

```yaml
---
name: Collection Tests

on:
  push:
    branches: [main]
    paths:
      - 'ansible/**'
  pull_request:
    branches: [main]
    paths:
      - 'ansible/**'

jobs:
  matrix-gen:
    name: Generate test matrix
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: ansible/collections/parasoltech/infrastructure
    outputs:
      envlist: ${{ steps.generate-matrix.outputs.envlist }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install tox tox-ansible
      - name: Generate matrix
        id: generate-matrix
        run: python -m tox --ansible --gh-matrix --conf tox-ansible.ini

  test:
    name: ${{ matrix.entry.name }}
    needs: matrix-gen
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: ansible/collections/parasoltech/infrastructure
    strategy:
      fail-fast: false
      matrix:
        entry: ${{ fromJSON(needs.matrix-gen.outputs.envlist) }}
    env:
      PY_COLORS: '1'
      ANSIBLE_FORCE_COLOR: 'true'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install tox tox-ansible
      - run: tox --ansible -c tox-ansible.ini -e ${{ matrix.entry.name }}

  all_green:
    if: always()
    needs: [test]
    runs-on: ubuntu-24.04
    steps:
      - uses: re-actors/alls-green@release/v1
        with:
          jobs: ${{ toJSON(needs) }}
```

Let us break down the key parts:

**Matrix generation**

The `matrix-gen` job runs `tox --ansible --gh-matrix --conf tox-ansible.ini` and captures the output. The `--gh-matrix` flag tells `tox-ansible` to write a JSON array to `$GITHUB_OUTPUT` under the key `envlist`. Each entry in the array has a `name` field that corresponds to a tox environment like `sanity-py3.12-2.19` or `unit-py3.12-2.19`.

The `outputs` section exposes this JSON to downstream jobs through `needs.matrix-gen.outputs.envlist`.

**Dynamic matrix consumption**

The `test` job uses `fromJSON(needs.matrix-gen.outputs.envlist)` to parse the JSON array into a GitHub Actions matrix. Each entry spawns a separate parallel job that runs the corresponding tox environment.

This is the same `tox --ansible` you used locally in Module 9. Same configuration file, same commands, same results -- just running on a cloud runner instead of your laptop.

**The `all_green` aggregation job**

With a dynamic matrix that might produce 4, 6, or 12 test jobs, you need a single status check to report the overall result. The `all_green` job depends on all `test` matrix jobs and uses the `re-actors/alls-green` action to check that every one of them passed.

!!! tip "The `all_green` pattern: one gate to rule them all"
    With a matrix of 6 test environments, add one `all_green` job that depends on all matrix jobs. Make `all_green` the single required check in branch protection. It adapts automatically as you add or remove environments -- no need to update the branch protection rules every time the matrix changes.

The `if: always()` is critical. Without it, the `all_green` job is skipped when any upstream job fails -- which is exactly when you need it to report a failure.

### Reusable Workflows

The `ansible/ansible-content-actions` repository provides production-grade reusable workflows for common Ansible content CI tasks. These are maintained by the Ansible team and cover changelog validation, release automation, and more.

For example, a changelog validation workflow:

```yaml
---
name: Changelog Check

on:
  pull_request:
    branches: [main]

jobs:
  changelog:
    uses: ansible/ansible-content-actions/.github/workflows/changelog.yaml@main
```

One line in the `jobs` section replaces an entire workflow definition. The `uses` key points to a workflow file in another repository, and GitHub Actions handles the rest.

!!! tip "If it passes locally, it must pass in CI"
    The entire point of `tox-ansible` is to guarantee this. If a test passes locally but fails in CI, something is wrong with your environment isolation -- and that is a bug worth fixing.

## Secrets and Security in CI

Some CI tasks need sensitive values: Vault passwords for encrypted variables, Galaxy tokens for publishing collections, cloud credentials for integration tests. These must never appear in code.

### GitHub Repository Secrets

GitHub stores secrets encrypted and injects them into workflows at runtime. They are:

- **Encrypted at rest**: GitHub cannot read them after they are saved
- **Masked in logs**: If a secret value appears in stdout, GitHub replaces it with `***`
- **Scoped to the repository**: Each repository has its own secrets
- **Not available to forks**: Pull requests from forked repositories cannot access secrets, preventing exfiltration

To add a secret, go to **Settings → Secrets and variables → Actions → New repository secret**.

### Vault Password in CI

When Molecule scenarios use encrypted variables, the Molecule workflow needs the Vault password. The pattern:

1. Store the Vault password as a GitHub secret called `VAULT_PASSWORD`
2. In the workflow, write the secret to a temporary file
3. Point Molecule at the file via an environment variable
4. The file is automatically cleaned up when the runner is destroyed

Add these steps to the Molecule workflow before the `Run Molecule tests` step:

```yaml
      - name: Write vault password file
        run: echo "$VAULT_PASSWORD" > .vault-password
        env:
          VAULT_PASSWORD: ${{ secrets.VAULT_PASSWORD }}

      - name: Run Molecule tests
        run: molecule test -s ${{ matrix.scenario }}
        env:
          ANSIBLE_VAULT_PASSWORD_FILE: .vault-password
```

!!! warning "Secrets never belong in code"
    Every CI platform provides a secrets mechanism. Store the secret in the platform, reference by name in the workflow, and the platform injects it at runtime. Secrets are masked in logs and not available to PRs from forks.

### Galaxy Tokens

Publishing collections to Galaxy or Automation Hub requires an API token. Store it as a secret and reference it in workflows:

```yaml
      - name: Publish collection
        run: >-
          ansible-galaxy collection publish
          parasoltech-infrastructure-*.tar.gz
          --server https://galaxy.ansible.com/
        env:
          ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN: ${{ secrets.GALAXY_TOKEN }}
```

### Fork Security

When someone forks your repository and opens a PR, the workflow runs on the fork's code. GitHub deliberately does not inject repository secrets into these runs. This is a security feature: a malicious fork could add a step that prints `${{ secrets.GALAXY_TOKEN }}` to the logs.

Design your workflows so that tests that do not need secrets (linting, sanity tests, unit tests) pass without them, and tests that require secrets (publishing, encrypted integration tests) are skipped or gated with an `if: github.event.pull_request.head.repo.full_name == github.repository` condition.

## Status Badges and Best Practices

### Status Badges

Status badges are small images that show the current state of a workflow: passing or failing. Add them to the collection README to give contributors instant visibility into CI health.

The badge URL format is:

```text
![Workflow Name](https://github.com/OWNER/REPO/actions/workflows/WORKFLOW_FILE/badge.svg)
```

For the three workflows in this module:

```markdown
![Ansible Lint](https://github.com/OWNER/REPO/actions/workflows/ansible-lint.yml/badge.svg)
![Molecule Tests](https://github.com/OWNER/REPO/actions/workflows/molecule.yml/badge.svg)
![Collection Tests](https://github.com/OWNER/REPO/actions/workflows/collection-test.yml/badge.svg)
```

Replace `OWNER/REPO` with your GitHub repository path.

### Branch Protection

Branch protection rules enforce quality gates at the repository level. When configured, pull requests cannot be merged until all required status checks pass, regardless of who is merging.

The key settings for an Ansible content repository:

- **Require status checks to pass before merging**: Select the `all_green` job from the collection test workflow. This single check covers all test environments.
- **Require pull request reviews**: At least one team member must approve before merging.
- **Do not allow bypassing the above settings**: Even repository admins must follow the rules.
- **Restrict force pushes**: Prevent rewriting history on `main`.

Branch protection is configured under **Settings → Branches → Branch protection rules** in the GitHub repository. The specific settings depend on your team's workflow and access model -- start with requiring the `all_green` status check and iterate from there.

!!! note "Branch protection requires admin access"
    Configuring branch protection rules requires repository admin permissions and varies by team workflow. The settings above are best practices -- apply them based on your organization's needs.

## Other CI Platforms

The workflows in this module use GitHub Actions, but the tools are the same everywhere. Only the CI configuration format changes.

### GitLab CI

GitLab CI uses `.gitlab-ci.yml` instead of `.github/workflows/`. The same tools run the same way -- only the configuration format changes:

```yaml
---
stages:
  - lint
  - test

ansible-lint:
  stage: lint
  image: ghcr.io/ansible/community-ansible-dev-tools:latest
  script:
    - ansible-lint

collection-tests:
  stage: test
  image: ghcr.io/ansible/community-ansible-dev-tools:latest
  script:
    - tox --ansible -c tox-ansible.ini
```

### Jenkins

For Jenkins, use the `ghcr.io/ansible/community-ansible-dev-tools` container image as the build agent -- it includes `ansible-lint`, Molecule, `tox-ansible`, and all the other tools from this module. The same commands work identically inside it.

The key point: learn the tools once, apply them everywhere. Only the CI configuration format changes.

## Exercises

### Exercise 1: Create an ansible-lint Workflow

Using only the concepts from the "Linting in CI with ansible-lint" section, create `.github/workflows/ansible-lint.yml` from scratch. Your workflow should:

- Trigger on pushes and pull requests to `main`
- Use an `ubuntu-24.04` runner
- Check out the code and run `ansible-lint` using the official action
- Point `ansible-lint` at the collection's working directory

After writing your version, compare it with the reference workflow in the section above. Did you miss anything? Did you add anything unnecessary?

### Exercise 2: Create a Molecule Test Workflow

Create `.github/workflows/molecule.yml` with path filtering, a matrix strategy for scenarios, color output, and artifact upload on failure.

Use the workflow from the "Molecule Integration Tests in CI" section above. After creating the file, open a pull request that introduces a deliberate error in the webserver role (for example, a typo in a variable name in a template). Observe the CI failure. Fix the error, push again, and observe the CI pass.

### Exercise 3: Create a tox-ansible Collection Test Workflow

Create `.github/workflows/collection-test.yml` with the two-job pattern: matrix generation and parallel test execution.

Use the workflow from the "Collection Testing with tox-ansible" section above. Before pushing, run the matrix generation locally to see the JSON output:

```bash
cd ansible/collections/parasoltech/infrastructure
tox --ansible --gh-matrix -c tox-ansible.ini
```

Examine the JSON. Push the workflow and observe the dynamic matrix in the GitHub Actions tab.

### Exercise 4: Configure Secrets and Status Badges

1. Navigate to your repository on GitHub and add a secret called `VAULT_PASSWORD` under **Settings → Secrets and variables → Actions**
2. Add the vault password step from the "Vault Password in CI" section to your Molecule workflow, before the `Run Molecule tests` step
3. Add status badges for all three workflows to the collection README at `ansible/collections/parasoltech/infrastructure/README.md`:

    ```markdown
    ![Ansible Lint](https://github.com/OWNER/REPO/actions/workflows/ansible-lint.yml/badge.svg)
    ![Molecule Tests](https://github.com/OWNER/REPO/actions/workflows/molecule.yml/badge.svg)
    ![Collection Tests](https://github.com/OWNER/REPO/actions/workflows/collection-test.yml/badge.svg)
    ```

4. Push and verify the badges render correctly in the README

### Exercise 5: Reusable Workflows (Bonus)

Create `.github/workflows/changelog.yml` that calls the `ansible/ansible-content-actions` reusable workflow for changelog validation:

```yaml
---
name: Changelog Check

on:
  pull_request:
    branches: [main]

jobs:
  changelog:
    uses: ansible/ansible-content-actions/.github/workflows/changelog.yaml@main
```

Explore the [ansible-content-actions repository](https://github.com/ansible/ansible-content-actions) to see what other reusable workflows are available. Consider which ones would benefit the CoP's collection.

## Summary

In this module you:

- Understood the critical distinction between CI/CD *for* Ansible content (testing your automation code in ephemeral runners) and CI/CD *with* Ansible (executing automation against real infrastructure with AAP)
- Created an `ansible-lint` workflow using the official `ansible/ansible-lint@v26` composite action, with triggers on push and pull request
- Built a Molecule test workflow with path filtering, matrix strategy for multiple scenarios, color output via environment variables, and artifact upload on failure for post-mortem debugging
- Configured `tox-ansible` with `--gh-matrix` to dynamically generate a CI test matrix, and used the two-job pattern (matrix generation → parallel execution) with an `all_green` aggregation job
- Learned to manage secrets in CI -- Vault passwords written to temporary files, Galaxy tokens injected as environment variables, and the security implications of fork PRs
- Added status badges to the collection README and understood branch protection as a best practice for enforcing quality gates at the repository level

The CoP at Parasol Tech now has automated quality gates on every pull request. Linting runs in seconds. Molecule integration tests and tox-ansible sanity/unit tests run in parallel. An `all_green` job aggregates the results into a single pass/fail signal. No one needs to remember to run the tests -- the CI pipeline enforces it.

## Next Steps

Next: [Module 12 -- Scaling with AAP](12-scaling-with-aap.md)
