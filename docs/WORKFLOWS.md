<p align="center">
    <a href="https://github.com/the-lupaxa-project">
        <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/the-lupaxa-project/readme-logo.png" alt="The Lupaxa Project Logo" />
    </a>
</p>

<h1 align="center">Reusable Workflow Catalogue</h1>

This document provides the reference guide for every reusable GitHub Actions workflow maintained by **The Lupaxa Project**.

These workflows form the shared automation platform used throughout repositories across every Lupaxa GitHub organisation. By centralising common automation
into reusable workflows, repositories benefit from consistent behaviour, simplified maintenance, reduced duplication, and a consistent security model.

The workflows are designed to be modular, reusable, configurable and easy to adopt, allowing individual repositories to remain small while still benefiting
from a comprehensive CI/CD platform.

> [!NOTE]
>
> ## Repository at a Glance
>
> This repository provides the shared GitHub Actions automation platform used throughout **The Lupaxa Project**.
>
> - **Over 30 reusable workflows** organised into **7 functional categories**.
> - Shared automation used across all Lupaxa Project repositories.
> - Consistent workflow interfaces with configurable inputs.
> - Centralised maintenance with minimal repository duplication.
> - Built around GitHub reusable workflows (`workflow_call`).
> - Designed with security, consistency and long-term maintainability in mind.

# Contents

