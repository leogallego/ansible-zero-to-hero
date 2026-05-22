# Module 9: Scaling with AAP

## Learning Objectives

By the end of this module you will be able to:

- Describe the Ansible Automation Platform components (Controller, Hub, EDA)
- Create job templates and workflows in Controller
- Configure inventories and credentials in Controller
- Set up RBAC with teams, roles, and permissions
- Integrate Execution Environments with Controller
- Configure project sync with content verification

## The Story So Far

The CoP at Parasol Tech has come a long way. The team has a tested, linted, and signed collection -- `parasoltech.infrastructure`. It ships inside a custom Execution Environment built with `ansible-builder`. Every change passes through `ansible-lint`, Molecule, pytest, and tox-ansible before merging. Content is signed with `ansible-sign` so that nobody can tamper with playbooks between review and execution.

But a new problem is emerging. Lionel runs the webserver deployment from a laptop. Jordan runs the patching playbook from a different laptop. A third team member runs ad-hoc commands from a jump host. Nobody has visibility into what ran, when, who ran it, or whether it succeeded. There is no audit trail, no access control, and no way to schedule recurring jobs.

"I ran the database backup playbook yesterday," Jordan says. "But I used `--limit staging` instead of `--limit production`. Nobody noticed until this morning."

Lionel frowns. "And I have no way to know who ran what on the prod servers last week. We need a control plane."

The CoP agrees: CLI execution does not scale. They need centralized orchestration with governance, audit logging, role-based access control, and the ability to chain automation into multi-step workflows. They need **Ansible Automation Platform**.

## AAP Overview

Ansible Automation Platform (AAP) is Red Hat's enterprise platform for managing Ansible automation at scale. It takes the CLI tools you have been using throughout this course and adds a centralized control plane with a web UI, REST API, RBAC, audit logging, credential management, and workflow orchestration.

AAP has three main components:

### Controller

**Automation Controller** (formerly Ansible Tower) is the central management layer. It provides:

- **Job Templates** -- reusable definitions for running playbooks with specific inventories, credentials, and variables
- **Workflows** -- multi-step automation pipelines that chain job templates together with conditional logic
- **Inventories** -- centralized host management with static sources, dynamic providers, and synced inventory from external systems
- **Credentials** -- secure storage for SSH keys, API tokens, cloud credentials, and vault passwords -- no more secrets on individual laptops
- **RBAC** -- teams, roles, and granular permissions that control who can run what on which hosts
- **Audit logging** -- every job execution is recorded with who triggered it, what ran, when it started, how long it took, and what the result was
- **Scheduling** -- run jobs on a recurring schedule without human intervention
- **REST API** -- everything available in the UI is also available via API, enabling integration with CI/CD pipelines, ticketing systems, and custom tooling

Controller is where the CoP will do most of their work. It replaces the pattern of "SSH into a server and run `ansible-playbook`" with a governed, auditable workflow.

### Automation Hub

**Private Automation Hub** is the organization's internal content repository. It serves two purposes:

1. **Collection registry** -- Teams publish collections to Hub instead of sharing tarballs or pointing at Git repositories. Other teams install collections from Hub using `ansible-galaxy`. Hub can host certified collections (from Red Hat and partners), validated community collections, and the organization's own private collections like `parasoltech.infrastructure`.

2. **EE container registry** -- Hub stores Execution Environment images. Controller pulls EE images from Hub when running jobs, ensuring every execution uses the approved, tested image. This is where the EE built in Module 8 would be published for production use.

Hub solves the content distribution problem. Instead of each team maintaining their own copy of collections and EE images, there is a single, governed source of truth.

### Event-Driven Ansible

**Event-Driven Ansible (EDA)** extends automation from "human triggers a job" to "events trigger jobs automatically." EDA introduces:

- **Event sources** -- integrations that listen for events from monitoring systems (Prometheus, Datadog), ticketing systems (ServiceNow), cloud providers (AWS CloudWatch), messaging systems (Kafka), webhooks, and more
- **Rulebooks** -- YAML files that define conditions and actions: "when this event occurs, run this job template"
- **Decision Environments** -- container images (similar to EEs) that bundle the Python dependencies needed by event source plugins

A simple rulebook looks like this:

