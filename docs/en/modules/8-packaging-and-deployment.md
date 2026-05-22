# Module 8: Packaging and Deployment

## Learning Objectives

By the end of this module you will be able to:

- Explain what Execution Environments are and why they matter
- Define an EE using `execution-environment.yml` (version 3)
- Build an EE with `ansible-builder` and test it with `ansible-navigator`
- Sign content with `ansible-sign` using GPG keys
- Describe the supply chain security workflow (sign → push → verify)

## The Story So Far

The CoP at Parasol Tech has built a tested, linted collection -- `parasoltech.infrastructure` with a `webserver` role, Molecule integration tests, pytest unit tests, and tox-ansible orchestration. Every pull request passes quality gates before it can be merged.

But then the trouble starts. A new team member runs the webserver playbook on their laptop and gets a different result. Their local Python environment is missing a dependency. Another team member works on a different OS and gets a version conflict in `ansible.posix`. The staging server has an older version of `ansible-core` than what the team tested with.

"We tested this," Alex says. "It passed everything."

Jordan sighs. "It passed on *our* machines. The staging server has a completely different Python environment."

The CoP identifies two problems:

1. **Portability** -- the automation works only when the execution environment matches the one the developer tested against. Every machine has different Python packages, system libraries, and Ansible versions.
2. **Integrity** -- anyone with push access to the Git repository can modify playbooks. There is no way to prove that the content running in production is the same content the CoP reviewed and approved.

The solutions: **Execution Environments** for portability, and **content signing** for integrity.

## Execution Environments

An Execution Environment (EE) is a container image that bundles everything Ansible needs to run: `ansible-core`, Python dependencies, system packages, and collections. When you run a playbook inside an EE, the execution uses the container's environment -- not whatever happens to be installed on the host machine.

This solves the "works on my machine" problem. The container image is immutable and versioned. If it works in development, it works in staging. If it works in staging, it works in production. Every execution uses the exact same dependencies.

### How EEs Work

Without an EE, Ansible runs on the control node using whatever Python interpreter and packages are installed locally:

```text
Control node (your laptop)
├── ansible-core 2.17
├── Python 3.11
├── ansible.posix 1.5.4
├── Missing: some-python-lib  ← breaks at runtime
└── playbook.yml
```

With an EE, Ansible runs inside a container that has everything pre-installed:

```text
Container image (EE)
├── ansible-core 2.19
├── Python 3.12
├── ansible.posix 2.1.0
├── some-python-lib 3.0
└── (all dependencies locked)

Control node
├── podman (or docker)
├── ansible-navigator
└── playbook.yml  ← runs INSIDE the container
```

The playbook file stays on the control node. `ansible-navigator` mounts it into the container at runtime. The execution happens inside the container, using the container's Python, modules, and libraries.

### The EE Ecosystem

Three tools work together:

| Tool | Purpose |
|------|---------|
| **`ansible-builder`** | Builds EE container images from a definition file |
| **`ansible-navigator`** | Runs playbooks inside EE containers |
| **`podman`** (or `docker`) | The container runtime that executes the image |

You already used `ansible-navigator` in Module 2. Now you will learn to build the images it runs inside.

## Defining an EE

The EE definition lives in `execution-environment.yml`. This file tells `ansible-builder` what to put inside the container image.

The `parasoltech-ee` definition for the CoP's collection lives at `ansible/execution-environments/parasoltech-ee/execution-environment.yml`:

```yaml
---
version: 3

images:
  base_image:
    name: quay.io/ansible/creator-ee:latest

dependencies:
  galaxy: requirements.yml
  python: []
  system: []
```

And the companion `requirements.yml`:

```yaml
---
collections:
  - name: parasoltech.infrastructure
  - name: ansible.posix
```

### The Version 3 Schema

The `version: 3` schema is the current standard for EE definitions. It replaced version 1 and version 2, which had a different structure. Always use version 3 for new EE projects.

### Schema Sections

#### `images`

The `base_image` specifies the starting container image. `ansible-builder` adds your dependencies on top of this base.

Common base images:

| Image | Contents |
|-------|----------|
| `quay.io/ansible/creator-ee:latest` | Full dev tools suite -- `ansible-core`, `ansible-lint`, `molecule`, and more |
| `quay.io/ansible/ansible-runner:latest` | Minimal runtime -- `ansible-core` and `ansible-runner` only |
| `registry.redhat.io/ansible-automation-platform/ee-minimal-rhel9` | Red Hat supported minimal EE for production |
| `registry.redhat.io/ansible-automation-platform/ee-supported-rhel9` | Red Hat supported EE with certified collections |

