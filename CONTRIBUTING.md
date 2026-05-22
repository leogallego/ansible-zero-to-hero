# Contributing to Ansible Zero to Hero

Thank you for your interest in contributing! This guide covers how to submit content, translations, and fixes.

## Ways to Contribute

- **Fix typos or broken links** — open a PR with the fix
- **Improve explanations** — clarify concepts, add examples, fix inaccuracies
- **Add translations** — translate module content to new languages
- **Report issues** — open a GitHub issue describing the problem

## Content Guidelines

### Module content

- Write in active voice, second person ("you will" not "the learner will")
- Keep explanations concise and practical — this is a course, not a reference manual
- All Ansible code must follow the conventions below

### Ansible code conventions

All Ansible code in the course (module content and companion code) must follow these rules:

- Use Fully Qualified Collection Names: `ansible.builtin.copy`, not `copy`
- Use `ansible_facts['key']` bracket notation, never `ansible_distribution`
- Use `true`/`false`, never `yes`/`no`
- 2-space YAML indentation
- Name tasks in imperative form: "Install required packages", "Ensure service is running"
- Prefix all role variables with the role name

### MkDocs formatting

The site uses MkDocs Material with these extensions:

- **Admonitions**: `!!! note "Title"` with 4-space indented content
- **Tabbed content**: `=== "Tab Name"` with 4-space indented content
- **Code blocks**: Use language annotations (````yaml`, ````bash`, ````text`)

## Translation Guidelines

### Adding a new language

1. Create a new language directory under `docs/` (e.g., `docs/fr/`)
2. Mirror the English directory structure exactly
3. Add the language to `mkdocs.yml` under `plugins.i18n.languages`

### Translation rules

- **Translate**: prose, headings, admonition titles, exercise instructions
- **Do NOT translate**: code blocks, command outputs, FQCNs, variable names, file paths, technical terms that are universally used in English (playbook, handler, template, role, facts, Execution Environment)
- **Maintain accents and diacritical marks** appropriate to the target language
- Use the same file names as the English version (MkDocs i18n maps by filename)

## Development Setup

1. Clone the repository
2. Open in the devcontainer (VS Code + Docker/Podman)
3. Run `mkdocs serve` to preview the site at `http://localhost:8000`
4. Make your changes and verify they render correctly

## Submitting Changes

1. Fork the repository
2. Create a branch for your changes
3. Make your changes following the guidelines above
4. Open a pull request with a clear description of what changed and why

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code. Report unacceptable behavior by opening a GitHub issue.