- [Workflow Catalogue](#workflow-catalogue)
- [Workflow Architecture](#workflow-architecture)
- [Using Reusable Workflows](#using-reusable-workflows)
- [Design Principles](#design-principles)
- [Standard Validation Interface](#standard-validation-interface)
- [Repository Quality](#repository-quality)
- [Language Analysis](#language-analysis)
- [Security](#security)
- [Documentation](#documentation)
- [Release Management](#release-management)
- [Repository Automation](#repository-automation)
- [Frequently Asked Questions](#frequently-asked-questions)
- [Best Practices](#best-practices)
- [Workflow Relationships](#workflow-relationships)
- [Further Reading](#further-reading)

# Workflow Catalogue

The following table provides a quick overview of every reusable workflow available in this repository.

| #   | Workflow                                                                    | Category               | Level        | Typical Use                                                                    |
| :-: |:--------------------------------------------------------------------------- | :--------------------- | :----------: | :----------------------------------------------------------------------------- |
|   1 | [Citation Validator](#citation-validator)                                   | Repository Quality     | Basic        | Validate repository citation metadata before publishing.                       |
|   2 | [Code Analysis](#code-analysis)                                             | Security               | Intermediate | Identify security vulnerabilities and code quality issues using GitHub CodeQL. |
|   3 | [Dependabot Manager](#dependabot-manager)                                   | Repository Automation  | Intermediate | Automatically manage Dependabot Pull Requests.                                 |
|   4 | [Dockerfile Linter](#dockerfile-linter)                                     | Language Analysis      | Basic        | Check Dockerfiles for best practices and common issues.                        |
|   5 | [First-Time Contributor Greetings](#first-time-contributor-greetings)       | Repository Automation  | Basic        | Welcome new contributors with automated messages.                              |
|   6 | [GitHub Actions Security](#github-actions-security)                         | Security               | Intermediate | Verify GitHub Actions workflows follow security best practices.                |
|   7 | [GitHub Release Generator](#github-release-generator)                       | Release Management     | Advanced     | Create and publish GitHub Releases from repository tags.                       |
|   8 | [JSON Validator](#json-validator)                                           | Repository Quality     | Basic        | Validate JSON configuration and data files.                                    |
|   9 | [Link Checker](#link-checker)                                               | Repository Quality     | Intermediate | Detect broken or invalid links in documentation.                               |
|  10 | [Markdown Linter](#markdown-linter)                                         | Repository Quality     | Basic        | Check Markdown documentation for formatting and style issues.                  |
|  11 | [MkDocs Site Publisher](#mkdocs-site-publisher)                             | Documentation          | Advanced     | Build and publish MkDocs documentation to GitHub Pages.                        |
|  12 | [Perl Linter](#perl-linter)                                                 | Language Analysis      | Basic        | Analyse Perl source code for syntax and quality issues.                        |
|  13 | [PHP Linter](#php-linter)                                                   | Language Analysis      | Basic        | Analyse PHP source code for syntax and coding issues.                          |
|  14 | [Puppet Linter](#puppet-linter)                                             | Language Analysis      | Basic        | Validate Puppet manifests against best practices.                              |
|  15 | [Python Code Auditor](#python-code-auditor)                                 | Language Analysis      | Basic        | Perform comprehensive static analysis of Python projects.                      |
|  16 | [Python Continuous Integration](#python-continuous-integration)             | Continuous Integration | Advanced     | Build, lint, test and validate Python projects.                                |
|  17 | [Python Continuous Integration (Make)](#python-continuous-integration-make) | Continuous Integration | Intermediate | Execute Makefile-driven Python CI pipelines.                                   |
|  18 | [Python Dependency Updater](#python-dependency-updater)                     | Release Management     | Basic        | Check Python dependencies for available updates.                               |
|  19 | [Python DocString Checker](#python-docstring-checker)                       | Language Analysis      | Basic        | Validate Python documentation strings.                                         |
|  20 | [Python Linter](#python-linter)                                             | Language Analysis      | Basic        | Check Python source code for linting issues.                                   |
|  21 | [Python Security Scanner](#python-security-scanner)                         | Language Analysis      | Basic        | Scan Python projects for common security vulnerabilities.                      |
|  22 | [Python Style Guide Checker](#python-style-guide-checker)                   | Language Analysis      | Basic        | Verify compliance with Python style guidelines.                                |
|  23 | [Ruby Code Smell Detector](#ruby-code-smell-detector)                       | Language Analysis      | Basic        | Detect maintainability and design issues in Ruby code.                         |
|  24 | [Ruby Linter](#ruby-linter)                                                 | Language Analysis      | Basic        | Check Ruby source code against coding standards.                               |
|  25 | [Secrets Scanner](#secrets-scanner)                                         | Security               | Intermediate | Detect exposed secrets and credentials in repositories.                        |
|  26 | [Shell Script Linter](#shell-script-linter)                                 | Language Analysis      | Basic        | Analyse shell scripts for portability and scripting issues.                    |
|  27 | [Stale Issue & Pull Request Handler](#stale-issue--pull-request-handler)    | Repository Automation  | Intermediate | Automatically manage inactive Issues and Pull Requests.                        |
|  28 | [Workflow Clean Up](#workflow-clean-up)                                     | Repository Automation  | Advanced     | Remove obsolete workflow runs and artifacts.                                   |
|  29 | [Workflow History Purge](#workflow-history-purge)                           | Repository Automation  | Advanced     | Permanently delete completed GitHub Actions workflow history.                  |
|  30 | [Workflow Notifier](#workflow-notifier)                                     | Repository Automation  | Advanced     | Send workflow status notifications to Slack.                                   |
|  31 | [Workflow Scheduler Test](#workflow-scheduler-test)                         | Repository Automation  | Basic        | Verify scheduled GitHub Actions workflows execute correctly.                   |
|  32 | [Workflow Summary](#workflow-summary)                                       | Repository Automation  | Intermediate | Generate summaries of GitHub Actions workflow runs.                            |
|  33 | [YAML Linter](#yaml-linter)                                                 | Repository Quality     | Basic        | Validate YAML configuration files.                                             |

> [!TIP]
> **Level Guide**
>
> - **Basic** – Simple wrapper around a shared validation pipeline with minimal configuration.
> - **Intermediate** – Adds orchestration, multiple configuration options or integrates with additional GitHub Actions.
> - **Advanced** – Provides feature-rich automation with extensive configuration, multiple stages or comprehensive repository management.

[↑ Back to Contents](#contents)

# Workflow Architecture

All workflows within this repository are implemented using GitHub's `workflow_call` feature.

Instead of embedding large amounts of workflow logic into every repository, individual repositories contain only lightweight workflows responsible for deciding
**when** automation should execute.

The implementation itself is delegated to a reusable workflow maintained within this repository.

```text
    Repository Workflow
            │
            ▼
    Reusable Workflow
            │
            ▼
    Shared Automation
```

This architecture provides several important advantages.

- Consistent behaviour across repositories.
- Reduced duplication.
- Centralised maintenance.
- Smaller repository workflows.
- Faster adoption of improvements.
- Consistent security practices.
- Shared engineering standards.

[↑ Back to Contents](#contents)

# Using Reusable Workflows

Reusable workflows are referenced using GitHub's `uses:` syntax.

A minimal example is shown below.

```yaml
jobs:
  markdown:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-markdown-linter.yml@master
```

Most workflows expose optional inputs that allow behaviour to be customised without modifying the reusable workflow itself.

[↑ Back to Contents](#contents)

# Design Principles

Every reusable workflow follows the same engineering philosophy.

## Consistency

Workflows expose consistent interfaces wherever practical, making it easier to move between different workflows without learning a new configuration model each
time.

## Simplicity

Repository workflows should remain small.

Complex implementation belongs inside reusable workflows rather than being duplicated throughout consuming repositories.

## Security

Workflows request only the GitHub permissions required to perform their task.

Third-party GitHub Actions are pinned to immutable commit SHAs to reduce supply-chain risk and improve reproducibility.

## Shared Tooling

Many validation workflows delegate execution to shared tooling maintained within the **CICDToolbox** project.

This allows improvements to validation logic to be shared automatically across all repositories that consume these workflows.

[↑ Back to Contents](#contents)

# Standard Validation Interface

Most validation workflows use the same configuration interface.

Learning one validation workflow therefore makes the others immediately familiar.

## Common Inputs

Unless stated otherwise, these are the common inputs supported by validation workflows.

| Input           | Description                                   |
| :-------------- | :-------------------------------------------- |
| `include_files` | Files or regular expressions to include.      |
| `exclude_files` | Files or regular expressions to exclude.      |
| `no_color`      | Disable ANSI coloured output.                 |
| `report_only`   | Report problems without failing the workflow. |
| `show_errors`   | Display detailed validation errors.           |
| `show_skipped`  | Display skipped files.                        |

## Common Setup

Unless documented otherwise, validation workflows:

- require only `contents: read` permission;
- require no secrets;
- execute a shared **CICDToolbox** validation pipeline.

[↑ Back to Contents](#contents)

# Repository Quality

Repository Quality workflows validate repository metadata, documentation and configuration files to help maintain consistent, well-structured repositories.

| Workflow                                  | Typical Use                                                   |
| :---------------------------------------- | :------------------------------------------------------------ |
| [Citation Validator](#citation-validator) | Validate repository citation metadata before publishing.      |
| [JSON Validator](#json-validator)         | Validate JSON configuration and data files.                   |
| [Link Checker](#link-checker)             | Detect broken or invalid links in documentation.              |
| [Markdown Linter](#markdown-linter)       | Check Markdown documentation for formatting and style issues. |
| [YAML Linter](#yaml-linter)               | Validate YAML configuration files.                            |

## Citation Validator

Validates CITATION.cff and related citation metadata to ensure it conforms to the Citation File Format specification. This workflow helps repositories maintain
accurate and machine-readable citation information for users, package indexes and research tools.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  citations:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-citation-validator.yml@master
```

## JSON Validator

Validates JSON files to ensure they are syntactically correct and suitable for use by applications, automation and configuration management systems.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  json:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-json-validator.yml@master
```

## Link Checker

Checks hyperlinks throughout repository documentation to identify broken, redirected or invalid links before documentation is published or released.

Unlike the other Repository Quality workflows, Link Checker also supports additional configuration for AwesomeBot.

### Inputs

[↑ Common Inputs](#common-inputs)

### Additional Inputs

| Input       | Description                                   |
| :---------- | :-------------------------------------------- |
| `flags`     | Additional AwesomeBot command-line arguments. |
| `whitelist` | Comma-separated list of URLs to ignore.       |

### Example

```yaml
jobs:
  links:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-link-checker.yml@master
```

## Markdown Linter

Analyses Markdown documentation for formatting, structure and style issues to help maintain consistent, readable and high-quality project documentation.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  markdown:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-markdown-linter.yml@master
```

## YAML Linter

Validates YAML files for syntax errors and formatting issues, helping ensure configuration files remain reliable, readable and suitable for automation.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  yaml:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-yaml-linter.yml@master
```

[↑ Back to Contents](#contents)

# Continuous Integration

Continuous Integration workflows provide complete build, test and validation pipelines for supported languages.

Unlike the validation workflows described in the previous section, these workflows orchestrate multiple quality tools and testing stages to provide
comprehensive Continuous Integration for a project.

| Workflow                                                                    | Typical Use                                     |
| :-------------------------------------------------------------------------- | :---------------------------------------------- |
| [Python Continuous Integration](#python-continuous-integration)             | Build, lint, test and validate Python projects. |
| [Python Continuous Integration (Make)](#python-continuous-integration-make) | Execute Makefile-driven Python CI pipelines.    |

## Python Continuous Integration

Provides a complete Continuous Integration pipeline for Python projects, including dependency installation, linting, type checking and automated testing across
multiple Python versions. This workflow is intended for repositories that follow a conventional Python project structure. It automatically installs project
dependencies before executing a standard quality pipeline consisting of linting, static analysis and automated tests.

### Features

- Matrix testing across multiple Python versions.
- Automatic dependency installation.
- Ruff linting.
- mypy type checking.
- pytest execution.
- Configurable project paths.

### Inputs

| Input             | Description                                                       |
| :---------------- | :---------------------------------------------------------------- |
| `paths`           | Comma-separated list of project directories or files to validate. |
| `python_versions` | Comma-separated list of Python versions to test.                  |

### Example

```yaml
jobs:
  python-ci:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-ci.yml@master
    with:
      paths: src,tests
```

### Notes

This workflow installs project dependencies automatically before running Ruff, mypy and pytest. If a `tests/` directory exists, the project's test suite is
executed automatically.

## Python Continuous Integration (Make)

Executes Continuous Integration using the repository's existing Makefile targets, allowing projects to retain custom build logic while using a shared reusable
workflow.

This workflow is intended for repositories that standardise their development lifecycle through Make targets. Rather than embedding the CI implementation within
the reusable workflow, it delegates execution to the project's existing Makefile.

### Features

- Matrix testing across multiple Python versions.
- Configurable Make targets.
- Minimal repository configuration.
- Supports custom project layouts.
- Reuses existing repository automation.

### Inputs

| Input             | Description                                             |
| :---------------- | :------------------------------------------------------ |
| `ci_target`       | Make target executed to perform Continuous Integration. |
| `install_target`  | Make target used to install project dependencies.       |
| `python_versions` | Comma-separated list of Python versions to test.        |

### Example

```yaml
jobs:
  python-ci:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-makefile-ci.yml@master
```

### Notes

This workflow provides a lightweight wrapper around a repository's existing Makefile-based automation. It allows each project to define its own build and
quality process while providing a consistent reusable workflow interface across The Lupaxa Project.

[↑ Back to Contents](#contents)

# Language Analysis

Language Analysis workflows perform language-specific linting and static analysis.

Most language validation workflows use the **Standard Validation Interface**, allowing repositories to configure different language validators in exactly
the same way.

| Workflow                                                  | Typical Use                                                 |
| :-------------------------------------------------------- | :---------------------------------------------------------- |
| [Dockerfile Linter](#dockerfile-linter)                   | Check Dockerfiles for best practices and common issues.     |
| [Perl Linter](#perl-linter)                               | Analyse Perl source code for syntax and quality issues.     |
| [PHP Linter](#php-linter)                                 | Analyse PHP source code for syntax and coding issues.       |
| [Puppet Linter](#puppet-linter)                           | Validate Puppet manifests against best practices.           |
| [Python Code Auditor](#python-code-auditor)               | Perform comprehensive static analysis of Python projects.   |
| [Python DocString Checker](#python-docstring-checker)     | Validate Python documentation strings.                      |
| [Python Linter](#python-linter)                           | Check Python source code for linting issues.                |
| [Python Security Scanner](#python-security-scanner)       | Scan Python projects for common security vulnerabilities.   |
| [Python Style Guide Checker](#python-style-guide-checker) | Verify compliance with Python style guidelines.             |
| [Ruby Code Smell Detector](#ruby-code-smell-detector)     | Detect maintainability and design issues in Ruby code.      |
| [Ruby Linter](#ruby-linter)                               | Check Ruby source code against coding standards.            |
| [Shell Script Linter](#shell-script-linter)               | Analyse shell scripts for portability and scripting issues. |

All of the above workflows:

- use the Standard Validation Interface;
- require only `contents: read`;
- require no secrets;
- execute a shared CICDToolbox validation pipeline.

## Dockerfile Linter

Analyses Dockerfiles for syntax issues, security concerns and container best practices using Hadolint. This helps ensure container images are built using
modern, secure and maintainable practices.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  dockerfile:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-dockerfile-linter.yml@master
```

## Perl Linter

Analyses Perl source code for syntax errors, style issues and maintainability concerns using the standard Perl validation pipeline.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  perl:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-perl-linter.yml@master
```

## PHP Linter

Validates PHP source code for syntax errors and common coding issues, helping maintain reliable and consistent PHP projects.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  php:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-php-linter.yml@master
```

## Puppet Linter

Checks Puppet manifests for syntax, style and best practice compliance, helping maintain consistent and reliable infrastructure code.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  puppet:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-puppet-linter.yml@master
```

## Python Code Auditor

Executes comprehensive static analysis of Python projects using multiple quality checks to identify maintainability issues beyond traditional linting.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  audit:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-code-auditor.yml@master
```

## Python DocString Checker

Checks Python docstrings for completeness and compliance with recognised documentation standards, helping maintain well-documented APIs and libraries.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  docstrings:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-docstring-checker.yml@master
```

## Python Linter

Analyses Python source code for syntax, style and programming issues using the standard Python linting pipeline.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  pylint:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-linter.yml@master
```

## Python Security Scanner

Performs automated security analysis of Python projects using Bandit to identify common security vulnerabilities before deployment or release.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  security:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-security-scanner.yml@master
```

## Python Style Guide Checker

Checks Python source code against recognised style guidelines to encourage consistent formatting and maintainable code.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  style:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-style-guide-checker.yml@master
```

## Ruby Code Smell Detector

Analyses Ruby projects for design issues, complexity and maintainability concerns using Reek to encourage cleaner object-oriented design.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  reek:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-ruby-code-smell-detector.yml@master
```

## Ruby Linter

Analyses Ruby source code using RuboCop to identify syntax, style and maintainability issues while encouraging consistent coding standards.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  ruby:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-ruby-linter.yml@master
```

## Shell Script Linter

Analyses shell scripts for syntax errors, portability issues and common scripting mistakes using ShellCheck.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  shellcheck:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-shell-script-linter.yml@master
```

[↑ Back to Contents](#contents)

# Security

Security workflows help identify vulnerabilities in source code, repository configuration and GitHub Actions workflows.

These workflows are intended to complement the language-specific validation workflows by focusing on security posture rather than coding style or correctness.

| Workflow                                            | Typical Use                                                                    |
| :-------------------------------------------------- | :----------------------------------------------------------------------------- |
| [Code Analysis](#code-analysis)                     | Identify security vulnerabilities and code quality issues using GitHub CodeQL. |
| [GitHub Actions Security](#github-actions-security) | Verify GitHub Actions workflows follow security best practices.                |
| [Secrets Scanner](#secrets-scanner)                 | Detect exposed secrets and credentials in repositories.                        |

## Code Analysis

Performs static application security testing using GitHub CodeQL. The workflow analyses supported programming languages for security vulnerabilities,
reliability issues and code quality problems before publishing results to GitHub Code Scanning.

Unlike the validation workflows, Code Analysis uses GitHub's native Code Scanning platform and publishes results directly into the repository's Security tab.

### Features

- Multi-language analysis.
- GitHub CodeQL.
- Security & Quality query suite.
- Automatic project build.
- Native GitHub Code Scanning integration.

### Inputs

| Input       | Description                                          |
| :---------- | :--------------------------------------------------- |
| `languages` | Comma-separated list of CodeQL languages to analyse. |

### Additional Permissions

```yaml
actions: read
security-events: write
```

### Example

```yaml
jobs:
  code-analysis:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-code-analysis.yml@master
    with:
      languages: python
```

### Notes

Results are published directly to GitHub Code Scanning where they can be reviewed alongside other repository security findings.

## GitHub Actions Security

Reviews GitHub Actions workflows to ensure third-party actions are pinned to immutable commit SHAs and comply with The Lupaxa Project's workflow security
standards.

### Features

- SHA pin verification.
- Repository allow-list support.
- Dry-run mode.
- Pull Request friendly.

### Inputs

| Input        | Description                                                  |
| :----------- | :----------------------------------------------------------- |
| `allow_list` | Additional repositories permitted to use non-SHA references. |
| `dry_run`    | Report issues without failing the workflow.                  |

### Additional Permissions

```yaml
pull-requests: write
```

### Example

```yaml
jobs:
  workflow-security:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-github-actions-security.yml@master
```

### Notes

Repositories within **The Lupaxa Project** are automatically trusted where appropriate, allowing reusable workflows from this repository to be consumed
without triggering validation failures.

## Secrets Scanner

Scans repositories and Git history for exposed credentials, API keys and other sensitive information using TruffleHog, helping prevent accidental secret
disclosure.

Unlike the validation workflows, Secrets Scanner analyses repository history as well as the working tree to identify verified and potential secrets.

### Features

- Repository scanning.
- Incremental Pull Request scanning.
- Full repository history support.
- Configurable TruffleHog arguments.

### Inputs

| Input        | Description                      |
| :----------- | :------------------------------- |
| `path`       | Repository path to scan.         |
| `base`       | Base Git reference.              |
| `head`       | Head Git reference.              |
| `extra_args` | Additional TruffleHog arguments. |

### Additional Permissions

```yaml
pull-requests: read
```

### Example

```yaml
jobs:
  secrets:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-secrets-scanner.yml@master
```

### Notes

The repository is checked out with the complete Git history to allow TruffleHog to perform historical secret detection where appropriate.

[↑ Back to Contents](#contents)

# Documentation

Documentation workflows build and publish project documentation.

| Workflow                                        | Typical Use                                             |
| :---------------------------------------------- | :------------------------------------------------------ |
| [MkDocs Site Publisher](#mkdocs-site-publisher) | Build and publish MkDocs documentation to GitHub Pages. |

## MkDocs Site Publisher

Builds MkDocs documentation sites and publishes them to GitHub Pages using a consistent deployment pipeline. The workflow simplifies documentation publishing
while ensuring repeatable builds.

### Features

- Python environment setup.
- Dependency installation.
- MkDocs build.
- GitHub Pages deployment.
- Optional cleanup of previous deployments.
- Automatic fallback installation when project development dependencies are unavailable.

### Inputs

| Input            | Description                                                 |
| :--------------- | :---------------------------------------------------------- |
| `python_version` | Python version used during the build.                       |
| `cleanup`        | Remove previous GitHub Pages deployments before publishing. |
| `use_dev_extras` | Install project development dependencies when available.    |

### Additional Permissions

```yaml
pages: write
deployments: write
id-token: write
```

### Example

```yaml
jobs:
  documentation:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-mkdocs-site-publisher.yml@master
```

### Notes

If installation of project development dependencies fails, the workflow automatically installs a minimal MkDocs environment to ensure documentation can still
be generated and published.

[↑ Back to Contents](#contents)

# Release Management

Release Management workflows automate project releases and dependency maintenance.

| Workflow                                                | Typical Use                                              |
| :------------------------------------------------------ | :------------------------------------------------------- |
| [GitHub Release Generator](#github-release-generator)   | Create and publish GitHub Releases from repository tags. |
| [Python Dependency Updater](#python-dependency-updater) | Check Python dependencies for available updates.         |

## GitHub Release Generator

Automatically creates GitHub Releases by generating release notes, resolving version information and publishing releases from repository tags.

### Features

- Automatic version detection.
- Automatic release note generation.
- Draft releases.
- Pre-release support.
- Custom release names.
- Optional GitHub token.

### Inputs

| Input          | Description                           |
| :------------- | :------------------------------------ |
| `tag`          | Tag to release.                       |
| `release_name` | Override the generated release title. |
| `draft`        | Create a draft release.               |
| `prerelease`   | Publish as a pre-release.             |

### Additional Permissions

```yaml
contents: write
```

### Optional Secrets

```text
github_token
```

### Example

```yaml
jobs:
  release:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-github-release-generator.yml@master
```

### Notes

If no tag is supplied, the workflow automatically determines the version from the triggering Git reference.

## Python Dependency Updater

Checks Python projects for outdated dependencies using automated dependency analysis, helping repositories remain current with the latest package releases.

### Inputs

[↑ Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  dependencies:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-dependency-updater.yml@master
```

[↑ Back to Contents](#contents)

# Repository Automation

Repository Automation workflows manage repositories, Issues, Pull Requests, workflow runs and external integrations.

| Workflow                                                                 | Typical Use                                                   |
| :----------------------------------------------------------------------- | :------------------------------------------------------------ |
| [Dependabot Manager](#dependabot-manager)                                | Automatically manage Dependabot Pull Requests.                |
| [First-Time Contributor Greetings](#first-time-contributor-greetings)    | Welcome new contributors with automated messages.             |
| [Stale Issue & Pull Request Handler](#stale-issue--pull-request-handler) | Automatically manage inactive Issues and Pull Requests.       |
| [Workflow Clean Up](#workflow-clean-up)                                  | Remove obsolete workflow runs and artifacts.                  |
| [Workflow History Purge](#workflow-history-purge)                        | Permanently delete completed GitHub Actions workflow history. |
| [Workflow Notifier](#workflow-notifier)                                  | Send workflow status notifications to Slack.                  |
| [Workflow Scheduler Test](#workflow-scheduler-test)                      | Verify scheduled GitHub Actions workflows execute correctly.  |
| [Workflow Summary](#workflow-summary)                                    | Generate summaries of GitHub Actions workflow runs.           |

## Dependabot Manager

Automatically manages Pull Requests created by Dependabot by applying labels, approving updates and merging eligible dependency changes according to the
configured repository policy.

### Features

- Automatic approval.
- Automatic merge.
- Major version detection.
- Configurable labels.
- Dependabot-only execution.

### Inputs

| Input                  | Description                                   |
| :--------------------- | :-------------------------------------------- |
| `auto_approve`         | Automatically approve eligible Pull Requests. |
| `auto_merge`           | Automatically merge eligible Pull Requests.   |
| `handle_major_updates` | Control handling of major version updates.    |
| `approve_label`        | Label applied to auto-approved Pull Requests. |
| `merge_label`          | Label applied before automatic merge.         |
| `major_update_label`   | Label applied to major version updates.       |

### Additional Permissions

```yaml
contents: write
pull-requests: write
```

### Example

```yaml
jobs:
  dependabot:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-dependabot-manager.yml@master
```

### Notes

This workflow only executes when the triggering actor is `dependabot[bot]`.

## First-Time Contributor Greetings

Automatically posts friendly welcome messages when contributors open their first Issue or Pull Request. The workflow provides a consistent onboarding
experience while encouraging community participation.

### Features

- Separate Issue and Pull Request messages.
- Configurable welcome text.
- Uses GitHub's official First Interaction Action.

### Inputs

| Input           | Description                                    |
| :-------------- | :--------------------------------------------- |
| `issue_message` | Welcome message posted to first Issues.        |
| `pr_message`    | Welcome message posted to first Pull Requests. |

### Required Secrets

```text
repo-token
```

### Additional Permissions

```yaml
issues: write
pull-requests: write
```

### Example

```yaml
jobs:
  greetings:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-first-time-contributor-greetings.yml@master
    secrets:
      repo-token: ${{ secrets.GITHUB_TOKEN }}
```

## Stale Issue & Pull Request Handler

Identifies inactive Issues and Pull Requests, applies configurable stale labels, notifies contributors and optionally closes abandoned discussions according to
repository policy.

### Features

- Independent Issue and Pull Request policies.
- Configurable stale and close periods.
- Custom notification messages.
- Configurable labels.
- Label-based exemptions.
- Optional Slack notifications.

### Additional Permissions

```yaml
issues: write
pull-requests: write
```

### Example

```yaml
jobs:
  stale:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-stale-issue-and-pull-request-handler.yml@master
```

### Notes

The workflow is built on GitHub's official `actions/stale` action while exposing a consistent configuration model across repositories.

## Workflow Summary

Generates concise Markdown summaries of GitHub Actions workflow runs and optionally uploads them as workflow artifacts for later review.

### Features

- Markdown summary generation.
- Artifact upload.
- Configurable retention period.
- Ignore selected jobs.

### Inputs

| Input                     | Description                     |
| :------------------------ | :------------------------------ |
| `ignore_jobs`             | Jobs excluded from the summary. |
| `upload_artifact`         | Upload the generated report.    |
| `artifact_retention_days` | Artifact retention period.      |

### Additional Permissions

```yaml
actions: read
```

### Example

```yaml
jobs:
  summary:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-summary.yml@master
```

## Workflow Notifier

Sends configurable Slack notifications summarising GitHub Actions workflow execution, helping teams monitor automation activity and quickly identify failures.

### Features

- Slack notifications.
- Notify on selected workflow results.
- Optional per-job reporting.
- Optional commit message inclusion.
- Ignore selected jobs.
- Automatic suppression for unsupported events.

### Inputs

| Input                    | Description                                              |
| :----------------------- | :------------------------------------------------------- |
| `notify_on_results`      | Workflow results that should trigger a notification.     |
| `include_jobs`           | Include individual job results in the notification.      |
| `include_commit_message` | Include the triggering commit message.                   |
| `ignore_jobs`            | Comma-separated list of jobs to exclude from the report. |

### Additional Permissions

```yaml
actions: read
```

### Required Secrets

```text
slack_webhook_url
```

### Example

```yaml
jobs:
  notify:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-notifier.yml@master
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Notes

Notifications are automatically suppressed for unsupported events, including external fork Pull Requests and Dependabot Pull Requests, preventing unnecessary
notifications while maintaining repository security.

## Workflow Clean Up

Maintains GitHub Actions workflow runs and artifacts using a simple retention-based cleanup policy.

This workflow is intended for routine scheduled maintenance. It removes old completed workflow runs, optionally removes runs whose workflow file no longer
exists, optionally deletes old workflow artifacts and preserves a small number of recent successful representative runs for each workflow on the configured branch.

### Typical Use

- Keep GitHub Actions history manageable.
- Remove old completed workflow runs.
- Remove runs from deleted or renamed workflow files.
- Delete old workflow artifacts.
- Preserve recent successful workflow history for reference.
- Produce a Markdown cleanup report.

### Features

- Retention-based workflow run cleanup.
- Optional artifact cleanup.
- Optional obsolete workflow run removal.
- Preserves the latest successful runs per workflow on the configured branch.
- Optional deletion of old skipped and neutral runs.
- Dry-run mode.
- Workflow run and artifact delete limits.
- Configurable delay between delete requests.
- Retry support for transient GitHub API failures.
- Configurable progress output and verbosity.
- Markdown report generation.
- Optional report artifact upload.

### Inputs

| Input                            | Description                                                                           |
| :------------------------------- | :------------------------------------------------------------------------------------ |
| `retention_days`                 | Delete completed workflow runs older than this many days.                             |
| `artifact_retention_days`        | Delete artifacts older than this many days when artifact cleanup is enabled.          |
| `dry_run`                        | Report what would be deleted without deleting anything.                               |
| `cleanup_artifacts`              | Also delete old repository workflow artifacts.                                        |
| `remove_obsolete`                | Remove completed workflow runs whose workflow file no longer exists.                  |
| `preserve_branch`                | Branch used when preserving representative successful workflow runs.                  |
| `keep_last_n_successful`         | Number of recent successful completed runs to keep per workflow on `preserve_branch`. |
| `delete_skipped`                 | Delete skipped runs when they are older than the retention period.                    |
| `delete_neutral`                 | Delete neutral runs when they are older than the retention period.                    |
| `max_deletes_per_run`            | Maximum workflow runs to delete in one cleanup execution. Use `0` for unlimited.      |
| `max_artifact_deletes_per_run`   | Maximum artifacts to delete in one cleanup execution. Use `0` for unlimited.          |
| `delete_sleep_seconds`           | Seconds to sleep between delete calls to reduce API throttling risk.                  |
| `progress_every`                 | Print progress after this many inspected workflow runs. Use `0` to disable.           |
| `verbosity`                      | Log verbosity. Use `quiet`, `normal` or `verbose`.                                    |
| `api_retries`                    | Number of retries for transient GitHub API failures.                                  |
| `upload_report_artifact`         | Upload the generated Markdown cleanup report as a workflow artifact.                  |
| `report_artifact_retention_days` | Number of days to retain the uploaded cleanup report artifact.                        |

### Additional Permissions

```yaml
actions: write
```

### Example

```yml
jobs:
  cleanup:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-clean-up.yml@master
```

### Notes

- This workflow is designed for routine scheduled maintenance.
- Dry-run mode should be used when introducing the workflow to a repository.
- The currently running workflow run is always preserved.
- This workflow is not intended to purge all workflow history.
- Use Workflow History Purge when a repository-wide reset of Actions history is required.

## Workflow History Purge

Permanently deletes completed GitHub Actions workflow runs from a repository.

Unlike **Workflow Clean Up**, which applies configurable retention policies, **Workflow History Purge** is intended for one-off administrative tasks where all
historical workflow runs should be removed. Typical use cases include preparing template repositories, clearing test history or resetting repositories before
publication.

### Typical Use

- Remove historical workflow runs.
- Reset GitHub Actions history.
- Prepare template repositories.
- Remove test and development workflow history.
- Start a project with a clean workflow history.

### Features

- Deletes all completed workflow runs.
- Automatically skips active and queued workflow runs.
- Dry-run mode enabled by default.
- Configurable deletion limit.
- Configurable delay between API requests.
- Automatic retry of transient GitHub API failures.
- Configurable verbosity levels.
- Produces a detailed execution summary.
- Built-in confirmation safeguards for destructive operations.

### Inputs

| Input | Description |
| :---- | :---------- |
| `dry_run` | Report what would be deleted without deleting workflow runs. |
| `limit` | Maximum number of completed workflow runs to delete. Use `0` for unlimited. |
| `delay_seconds` | Delay between delete requests in seconds. |
| `verbosity` | Output verbosity (`0` = summary, `1` = progress, `2` = detailed). |
| `retries` | Number of retries for transient GitHub API failures. |
| `confirm` | Confirms destructive deletion when `dry_run` is disabled. |

### Default Permissions

```yaml
actions: write
contents: read
```

### Required Secrets

None.

### Example

```yaml
jobs:
  workflow-history-purge:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-history-purge.yml@master
    with:
      dry_run: true
```

### Notes

- This workflow permanently deletes GitHub Actions workflow history.
- The currently executing workflow cannot be deleted and is automatically skipped.
- Active and queued workflow runs are automatically skipped.
- Dry-run mode is enabled by default.
- A confirmation flag is required before destructive deletion is permitted.
- This workflow is intended for occasional administrative use rather than routine repository maintenance.

[↑ Back to Contents](#contents)

## Workflow Scheduler Test

Provides a lightweight diagnostic workflow for confirming that scheduled GitHub Actions workflows are executing correctly and that runner environments are
operating as expected.

### Features

- Displays workflow metadata.
- Displays runner information.
- Displays execution time.
- Displays GitHub context.
- Lightweight diagnostic output.

### Example

```yaml
jobs:
  scheduler-test:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-scheduler-test.yml@master
```

[↑ Back to Contents](#contents)

# Frequently Asked Questions

## Can multiple reusable workflows be used together?

Yes.

Repositories commonly combine multiple reusable workflows within a single GitHub Actions workflow, with each reusable workflow responsible for a specific
task.

For example, a repository might execute:

- Markdown Linter
- YAML Linter
- Python Continuous Integration
- Secrets Scanner

as independent jobs within the same workflow.

## Why do so many workflows look similar?

Many workflows share the **Standard Validation Interface** and delegate execution to common tooling maintained by **CICDToolbox**.

This consistency reduces the learning curve and simplifies adoption across multiple repositories.

## Do I need to use every workflow?

No.

Each reusable workflow is independent.

Repositories should enable only those workflows appropriate for their language, tooling and automation requirements.

## Can workflow behaviour be customised?

Yes.

Most workflows expose configurable inputs allowing behaviour to be customised without modifying the reusable workflow itself.

## Why are GitHub Actions pinned to commit SHAs?

Pinning actions to immutable commit SHAs improves reproducibility and helps protect repositories against supply-chain attacks.

This is the standard followed throughout **The Lupaxa Project**.

[↑ Back to Contents](#contents)

# Best Practices

The following recommendations have evolved from the practical use of these workflows across repositories within **The Lupaxa Project**.

Following these guidelines will help keep repository workflows consistent, maintainable and secure.

## Keep Calling Workflows Small

A repository workflow should primarily determine **when** automation runs.

The implementation should remain within the reusable workflow wherever practical.

For example, repository workflows should generally contain:

- Trigger definitions.
- Branch and path filters.
- Permissions.
- Calls to reusable workflows.

Avoid duplicating implementation across multiple repositories.

## Use the Minimum Number of Workflows

Not every repository requires every workflow.

Choose only those workflows that provide value for the technologies used by the repository.

For example:

| Repository Type | Recommended Workflows                                             |
| :-------------- | :---------------------------------------------------------------- |
| Documentation   | Markdown Linter, YAML Linter, Link Checker, MkDocs Site Publisher |
| Python Library  | Python CI, Python Linter, Python Security Scanner, Code Analysis  |
| Puppet Module   | Puppet Linter, Markdown Linter, YAML Linter                       |
| Shell Utilities | Shell Script Linter, Markdown Linter, Secrets Scanner             |

## Prefer Reusable Workflows

If several repositories perform the same automation, prefer implementing it once as a reusable workflow rather than maintaining multiple copies.

Benefits include:

- Reduced duplication.
- Easier maintenance.
- Consistent behaviour.
- Faster rollout of improvements.
- Consistent security practices.

## Introduce Validation Gradually

Many validation workflows support the `report_only` option.

When introducing a new validation workflow to an existing repository, consider enabling report-only mode initially to identify issues before enforcing them.

Once the repository is compliant, report-only mode can be disabled to enforce validation as part of Continuous Integration.

## Review Workflow Permissions

Although reusable workflows request only the permissions they require, calling workflows should avoid granting broader permissions unless genuinely necessary.

Following the principle of least privilege reduces the impact of accidental configuration errors.

## Keep Workflow References Current

Repositories should periodically update the version of the reusable workflows they consume.

Doing so ensures repositories benefit from:

- Bug fixes.
- Security improvements.
- Performance enhancements.
- New features.

## Schedule Maintenance Workflows

Repository maintenance workflows are most effective when executed on a schedule.

Examples include:

- Workflow Clean Up
- Stale Issue & Pull Request Handler
- Secrets Scanner
- Code Analysis

Running these workflows regularly helps keep repositories healthy without requiring manual intervention.

## Monitor Workflow Results

Treat workflow failures as opportunities to improve the repository.

Validation workflows are designed to identify issues early, allowing problems to be resolved before they reach production or a public release.

[↑ Back to Contents](#contents)

# Workflow Relationships

The reusable workflows complement one another and are intended to be combined where appropriate.

A typical repository might use the following workflow stack.

```text
Repository
│
├── Repository Quality
│   ├── Citation Validator
│   ├── JSON Validator
│   ├── Link Checker
│   ├── Markdown Linter
│   └── YAML Linter
│
├── Continuous Integration
│   ├── Python Continuous Integration
│   └── Python Continuous Integration (Make)
│
├── Language Analysis
│   ├── Dockerfile Linter
│   ├── Perl Linter
│   ├── PHP Linter
│   ├── Puppet Linter
│   ├── Python Code Auditor
│   ├── Python DocString Checker
│   ├── Python Linter
│   ├── Python Security Scanner
│   ├── Python Style Guide Checker
│   ├── Ruby Code Smell Detector
│   ├── Ruby Linter
│   └── Shell Script Linter
│
├── Security
│   ├── Code Analysis
│   ├── GitHub Actions Security
│   └── Secrets Scanner
│
├── Documentation
│   └── MkDocs Site Publisher
│
├── Release Management
│   ├── GitHub Release Generator
│   └── Python Dependency Updater
│
└── Repository Automation
    ├── Dependabot Manager
    ├── First-Time Contributor Greetings
    ├── Stale Issue & Pull Request Handler
    ├── Workflow Clean Up
    ├── Workflow History Purge
    ├── Workflow Notifier
    ├── Workflow Scheduler Test
    └── Workflow Summary
```

Repositories are free to adopt only those workflows that are appropriate for their requirements.

[↑ Back to Contents](#contents)

# Further Reading

For additional information about The Lupaxa Project, refer to:

- `README.md`
- `LICENSE`
- The organisation-wide documentation maintained in the `.github` repository.

Further information about GitHub Actions is available from the official GitHub documentation.

[↑ Back to Contents](#contents)

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