For development, `creator-ee` is convenient because it includes all the dev tools. For production, use a minimal base image to reduce attack surface and image size.

#### `dependencies`

Three types of dependencies can be declared:

- **`galaxy`** -- Points to a `requirements.yml` file listing Ansible collections. These are installed with `ansible-galaxy collection install` during the build.
- **`python`** -- A list of Python packages (or a path to a `requirements.txt` file). These are installed with `pip` during the build.
- **`system`** -- A list of system packages (or a path to a `bindep.txt` file). These are installed with the system package manager (`dnf`, `apt`, etc.) during the build.

The separation is important. Collections go in `galaxy`, their Python dependencies go in `python`, and their system library dependencies go in `system`. This mirrors how you would install dependencies manually, but `ansible-builder` automates it inside the container build.

#### Optional Sections

The version 3 schema supports additional sections for advanced use cases:

```yaml
---
version: 3

images:
  base_image:
    name: quay.io/ansible/creator-ee:latest

dependencies:
  galaxy: requirements.yml
  python:
    - jmespath
    - netaddr
  system:
    - iputils

additional_build_files:
  - src: custom-ansible.cfg
    dest: configs

additional_build_steps:
  prepend_final:
    - COPY _build/configs/custom-ansible.cfg /etc/ansible/ansible.cfg
  append_final:
    - RUN echo "Build complete"

options:
  tags:
    - parasoltech-ee:1.0.0
    - parasoltech-ee:latest
  package_manager_path: /usr/bin/dnf
```

- **`additional_build_files`** -- Copies extra files into the build context. Useful for custom configuration files, scripts, or local collection tarballs.
- **`additional_build_steps`** -- Injects custom Containerfile instructions at specific points in the build (`prepend_base`, `append_base`, `prepend_galaxy`, `append_galaxy`, `prepend_builder`, `append_builder`, `prepend_final`, `append_final`).
- **`options`** -- Build options like image tags and the package manager path.

!!! tip "Keep it simple"
    For most use cases, you only need `images`, `dependencies`, and maybe `options.tags`. The advanced sections exist for edge cases -- do not add complexity until you need it.

## Building with ansible-builder

`ansible-builder` takes the EE definition and produces a container image. It works in two steps: first it generates a Containerfile, then it builds the image.

### Step 1: Preview the Containerfile

Before building, you can inspect what `ansible-builder` will do:

```bash
cd ansible/execution-environments/parasoltech-ee
ansible-builder create
```

This generates a `context/` directory containing a `Containerfile` and all the files needed for the build. Open `context/Containerfile` to see the four stages:

```text
context/
  Containerfile    # The multi-stage build definition
  _build/
    requirements.yml    # Galaxy dependencies
    ...
```

The generated Containerfile has four stages:

| Stage | Purpose |
|-------|---------|
| **Base** | Starts from the base image, installs system packages |
| **Galaxy** | Installs Ansible collections from `requirements.yml` |
| **Builder** | Installs Python packages, compiles any native extensions |
| **Final** | Assembles the final image from the previous stages |

This multi-stage approach keeps the final image small. Build tools and compilation artifacts are discarded -- only the runtime dependencies make it into the final image.

!!! note "Inspect before you build"
    Running `ansible-builder create` is a dry run. It generates the Containerfile without building anything. Use it to verify your EE definition is correct before committing to a full build, which can take several minutes.

### Step 2: Build the Image

Build the image with a tag:

```bash
ansible-builder build --tag parasoltech-ee:1.0.0
```

For detailed output during the build:

```bash
ansible-builder build --tag parasoltech-ee:1.0.0 -v 3
```

The `-v 3` flag sets maximum verbosity so you can see every step of the container build. This is useful for debugging dependency installation failures.

When the build completes:

```text
[4/4] STEP 22/22: CMD ["bash"]
[4/4] COMMIT parasoltech-ee:1.0.0
--> a1b2c3d4e5f6
Successfully tagged localhost/parasoltech-ee:1.0.0

Complete! The build context can be found at:
  /path/to/parasoltech-ee/context
```

### Working with Local Collections

If your collection is not published to Galaxy or Automation Hub yet, you need to package it as a tarball and reference it locally in the EE definition.

First, build the collection tarball:

```bash
cd ansible/collections/parasoltech/infrastructure
ansible-galaxy collection build \
  --output-path ../../execution-environments/parasoltech-ee/
```

Then modify the EE definition to use the local tarball:

```yaml
---
version: 3

images:
  base_image:
    name: quay.io/ansible/creator-ee:latest

dependencies:
  python_interpreter:
    python_path: /usr/bin/python3

  galaxy:
    collections:
      - name: collection_tarballs/parasoltech-infrastructure-1.0.0.tar.gz
        type: file
  python: []
  system: []

additional_build_files:
  - src: parasoltech-infrastructure-1.0.0.tar.gz
    dest: collection_tarballs
```

The `type: file` tells `ansible-galaxy` to install from the local path instead of downloading from Galaxy. The `additional_build_files` section copies the tarball into the build context where the Galaxy stage can find it.

## Testing Your EE

After building, verify the image before deploying it anywhere.

### Verify with podman

Check that the image exists and the collections are installed:

```bash
# List local images
podman images | grep parasoltech

# Check ansible-core version inside the EE
podman run --rm parasoltech-ee:1.0.0 ansible --version

# List installed collections
podman run --rm parasoltech-ee:1.0.0 \
  ansible-galaxy collection list
```

Expected output from the collection list:

```text
# /usr/share/ansible/collections/ansible_collections
Collection                   Version
---------------------------- -------
ansible.posix                2.1.0
parasoltech.infrastructure   1.0.0
```

### Test with ansible-navigator

Run the webserver playbook using the custom EE:

```bash
ansible-navigator run \
  ansible/playbooks/module-05/deploy-webserver.yml \
  --execution-environment-image parasoltech-ee:1.0.0 \
  --pull-policy never
```

The `--pull-policy never` flag tells `ansible-navigator` to use the local image instead of trying to pull it from a registry. This is important during development when the image only exists locally.

If the playbook runs successfully inside the EE, the environment is correctly packaged. Every machine that uses this image will get the same result.

!!! tip "Iterative development"
    During EE development, use the `create` → `build` → `test` cycle:

    1. Edit `execution-environment.yml`
    2. Run `ansible-builder create` to preview the Containerfile
    3. Run `ansible-builder build --tag parasoltech-ee:dev` to build
    4. Run `podman run --rm parasoltech-ee:dev ansible-galaxy collection list` to verify
    5. Run a playbook with `ansible-navigator` to test end-to-end

    Only tag with a version number (like `1.0.0`) when the EE is validated and ready for promotion.

## Content Signing with ansible-sign

Execution Environments solve the portability problem. Content signing solves the integrity problem.

`ansible-sign` is a utility that signs and verifies Ansible project directories. It works by:

1. Computing SHA-256 checksums of every file you want to protect
2. Writing those checksums to a manifest file
3. Signing the manifest with a GPG key

Anyone with the matching public key can then verify that the content has not been tampered with -- no files modified, no files added, no files removed.

### GPG Key Setup

`ansible-sign` uses GNU Privacy Guard (GPG) keys. If you do not have a GPG key, create one using a batch file for non-interactive generation:

Create a file called `gpg-batch.txt`:

```text
%echo Generating a GPG key for ansible-sign
Key-Type: default
Key-Length: 4096
Subkey-Type: default
Subkey-Length: default
Name-Real: Parasol Tech Automation
Name-Comment: content signing key
Name-Email: automation@parasol.example
Expire-Date: 1y
%no-ask-passphrase
%no-protection
%commit
%echo done
```

Generate the key:

```bash
gpg --batch --gen-key gpg-batch.txt
```

Verify it was created:

```bash
gpg --list-secret-keys
```

```text
sec   rsa4096 2026-05-21 [SC] [expires: 2027-05-21]
      ABCDEF1234567890ABCDEF1234567890ABCDEF12
uid           [ultimate] Parasol Tech Automation (content signing key) <automation@parasol.example>
ssb   rsa3072 2026-05-21 [E]
```

!!! warning "Production key management"
    The example above creates a key without a passphrase for simplicity. In production, always use a passphrase-protected key and store it in a secure key management system. Never commit private keys to version control.

### The MANIFEST.in File

Before signing, you need a `MANIFEST.in` file that tells `ansible-sign` which files to include in the checksum manifest. This file uses Python's `distlib.manifest` syntax -- the same format used by Python packaging tools.

The signing example at `ansible/execution-environments/signing-example/MANIFEST.in`:

```text
# Exclude version control and development artifacts
global-exclude .git
global-exclude .git/*
prune .git

# Include all playbooks
recursive-include . *.yml
recursive-include . *.yaml

# Include documentation
include README.md

# Exclude test and temporary files
prune .tox
prune .venv
prune tmp
global-exclude *.pyc
global-exclude __pycache__
```