```yaml
---
- name: Respond to web server alerts
  hosts: all
  sources:
    - ansible.eda.webhook:
        host: 0.0.0.0
        port: 5000
  rules:
    - name: Restart web server on health check failure
      condition: event.payload.alert == "webserver_down"
      action:
        run_job_template:
          name: "Restart Web Server"
          organization: "Parasol Tech"
```

EDA is powerful but it is an advanced topic. This module focuses on Controller and Hub -- the components the CoP needs first. EDA becomes relevant once the team has stable job templates and workflows that can be triggered programmatically.

!!! note "EDA scope"
    Event-Driven Ansible is a full topic on its own. This module introduces the concept so you understand where it fits in the platform. For hands-on EDA work, refer to the [EDA documentation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/).

## Lab Environment

### AAP Sandbox Access

To follow the exercises in this module, you need access to an AAP instance. There are two options:

**Option 1: Red Hat AAP Sandbox (recommended)**

Red Hat provides a free, time-limited AAP sandbox environment for learning:

1. Visit the [AAP Trial page](https://www.redhat.com/en/technologies/management/ansible/trial)
2. Log in with your Red Hat account (free to create)
3. Follow the setup instructions to provision your sandbox
4. You will receive a Controller URL and credentials

The sandbox includes Controller, a private Automation Hub, and pre-configured resources to explore.

**Option 2: Red Hat Developer Sandbox**

The [Red Hat Developer Sandbox](https://developers.redhat.com/products/ansible/getting-started) provides access to AAP as part of a broader developer environment. This option includes additional developer tools and services.

!!! tip "No AAP access?"
    If you cannot access an AAP instance right now, this module is still valuable. The concepts, architecture, and mapping from CLI to Controller apply to any AAP version. Read through the material, study the diagrams, and revisit the exercises when you have access.

## From CLI to Controller

Everything you have done on the command line maps directly to a Controller concept. The transition is not about learning new automation -- it is about managing the same automation through a governed platform.

| CLI Concept | Controller Equivalent | What Changes |
|-------------|----------------------|--------------|
| `ansible-playbook deploy.yml` | **Job Template** | Playbook, inventory, credentials, and variables are bundled into a reusable, parameterized definition |
| Inventory files (`hosts.yml`, `group_vars/`) | **Inventory** + **Inventory Source** | Inventories are stored in Controller. Sources can sync from Git, cloud providers, or custom scripts |
| `~/.ssh/` keys, vault passwords | **Credentials** | Secrets are stored encrypted in Controller. Users can *use* credentials without *seeing* them |
| `ansible.cfg` | **Project** + **Organization settings** | Configuration is managed per-project and per-organization through the UI/API |
| `--limit webservers` | **Limit** field on Job Template | Same concept, exposed as a UI field that can be locked down or parameterized |
| `--extra-vars "env=prod"` | **Extra Variables** / **Survey** | Variables can be prompted at launch time with validation using surveys |
| Running from cron | **Schedule** on Job Template | Built-in scheduler with recurrence rules, no cron management needed |
| Checking terminal output | **Job output log** + **Notifications** | Full stdout capture, log retention, and notifications to Slack, email, webhook, etc. |

The key insight: Controller does not change *what* Ansible does. It changes *how you manage* what Ansible does. Your playbooks, roles, collections, and EEs work exactly the same way -- Controller adds governance, audit, and collaboration on top.

### Projects

A **Project** in Controller is a reference to a source control repository containing Ansible content. When you create a Project, you tell Controller:

- Where the Git repository lives (URL)
- Which branch or tag to use
- Which credential to use for authentication (SSH key or token)
- Whether to verify content signatures (using the GPG credential from Module 8)

Controller clones the repository and makes its contents available for Job Templates. When the repository changes, you sync the Project to pull the latest content.

This is how the signed content from Module 8 gets into Controller. The supply chain security workflow completes here:

```text
Developer signs content → Pushes to Git → Controller syncs Project → Verifies GPG signature
```

## Job Templates

A **Job Template** is the most fundamental unit of work in Controller. It bundles everything needed to run a playbook:

- **Project** -- which Git repository contains the playbook
- **Playbook** -- which playbook file to run (selected from the Project)
- **Inventory** -- which hosts to target
- **Credentials** -- which keys/tokens to use for authentication
- **Execution Environment** -- which EE image to use for the runtime
- **Extra Variables** -- default variables to pass to the playbook
- **Limit** -- optional host pattern to restrict execution
- **Verbosity** -- the `-v` level (0-5)

### Creating a Job Template

To create a Job Template for the webserver deployment from Module 6:

1. **Create a Project** pointing to the Git repository that contains the `parasoltech.infrastructure` collection and its playbooks
2. **Create or select an Inventory** with the target hosts
3. **Create or select a Credential** with the SSH key for the target hosts
4. **Create the Job Template** with:
    - Name: `Deploy Web Server`
    - Project: the project created in step 1
    - Playbook: `playbooks/deploy-webserver.yml`
    - Inventory: the inventory from step 2
    - Credentials: the SSH credential from step 3
    - Execution Environment: `parasoltech-ee`

Once created, anyone with the right permissions can launch the job template from the UI or API. Every execution is logged with the user who launched it, the parameters used, and the full output.

### Surveys

**Surveys** let you prompt users for input at launch time. Instead of trusting users to type `--extra-vars` correctly, you define a form with typed fields, default values, and validation rules.

For example, a survey for the webserver deployment might include:

- **Environment** (dropdown): `dev`, `staging`, `production`
- **Web server port** (integer): default `8080`, minimum `1024`, maximum `65535`
- **Enable TLS** (boolean): default `true`

Surveys turn a generic job template into a self-service interface. A team member who does not know Ansible can deploy a web server by filling out a form -- the survey maps their answers to extra variables that the playbook consumes.

!!! tip "Survey variables map to extra vars"
    Survey answers are injected as extra variables. If your playbook uses `webserver_port`, create a survey question with the variable name `webserver_port`. The playbook code does not change at all.

### Launching and Monitoring

After creating a job template, you can:

- **Launch** it immediately from the UI or via the API
- **Schedule** it to run at specific times (daily, weekly, on a cron expression)
- **Monitor** running jobs in real time -- the output streams live, just like watching a terminal
- **Review** completed jobs -- every run is stored with its full output, start/end time, and status

The job detail view shows the same output you would see from `ansible-playbook` on the command line, plus metadata about the execution environment, credentials used, and which user triggered the run.

## Workflows

A **Workflow** chains multiple job templates into a multi-step automation pipeline. Each node in a workflow can:

- Run a **Job Template**
- Run another **Workflow** (nested workflows)
- Run a **Project Sync**
- Run an **Inventory Source Sync**
- Execute an **Approval** node (pause and wait for a human to approve before continuing)

Nodes connect with three types of edges:

| Edge Type | Meaning |
|-----------|---------|
| **On Success** (green) | Run the next node only if this one succeeded |
| **On Failure** (red) | Run the next node only if this one failed |
| **Always** (blue) | Run the next node regardless of this one's result |

### Example: Parasol Tech Deployment Workflow

The CoP designs a deployment workflow that chains the automation from previous modules:

```text
┌─────────────────┐   success   ┌────────────────┐   success   ┌──────────────────┐
│  Sync Project   │────────────▶│  Deploy Web    │────────────▶│  Verify Service  │
│  (verify GPG)   │             │  Server        │             │  Health          │
└─────────────────┘             └────────────────┘             └──────────────────┘
        │                              │                              │
     failure                        failure                        failure
        ▼                              ▼                              ▼
┌─────────────────┐             ┌────────────────┐             ┌──────────────────┐
│  Notify: Content│             │  Notify: Deploy│             │  Rollback Web    │
│  Tampered       │             │  Failed        │             │  Server          │
└─────────────────┘             └────────────────┘             └──────────────────┘
                                                                      │
                                                                   always
                                                                      ▼
                                                               ┌──────────────────┐
                                                               │  Notify: Rollback│
                                                               │  Executed        │
                                                               └──────────────────┘
```

This workflow:

1. **Syncs the Project** and verifies the GPG signature (Module 8). If the content has been tampered with, the workflow stops and sends a notification.
2. **Deploys the web server** using the job template. If deployment fails, a notification is sent.
3. **Verifies the service** is healthy. If the health check fails, it triggers a rollback and then notifies regardless of the rollback's outcome.

Each node in this workflow is a separate job template. The workflow orchestrates them, handles failures, and ensures the right people are notified. This is far more robust than a shell script that runs three `ansible-playbook` commands in sequence.

### Convergence and Branching

Workflows support more than linear chains. Nodes can fan out (one node triggers multiple parallel nodes) and converge (multiple nodes must complete before the next one starts). This enables patterns like:

- Run database migration and cache warming in parallel, then deploy the application after both succeed
- Run the same playbook against multiple environments in parallel
- Add an approval gate before production deployment

## Inventories and Credentials

### Inventories in Controller

Controller inventories serve the same purpose as the inventory files from Module 3, but with additional capabilities:

- **Static hosts** -- add hosts and groups directly in the UI, equivalent to editing `hosts.yml`
- **Inventory Sources** -- sync hosts from external systems automatically:
    - **SCM (Git)** -- pull inventory files from a repository (your structured `inventory/` directory works directly)
    - **Cloud providers** -- discover hosts from AWS, Azure, GCP, VMware, OpenStack
    - **Custom scripts** -- run a dynamic inventory script that returns JSON
- **Smart Inventories** -- create dynamic groups based on host facts and filters

For the CoP, the most natural starting point is an SCM inventory source that points to the same Git repository as the Project. This keeps the inventory files the team already wrote (in Module 3) as the source of truth, while making them available in Controller.

### Variables in Controller

Inventory variables in Controller follow the same precedence rules as CLI Ansible. You can define variables at the host level, group level, or inventory level. These map directly to what you would put in `host_vars/` and `group_vars/` in your structured inventory directory.

!!! warning "One source of truth"
    Avoid defining the same variable in both your Git-tracked inventory files and in the Controller UI. Pick one location and be consistent. The recommended approach is to keep variables in Git (managed by the CoP) and sync them to Controller via the SCM inventory source.

### Credentials

Credentials are one of Controller's most important features. They store secrets -- SSH keys, passwords, API tokens, vault passwords, cloud provider credentials -- encrypted in the database.

Key credential types:

| Type | Purpose |
|------|---------|
| **Machine** | SSH keys and passwords for connecting to managed hosts |
| **Source Control** | Git credentials for syncing Projects |
| **Vault** | Ansible Vault passwords for decrypting encrypted files |
| **Container Registry** | Credentials for pulling EE images from private registries |
| **GPG Public Key** | Public key for content signature verification |
| **Cloud** | AWS, Azure, GCP, VMware credentials for cloud modules and dynamic inventory |

The critical security benefit: users can *use* a credential to run a job without ever seeing the secret value. A junior team member can deploy to production servers using an SSH key they cannot download, copy, or view. The credential is injected into the EE at runtime by Controller.

This is a fundamental shift from CLI Ansible, where everyone who runs playbooks needs direct access to SSH keys and vault passwords on their local machine.

## RBAC

Role-Based Access Control (RBAC) in Controller determines who can do what. It is built on three concepts:

### Organizations

An **Organization** is the top-level grouping. It contains users, teams, projects, inventories, and credentials. A single AAP installation can host multiple organizations.

For Parasol Tech, there might be one organization for each division:

- `Parasol Tech - Platform` (the CoP's organization)
- `Parasol Tech - Database` (the database team)
- `Parasol Tech - Networking` (the network team)

### Teams

A **Team** is a group of users within an organization. Teams are how you assign permissions at scale -- instead of giving permissions to each user individually, you assign permissions to a team and add users to that team.

The CoP might create teams like:

- `Platform Admins` -- full access to all resources
- `Platform Developers` -- can create and edit job templates, but cannot modify credentials or inventories
- `Platform Operators` -- can launch job templates and view results, but cannot edit them

### Roles and Permissions

Controller has a granular permission model. For each resource type (Job Template, Inventory, Credential, Project, etc.), several permission levels exist:

| Role | Capabilities |
|------|-------------|
| **Admin** | Full control -- create, edit, delete, execute, and grant permissions to others |
| **Use** | Can use the resource (e.g., attach a credential to a job template) but cannot edit it |
| **Execute** | Can launch a job template or workflow but cannot edit its configuration |
| **Read** | Can view the resource but cannot modify or execute it |
| **Approval** | Can approve or deny workflow approval nodes |

These roles are assigned per-resource. This means you can give a team `Execute` permission on the `Deploy Web Server` job template, `Read` permission on the production inventory, and no access to the credentials used by that job template. The team can launch the deployment but cannot see the SSH keys, edit the inventory, or modify the job template configuration.

### RBAC Design for the CoP

A practical RBAC setup for Parasol Tech:

```text
Organization: Parasol Tech - Platform
│
├── Team: Platform Admins
│   ├── Admin on all Projects
│   ├── Admin on all Inventories
│   ├── Admin on all Credentials
│   └── Admin on all Job Templates
│
├── Team: Platform Developers
│   ├── Admin on Job Templates (can create/edit)
│   ├── Use on Credentials (can attach to JTs)
│   ├── Use on Inventories (can attach to JTs)
│   └── Read on Projects
│
└── Team: Platform Operators
    ├── Execute on specific Job Templates
    ├── Read on Inventories
    └── Approval on Deployment Workflow
```

With this setup:

- **Admins** manage the infrastructure: credentials, inventories, projects, and EE configurations
- **Developers** create and test job templates using existing credentials and inventories
- **Operators** run approved job templates and approve deployment workflows without any ability to modify the automation or access secrets

This is the governance the CoP was missing when everyone ran `ansible-playbook` from their own laptop.

## EE Integration

The Execution Environment built in Module 8 integrates directly with Controller. Instead of running playbooks with whatever Python happens to be on a server, Controller runs every job inside an EE container.

### Adding EEs to Controller

Controller needs to know where to pull EE images from. There are two approaches:

**From a container registry (recommended for production):**

1. Push the EE image to a container registry (Private Automation Hub, Quay.io, or any OCI registry) -- as shown in Module 8
2. In Controller, create an **Execution Environment** resource pointing to the image URL (e.g., `hub.parasol.example/ee-images/parasoltech-ee:1.0.0`)
3. If the registry requires authentication, create a **Container Registry** credential and attach it to the EE

**From a local image (for development/testing):**

1. Build the image on the Controller host with `ansible-builder`
2. Reference the local image name in the Controller EE configuration

### Assigning EEs to Job Templates

Each job template can specify which EE to use. When the job launches, Controller pulls the EE image (if not already cached) and runs the playbook inside it.

This completes the portability story from Module 8:

```text
Module 8:  Build EE → Test locally with ansible-navigator
Module 9:  Push EE to registry → Controller pulls and uses it for every job
```

Every execution -- whether triggered by a user, a schedule, a workflow, or an API call -- uses the same EE image with the same dependencies. The "works on my machine" problem is eliminated at the platform level, not just the individual developer level.

### EE Lifecycle

As the CoP updates their collection and dependencies, the EE lifecycle looks like this:

1. Developer updates `execution-environment.yml` (add a new collection, update a Python dependency)
2. CI builds a new EE image with a new version tag (e.g., `parasoltech-ee:1.1.0`)
3. The image is pushed to the container registry
4. An admin updates the Controller EE resource to point to the new tag
5. All job templates using that EE now run with the updated dependencies

This is a controlled, versioned process. The EE in production does not change until an admin deliberately updates it. Rollback is as simple as pointing back to the previous tag.

## Project Sync and Content Verification

### Project Sync

When Controller syncs a Project, it clones (or pulls) the Git repository and makes its contents available. You can trigger a sync manually, schedule it, or configure webhooks so that a Git push automatically triggers a sync.

The sync process:

1. Controller connects to the Git repository using the Source Control credential
2. It clones the repository (or fetches updates to an existing clone)
3. It scans the repository for playbook files and makes them available for Job Templates
4. If content verification is configured, it runs signature verification

### Content Verification with GPG

This is where the content signing from Module 8 closes the loop. When a Project has GPG content verification enabled:

1. Upload the public GPG key to Controller as a **GPG Public Key** credential
2. Configure the Project to use this credential for content verification
3. On every sync, Controller runs the equivalent of `ansible-sign project gpg-verify .` on the repository content

If verification succeeds, the Project syncs normally and its content is available. If verification fails -- because a file was modified, added, or removed after signing -- the sync fails. No job templates can run the unverified content.

```text
Complete supply chain:

Developer → Reviews code → Signs with ansible-sign → Pushes to Git
                                                          │
Controller ← Syncs Project ← Verifies GPG signature ─────┘
     │
     └── Runs playbook in EE ← Pulls EE from Hub
```

Every link in this chain is verified:

- The **content** is signed and verified (ansible-sign + GPG)
- The **runtime** is packaged and versioned (EE + container registry)
- The **access** is governed (RBAC + credentials)
- The **execution** is audited (job logs + notifications)

This is the mature automation practice the CoP set out to build.

## Exercises

### Exercise 1: Explore the AAP Interface

Log in to your AAP sandbox and explore the main navigation areas. Identify where each concept from this module lives in the UI:

- Organizations
- Projects
- Inventories
- Credentials
- Job Templates
- Workflows
- Execution Environments

!!! tip "Use the documentation"
    The AAP UI may vary slightly between versions. Refer to the [AAP documentation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/) for version-specific navigation instructions.

### Exercise 2: Create a Project

Create a Project in Controller:

1. Navigate to the Projects section
2. Create a new Project with:
    - **Name**: `Parasol Infrastructure`
    - **Organization**: your sandbox organization
    - **Source Control Type**: Git
    - **Source Control URL**: the URL of your course repository

3. Sync the Project and verify it succeeds

If you set up content signing in Module 8 and have a GPG public key, configure the Project to verify signatures during sync.

### Exercise 3: Create an Inventory

Create an Inventory in Controller:

1. Navigate to the Inventories section
2. Create a new Inventory:
    - **Name**: `Parasol Dev Environment`
    - **Organization**: your sandbox organization
3. Add a host manually (use `localhost` with `ansible_connection: local` for sandbox testing)
4. Create a group called `webservers` and add the host to it

### Exercise 4: Create and Launch a Job Template

Create a Job Template that ties together the Project and Inventory:

1. Navigate to Job Templates
2. Create a new Job Template:
    - **Name**: `Deploy Web Server`
    - **Project**: `Parasol Infrastructure`
    - **Playbook**: select a playbook from the synced Project
    - **Inventory**: `Parasol Dev Environment`
    - **Credentials**: select or create an appropriate credential

3. Launch the job template
4. Watch the output in real time
5. After completion, review the job details -- note the start time, end time, user, and status

### Exercise 5: Build a Simple Workflow

Create a Workflow that chains two job templates:

1. Navigate to Workflow Templates
2. Create a new Workflow Template:
    - **Name**: `Deploy and Verify`
    - **Organization**: your sandbox organization
3. Open the workflow visualizer
4. Add the `Deploy Web Server` job template as the first node
5. Add a second node (a simple verification playbook) connected with an "On Success" edge
6. Save and launch the workflow
7. Watch both nodes execute in sequence

### Exercise 6: Configure RBAC

Explore the RBAC model:

1. Navigate to Teams and create a team called `Operators`
2. Navigate to Users and create a test user or note an existing one
3. Add the user to the `Operators` team
4. On the `Deploy Web Server` job template, grant the `Operators` team **Execute** permission
5. Verify that the team can launch the job template but cannot edit it

!!! note "Sandbox limitations"
    Some sandbox environments may not support all RBAC operations. If you encounter permission restrictions, study the RBAC concepts and permission model in the documentation instead.

## Summary

In this module you:

- Learned that Ansible Automation Platform provides a centralized control plane with three components: **Controller** for orchestration and governance, **Automation Hub** for content distribution, and **Event-Driven Ansible** for event-based automation
- Mapped every CLI concept to its Controller equivalent -- playbooks become Job Templates, inventory files become Inventories with Sources, SSH keys become Credentials, and scripts become Schedules
- Created Job Templates that bundle a playbook, inventory, credentials, EE, and variables into a reusable, launchable unit of work
- Built Workflows that chain job templates with success, failure, and always edges to create robust multi-step automation pipelines with approval gates
- Configured Inventories from static hosts and SCM sources, and used Credentials to securely store and inject secrets without exposing them to users
- Set up RBAC with Organizations, Teams, and granular per-resource roles (Admin, Use, Execute, Read) to govern who can do what
- Integrated the Execution Environment from Module 8 with Controller, ensuring every job uses the same versioned, tested runtime
- Completed the supply chain security workflow: developers sign content with `ansible-sign`, push to Git, and Controller verifies the GPG signature on every Project Sync before allowing execution

The CoP at Parasol Tech now has a complete automation practice. Content is developed collaboratively (Module 6), tested rigorously (Module 7), packaged reproducibly (Module 8), and managed through a governed platform with RBAC, audit logging, and workflow orchestration (Module 9). The journey from Lionel running ad-hoc commands on a laptop to a fully governed enterprise automation practice is complete.

## Course Conclusion

Lionel leans back and looks at the dashboard. The deployment workflow ran overnight -- Project synced, GPG signatures verified, web servers deployed across three environments, health checks passed, notifications sent to the team channel. No one had to SSH into anything. No one typed `ansible-playbook` at 2 AM.

It is hard to believe this started with a single ad-hoc command on a laptop.

**The journey:**

- **Module 1** -- Lionel discovered Ansible and ran the first ad-hoc command. One engineer, one machine, one problem.
- **Module 2** -- Ad-hoc commands became playbooks. Automation became repeatable.
- **Module 3** -- Playbooks grew beyond localhost. Structured inventories organized hosts across environments.
- **Module 4** -- Variables and facts made playbooks flexible. The same automation adapted to different environments.
- **Module 5** -- Templates and handlers turned playbooks into configuration management tools. Services restarted when configs changed.
- **Module 6** -- The CoP formed. Roles and collections turned individual playbooks into reusable, shareable components. `ansible-creator` scaffolded the collection. `ade` managed the development environment.
- **Module 7** -- Quality gates went up. `ansible-lint` caught style issues, Molecule tested roles end-to-end, pytest validated logic, and tox-ansible orchestrated the matrix. No untested code reached production.
- **Module 8** -- Execution Environments eliminated "works on my machine." Content signing with `ansible-sign` proved that what runs in production is what the CoP reviewed. The supply chain was secured.
- **Module 9** -- Controller brought governance. Job templates, workflows, RBAC, audit logging, and centralized credential management replaced the chaos of everyone running playbooks from their own laptop.

What started as one person solving one problem is now an enterprise automation practice with testing, packaging, signing, and governance.

### What Comes Next

The core journey is complete, but there is more to explore:

**Domain tracks (Modules 10-11)**

- [Module 10 -- Linux Systems](10-linux-systems.md): Apply everything you have learned to Linux system administration -- user management, hardening, patching, and compliance at scale
- [Module 11 -- Network Automation](11-network-automation.md): Extend Ansible to network devices with `network_cli`, resource modules, and integration with NetBox as a source of truth

These tracks are optional and self-contained. They do not introduce new core concepts -- they apply the skills from modules 1-9 to specific domains.

**Community and certification**

- **Contribute to Ansible** -- The Ansible community thrives on contributions. Start by improving documentation, submitting bug reports, or sharing roles on [Ansible Galaxy](https://galaxy.ansible.com/). Join the community on [forum.ansible.com](https://forum.ansible.com/).
- **Red Hat Certification** -- Validate your skills with the [Red Hat Certified Engineer (RHCE)](https://www.redhat.com/en/services/certification/rhce) exam, which includes Ansible automation, or the [Red Hat Certified Specialist in Developing Automation with Ansible Automation Platform](https://www.redhat.com/en/services/certification/red-hat-certified-specialist-developing-automation-ansible-automation-platform) exam.
- **Ansible Development Tools** -- Continue exploring `adt` and its components. The tools evolve rapidly -- check the [Ansible Development Tools documentation](https://ansible.readthedocs.io/projects/dev-tools/) for the latest features.

**Keep practicing**

The best way to learn automation is to automate. Find a manual process at your organization, break it into the architecture hierarchy (landscape, type, function, component), write a role, test it with Molecule, package it as a collection, and deploy it through Controller. Then do it again with the next process.

The Zen of Ansible says it well: *"Ansible is not just a tool -- it is a practice."* This course gave you the tools and the patterns. The practice is yours to build.