Key directives:

| Directive | Meaning |
|-----------|---------|
| `include <file>` | Include a specific file |
| `recursive-include <dir> <pattern>` | Include all files matching pattern in dir and subdirs |
| `global-exclude <pattern>` | Exclude files matching pattern everywhere |
| `prune <dir>` | Exclude an entire directory tree |

The principle: include everything that affects execution (playbooks, roles, inventory, configuration), exclude everything that does not (version control, test artifacts, caches).

### Signing and Verification

With the GPG key and `MANIFEST.in` in place, signing is a single command.

**Sign the project:**

```bash
cd ansible/execution-environments/signing-example
ansible-sign project gpg-sign .
```

```text
[OK   ] GPG signing successful!
[NOTE ] Checksum manifest: ./.ansible-sign/sha256sum.txt
[NOTE ] GPG summary: signature created
```

This creates two files inside `.ansible-sign/`:

```text
.ansible-sign/
  sha256sum.txt       # Checksum manifest (one hash per file)
  sha256sum.txt.sig   # GPG signature of the manifest
```

The `sha256sum.txt` file contains one line per protected file:

```text
a1b2c3d4...  ./playbook.yml
e5f6a7b8...  ./README.md
```

**Verify the project:**

```bash
ansible-sign project gpg-verify .
```

```text
[OK   ] GPG signature verification succeeded.
[NOTE ] Checksum manifest: ./.ansible-sign/sha256sum.txt
[NOTE ] GPG summary: valid signature
```

If any file has been modified, added, or removed since signing, verification fails:

```text
[FAIL ] GPG signature verification FAILED.
[NOTE ] Modified: ./playbook.yml
```

### Supply Chain Security Workflow

Content signing becomes powerful when integrated into the deployment pipeline. The workflow is:

```text
Developer workstation          Git repository          AAP Controller
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ 1. Write content │     │                  │     │                  │
│ 2. Run tests     │────▶│ 3. Push signed   │────▶│ 4. Project Sync  │
│ 3. Sign project  │     │    content       │     │ 5. Verify GPG    │
│    (gpg-sign)    │     │                  │     │    signature     │
└──────────────────┘     └──────────────────┘     │ 6. Run if valid  │
                                                  └──────────────────┘
```

1. **Developer signs** -- After the CoP reviews and approves changes, a trusted signer runs `ansible-sign project gpg-sign .` on the project directory.
2. **Push to Git** -- The signed content (including `.ansible-sign/`) is committed and pushed to the repository.
3. **AAP Project Sync** -- Ansible Automation Platform's Controller pulls the repository.
4. **AAP verifies** -- Controller is configured with the public GPG key as a credential. During Project Sync, it runs the equivalent of `ansible-sign project gpg-verify .` on the pulled content.
5. **Execute or reject** -- If verification succeeds, the content is trusted and can run. If it fails, the sync fails and no job templates can execute -- the content is blocked.

This means that even if an attacker compromises the Git repository and modifies a playbook, the content will not execute. The checksums will not match, the GPG signature will be invalid, and AAP will reject the content.

!!! note "Two layers of trust"
    Content signing protects the **content** (playbooks, roles, inventory). Execution Environments protect the **runtime** (Python, collections, system packages). Together, they form a complete supply chain security model: you know exactly what code will run and exactly what environment it will run in.

## Publishing to Automation Hub

Once the EE image is built and tested, the next step is publishing it to a container registry where AAP Controller can pull it. The typical destinations are:

- **Private Automation Hub** -- The organization's internal registry, part of AAP. This is the recommended destination for production EE images.
- **Quay.io** -- Red Hat's public/private container registry.
- **Any OCI-compatible registry** -- Harbor, Docker Hub, GitLab Container Registry, etc.

### Push to a Registry

Tag and push using `podman`:

```bash
# Tag for the target registry
podman tag parasoltech-ee:1.0.0 \
  hub.parasol.example/ee-images/parasoltech-ee:1.0.0

# Log in to the registry
podman login hub.parasol.example

# Push the image
podman push hub.parasol.example/ee-images/parasoltech-ee:1.0.0
```

### Publish the Collection

The collection itself can be published to Automation Hub or Galaxy:

```bash
cd ansible/collections/parasoltech/infrastructure

# Build the collection tarball
ansible-galaxy collection build

# Publish to Private Automation Hub
ansible-galaxy collection publish \
  parasoltech-infrastructure-1.0.0.tar.gz \
  --server https://hub.parasol.example/api/galaxy/content/published/ \
  --token <your-api-token>
```

Once published, other teams can install the collection from Automation Hub instead of copying files, and EE definitions can reference the published collection instead of using local tarballs.

### The Complete Lifecycle

The full packaging and deployment lifecycle for the CoP looks like this:

```text
1. Develop     ──▶  Write roles and playbooks
2. Test        ──▶  ansible-lint + pytest + molecule + tox-ansible
3. Package EE  ──▶  ansible-builder build --tag parasoltech-ee:1.0.0
4. Test EE     ──▶  ansible-navigator run ... --eei parasoltech-ee:1.0.0
5. Sign        ──▶  ansible-sign project gpg-sign .
6. Publish     ──▶  Push EE to registry, collection to Hub
7. Deploy      ──▶  AAP pulls, verifies, executes
```

Each step builds on the previous one. Nothing reaches production without passing through every gate.

## Exercises

### Exercise 1: Build an Execution Environment

Navigate to the EE directory and preview the build:

```bash
cd ansible/execution-environments/parasoltech-ee
ansible-builder create
```

Examine the generated `context/Containerfile`. Identify the four build stages and understand what each one does. Then build the image:

```bash
ansible-builder build --tag parasoltech-ee:latest
```

Verify the image exists:

```bash
podman images | grep parasoltech
```

### Exercise 2: Test the EE

Run a command inside the EE to verify the collections are installed:

```bash
podman run --rm parasoltech-ee:latest \
  ansible-galaxy collection list
```

Confirm that `parasoltech.infrastructure` and `ansible.posix` appear in the output.

### Exercise 3: Add a Python Dependency

Modify `execution-environment.yml` to add `jmespath` as a Python dependency:

```yaml
dependencies:
  galaxy: requirements.yml
  python:
    - jmespath
  system: []
```

Rebuild the EE and verify `jmespath` is installed:

```bash
ansible-builder build --tag parasoltech-ee:latest
podman run --rm parasoltech-ee:latest \
  python3 -c "import jmespath; print(jmespath.__version__)"
```

### Exercise 4: Sign a Project

Navigate to the signing example and create a GPG key:

```bash
cd ansible/execution-environments/signing-example
gpg --batch --gen-key gpg-batch.txt
```

Sign the project:

```bash
ansible-sign project gpg-sign .
```

Verify the signature:

```bash
ansible-sign project gpg-verify .
```

Now modify a file and verify again -- the verification should fail.

??? example "Solution"
    ```bash
    # Modify a signed file
    echo "# tampered" >> MANIFEST.in

    # Verification should fail
    ansible-sign project gpg-verify .
    # [FAIL] GPG signature verification FAILED.

    # Restore the original file
    git checkout MANIFEST.in

    # Re-verify — should pass again
    ansible-sign project gpg-verify .
    # [OK] GPG signature verification succeeded.
    ```

### Exercise 5: Run a Playbook in the EE

Use `ansible-navigator` to run a playbook inside the custom EE:

```bash
ansible-navigator run \
  ansible/playbooks/module-05/deploy-webserver.yml \
  --execution-environment-image parasoltech-ee:latest \
  --pull-policy never \
  --mode stdout
```

Compare the output to running the same playbook without an EE. The results should be identical, but the execution environment is now portable and reproducible.

## Summary

In this module you:

- Learned that Execution Environments are container images that bundle `ansible-core`, collections, Python packages, and system dependencies into an immutable, portable runtime
- Defined an EE using the `execution-environment.yml` version 3 schema, specifying a base image and dependencies across three categories (galaxy, python, system)
- Used `ansible-builder create` to preview the generated multi-stage Containerfile, and `ansible-builder build` to produce the container image
- Tested the EE with `podman` for quick checks and `ansible-navigator` for end-to-end playbook execution
- Set up GPG keys and a `MANIFEST.in` file to sign Ansible projects with `ansible-sign`, creating checksum manifests protected by cryptographic signatures
- Understood the supply chain security workflow where developers sign content, push to Git, and AAP Controller verifies the GPG signature before allowing execution
- Published EE images to container registries and collections to Automation Hub, completing the packaging lifecycle

The CoP at Parasol Tech now has a complete pipeline: code is tested (Module 7), packaged into Execution Environments, signed for integrity, and published for consumption. No more dependency conflicts, no more "works on my machine," and no more unverified content running in production.

## Next Steps

Next: [Module 9 -- Scaling with AAP](9-scaling-with-aap.md)
