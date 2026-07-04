<p align="center">
    <a href="https://github.com/the-lupaxa-project">
        <img src="https://raw.githubusercontent.com/the-lupaxa-project/org-logos/master/orgs/the-lupaxa-project/readme-logo.png" alt="The Lupaxa Project Logo" width="256" />
    </a>
</p>

<h1 align="center">The Lupaxa Project: Reusable Workflows</h1>

This document provides the reference guide for every reusable GitHub Actions workflow maintained by **The Lupaxa Project**.

These workflows form the shared automation platform used throughout repositories across every Lupaxa GitHub organisation. By centralising common automation
into reusable workflows, repositories benefit from consistent behaviour, simplified maintenance, reduced duplication, and a consistent security model.

The workflows are designed to be modular, reusable, configurable and easy to adopt, allowing individual repositories to remain small while still benefiting
from a comprehensive CI/CD platform.

# Contents

- [Workflow Catalogue](#workflow-catalogue)
- [Workflow Architecture](#workflow-architecture)
- [Using Reusable Workflows](#using-reusable-workflows)
- [Design Principles](#design-principles)
- [Standard Validation Interface](#standard-validation-interface)
- [Repository Quality](#repository-quality)
- [Language Quality](#language-quality)
- [Security](#security)
- [Documentation](#documentation)
- [Release Management](#release-management)
- [Repository Automation](#repository-automation)
- [Frequently Asked Questions](#frequently-asked-questions)
- [Best Practices](#best-practices)
- [Workflow Relationships](#workflow-relationships)
- [Further Reading](#further-reading)
- [Contributing](#contributing)

# Workflow Catalogue

The following table provides a quick overview of every reusable workflow available in this repository.

| Workflow                                                                    | Category              | Level        | Purpose                                          |
| :-------------------------------------------------------------------------- | :-------------------- | :----------: | :----------------------------------------------- |
| [Citation Validator](#citation-validator)                                   | Repository Quality    | Basic        | Validate `CITATION.cff` files.                   |
| [Code Analysis](#code-analysis)                                             | Security              | Intermediate | Perform GitHub CodeQL analysis.                  |
| [Dependabot Manager](#dependabot-manager)                                   | Repository Automation | Intermediate | Automate Dependabot Pull Requests.               |
| [Dockerfile Linter](#dockerfile-linter)                                     | Language Quality      | Basic        | Validate Dockerfiles.                            |
| [First-Time Contributor Greetings](#first-time-contributor-greetings)       | Repository Automation | Basic        | Welcome first-time contributors.                 |
| [GitHub Actions Security](#github-actions-security)                         | Security              | Intermediate | Validate GitHub Actions security.                |
| [GitHub Release Generator](#github-release-generator)                       | Release Management    | Advanced     | Create GitHub Releases.                          |
| [JSON Validator](#json-validator)                                           | Repository Quality    | Basic        | Validate JSON documents.                         |
| [Link Checker](#link-checker)                                               | Repository Quality    | Intermediate | Validate hyperlinks in documentation.            |
| [Markdown Linter](#markdown-linter)                                         | Repository Quality    | Basic        | Validate Markdown documentation.                 |
| [MkDocs Site Publisher](#mkdocs-site-publisher)                             | Documentation         | Advanced     | Build and publish MkDocs documentation.          |
| [Perl Linter](#perl-linter)                                                 | Language Quality      | Basic        | Lint Perl source code.                           |
| [PHP Linter](#php-linter)                                                   | Language Quality      | Basic        | Lint PHP source code.                            |
| [Puppet Linter](#puppet-linter)                                             | Language Quality      | Basic        | Validate Puppet manifests.                       |
| [Python Code Auditor](#python-code-auditor)                                 | Language Quality      | Basic        | Perform advanced Python static analysis.         |
| [Python Continuous Integration](#python-continuous-integration)             | Language Quality      | Advanced     | Complete Python Continuous Integration pipeline. |
| [Python Continuous Integration (Make)](#python-continuous-integration-make) | Language Quality      | Intermediate | Run Python CI using repository Make targets.     |
| [Python Dependency Updater](#python-dependency-updater)                     | Release Management    | Basic        | Detect outdated Python dependencies.             |
| [Python DocString Checker](#python-docstring-checker)                       | Language Quality      | Basic        | Validate Python docstrings.                      |
| [Python Linter](#python-linter)                                             | Language Quality      | Basic        | Lint Python source code.                         |
| [Python Security Scanner](#python-security-scanner)                         | Language Quality      | Basic        | Scan Python projects for security issues.        |
| [Python Style Guide Checker](#python-style-guide-checker)                   | Language Quality      | Basic        | Validate Python coding standards.                |
| [Ruby Code Smell Detector](#ruby-code-smell-detector)                       | Language Quality      | Basic        | Detect Ruby code smells.                         |
| [Ruby Linter](#ruby-linter)                                                 | Language Quality      | Basic        | Lint Ruby source code.                           |
| [Secrets Scanner](#secrets-scanner)                                         | Security              | Intermediate | Detect exposed credentials and secrets.          |
| [Shell Script Linter](#shell-script-linter)                                 | Language Quality      | Basic        | Validate shell scripts.                          |
| [Stale Issue & Pull Request Handler](#stale-issue--pull-request-handler)    | Repository Automation | Intermediate | Manage inactive Issues and Pull Requests.        |
| [Workflow Clean Up](#workflow-clean-up)                                     | Repository Automation | Advanced     | Clean workflow runs and workflow artifacts.      |
| [Workflow Notifier](#workflow-notifier)                                     | Repository Automation | Advanced     | Send Slack workflow notifications.               |
| [Workflow Scheduler Test](#workflow-scheduler-test)                         | Repository Automation | Basic        | Verify scheduled workflow execution.             |
| [Workflow Summary](#workflow-summary)                                       | Repository Automation | Intermediate | Generate workflow execution summaries.           |
| [YAML Linter](#yaml-linter)                                                 | Repository Quality    | Basic        | Validate YAML configuration files.               |

#### Level Guide

| Level            | Description                                                                                                    |
| :--------------- | :------------------------------------------------------------------------------------------------------------- |
| **Basic**        | Thin wrapper around a shared validation pipeline with minimal configuration.                                   |
| **Intermediate** | Performs orchestration, exposes multiple configuration options, or integrates with one or more GitHub Actions. |
| **Advanced**     | Feature-rich automation with extensive configuration, multiple stages, or complex repository management tasks. |

[↑ Back to Contents](#contents)

# Workflow Architecture

All workflows within this repository are implemented using GitHub's `workflow_call` feature.

Instead of embedding large amounts of workflow logic into every repository, individual repositories contain only lightweight workflows responsible for
deciding **when** automation should execute.

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

Workflows expose consistent interfaces wherever practical, making it easier to move between different workflows without learning a new configuration model
each time.

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

Unless stated this is the common set of inputs that the reuable workflows will accept.

| Input           | Description                                   |
| :-------------- | :-------------------------------------------- |
| `include_files` | Files or regular expressions to include.      |
| `exclude_files` | Files or regular expressions to exclude.      |
| `report_only`   | Report problems without failing the workflow. |
| `show_errors`   | Display detailed validation errors.           |
| `show_skipped`  | Display skipped files.                        |
| `no_color`      | Disable ANSI coloured output.                 |

Unless documented otherwise, validation workflows:

- require only `contents: read` permission;
- require no secrets;
- produce no workflow outputs;
- execute a shared **CICDToolbox** validation pipeline.

[↑ Back to Contents](#contents)

# Repository Quality

Repository Quality workflows validate repository metadata, documentation and configuration files.

These workflows are typically executed as part of Continuous Integration and help ensure repositories remain consistent, well-structured and compliant with
project standards.

| Workflow                                  | Purpose                               |
| :---------------------------------------- | :------------------------------------ |
| [Citation Validator](#citation-validator) | Validate citation metadata.           |
| [JSON Validator](#json-validator)         | Validate JSON documents.              |
| [Link Checker](#link-checker)             | Validate hyperlinks in documentation. |
| [Markdown Linter](#markdown-linter)       | Validate Markdown documentation.      |
| [YAML Linter](#yaml-linter)               | Validate YAML configuration.          |

## Citation Validator

Validates `CITATION.cff` and related citation metadata to ensure it conforms to the expected format and standards before changes are merged. This workflow
helps maintain accurate, consistent and well-formed citation metadata throughout a project, making it particularly useful for documentation repositories and
projects that rely on structured citation files.

### Inputs

[Common Inputs](#common-inputs)

### Example

```yaml
name: Citation Validator

on:
  pull_request:
    paths:
      - "CITATION.cff"
  push:
    branches:
      - "**"
    paths:
      - "CITATION.cff"

permissions:
  contents: read

jobs:
  citations:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-citation-validator.yml@master
```

## JSON Validator

Validates JSON files throughout a repository to ensure they are syntactically correct and conform to the JSON specification before changes are merged. By
detecting malformed or invalid JSON early in the development process, this workflow helps prevent configuration errors, deployment failures and application
issues caused by incorrectly formatted JSON documents.

### Inputs

[Common Inputs](#common-inputs)

### Example

```yaml
ame: JSON Linter

on:
  pull_request:
    paths:
      - "**/*.json"
  push:
    branches:
      - "**"
    paths:
      - "**/*.json"

permissions:
  contents: read

jobs:
  json:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-json-validator.yml@master
```

## Link Checker

Sscans repository files for hyperlinks and verifies that they resolve correctly, helping to identify broken, redirected or otherwise invalid links before
changes are merged. By automatically validating links across documentation and source files, this workflow helps maintain accurate, reliable documentation
and improves the overall quality and user experience of a project.

Unlike the other Repository Quality workflows, Link Checker also supports additional configuration for AwesomeBot.

### Inputs

[Common Inputs](#common-inputs)

### Additional Inputs

| Input       | Description                                   |
| :---------- | :-------------------------------------------- |
| `flags`     | Additional AwesomeBot command-line arguments. |
| `whitelist` | Comma-separated list of URLs to ignore.       |

### Example

```yaml
name: Link Checker

on:
  pull_request:
    paths:
      - "**/*.md"
  push:
    paths:
      - "**/*.md"

permissions:
  contents: read

jobs:
  links:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-link-checker.yml@master
```

## Markdown Linter

Analyses Markdown files to identify formatting inconsistencies, style violations and documentation issues before they are merged into the repository. By
enforcing consistent Markdown standards across documentation, this workflow helps improve readability, maintainability and the overall quality of project
documentation.

### Inputs

[Common Inputs](#common-inputs)

### Example

```yaml
jobs:
  markdown:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-markdown-linter.yml@master
```

## YAML Linter

Validates YAML configuration files and detects syntax errors, formatting inconsistencies and deviations from established YAML best practices before changes
are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable diagnostic
output to suit different development and CI workflows. By validating YAML configuration files early in the development process, this workflow helps prevent
configuration errors, deployment failures and automation issues while promoting consistent, maintainable YAML across repositories.

### Pipeline

CICDToolbox YAML Linter

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  yaml:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-yaml-linter.yml@master
```

[↑ Back to Contents](#contents)

# Language Quality

Language Quality workflows perform language-specific linting, static analysis and continuous integration.

Most language validation workflows use the **Standard Validation Interface**, allowing repositories to configure different language validators in exactly
the same way.

| Workflow                   | Pipeline    |
| :------------------------- | :---------- |
| Dockerfile Linter          | Hadolint    |
| Perl Linter                | Perl Critic |
| PHP Linter                 | PHP Lint    |
| Puppet Linter              | Puppet Lint |
| Python Linter              | pylint      |
| Python Style Guide Checker | pycodestyle |
| Python DocString Checker   | pydocstyle  |
| Python Code Auditor        | pylama      |
| Python Security Scanner    | Bandit      |
| Ruby Linter                | RuboCop     |
| Ruby Code Smell Detector   | Reek        |
| Shell Script Linter        | ShellCheck  |

All of the above workflows:

- use the Standard Validation Interface;
- require only `contents: read`;
- require no secrets;
- execute a shared CICDToolbox validation pipeline.

## Python Continuous Integration

Provides a complete Continuous Integration pipeline for Python projects.

Unlike the validation workflows, Python Continuous Integration performs a full project build, static analysis and automated test execution.

### Features

- Matrix testing across multiple Python versions.
- Automatic dependency installation.
- Ruff linting.
- mypy type checking.
- pytest execution.
- Configurable project paths.

### Inputs

| Input             | Description                                              |
| :---------------- | :------------------------------------------------------- |
| `python_versions` | Python versions to test.                                 |
| `paths`           | Comma-separated list of project directories to validate. |

### Additional Permissions

None.

### Required Secrets

None.

### Example

```yaml
jobs:
  python-ci:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-ci.yml@master
    with:
      paths: src,tests
```

### Notes

Project dependencies are installed automatically before running Ruff, mypy and pytest. If a `tests/` directory is present, the workflow automatically executes
the project's test suite.

## Python Continuous Integration (Make)

Runs Continuous Integration using the repository's existing Makefile.

This workflow is intended for repositories that standardise their build process through Make targets.

### Features

- Matrix testing.
- Configurable Make targets.
- Supports custom project layouts.
- Minimal repository configuration.

### Inputs

| Input             | Description                                      |
| :---------------- | :----------------------------------------------- |
| `python_versions` | Python versions to test.                         |
| `install_target`  | Make target used to install dependencies.        |
| `ci_target`       | Make target executed for Continuous Integration. |

### Example

```yaml
jobs:
  ci:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-makefile-ci.yml@master
```

### Notes

Rather than implementing the CI logic directly, this workflow delegates execution to the repository's Makefile, allowing projects to define their own quality
pipeline while maintaining a consistent entry point.

## Python Linter

Runs the shared Python linting pipeline.

### Pipeline

CICDToolbox Pylint

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  pylint:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-linter.yml@master
```

## Python Style Guide Checker

Checks Python source code against recognised style guidelines.

### Pipeline

CICDToolbox pycodestyle

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  style:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-style-guide-checker.yml@master
```

## Python DocString Checker

Validates Python docstrings.

### Pipeline

CICDToolbox pydocstyle

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  docstrings:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-docstring-checker.yml@master
```

## Python Code Auditor

Performs comprehensive static analysis of Python projects.

### Pipeline

CICDToolbox Pylama

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  audit:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-code-auditor.yml@master
```

## Python Security Scanner

Performs security analysis using Bandit.

### Pipeline

CICDToolbox Bandit

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  security:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-security-scanner.yml@master
```

## Python Dependency Updater

Checks Python dependencies for available updates.

### Pipeline

CICDToolbox PUR

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  dependencies:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-dependency-updater.yml@master
```

## PHP Linter

Performs static analysis of PHP source code.

### Pipeline

CICDToolbox PHP Lint

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  php:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-php-linter.yml@master
```

## Perl Linter

Performs static analysis of Perl source code.

### Pipeline

CICDToolbox Perl Critic

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  perl:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-perl-linter.yml@master
```

## Puppet Linter

Validates Puppet manifests.

### Pipeline

CICDToolbox Puppet Lint

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  puppet:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-puppet-linter.yml@master
```

## Ruby Linter

Runs RuboCop against Ruby projects.

### Pipeline

CICDToolbox RuboCop

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  ruby:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-ruby-linter.yml@master
```

## Ruby Code Smell Detector

Analyses Ruby projects for design issues and code smells.

### Pipeline

CICDToolbox Reek

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  reek:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-ruby-code-smell-detector.yml@master
```

## Shell Script Linter

Runs ShellCheck against shell scripts.

### Pipeline

CICDToolbox ShellCheck

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  shellcheck:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-shell-script-linter.yml@master
```

## Dockerfile Linter

Validates Dockerfiles using Hadolint.

### Pipeline

CICDToolbox Hadolint

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  dockerfile:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-dockerfile-linter.yml@master
```

[↑ Back to Contents](#contents)

# Security

Security workflows help identify vulnerabilities in source code, repository configuration and GitHub Actions workflows.

These workflows are intended to complement the language-specific validation workflows by focusing on security posture rather than coding style or correctness.

| Workflow                | Purpose                                 |
| :---------------------- | :-------------------------------------- |
| Code Analysis           | Perform GitHub CodeQL analysis.         |
| GitHub Actions Security | Validate GitHub Actions security.       |
| Secrets Scanner         | Detect exposed secrets and credentials. |

## Code Analysis

Performs static application security testing using **GitHub CodeQL**.

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

### Required Secrets

None.

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

Checks GitHub Actions workflows for common security issues.

The workflow validates that third-party actions are pinned to immutable commit SHAs and verifies that workflow references comply with the project's security
policy.

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

### Required Secrets

None.

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

Scans repositories for exposed credentials using **TruffleHog**.

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

### Required Secrets

None.

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

| Workflow              | Purpose                                          |
| :-------------------- | :----------------------------------------------- |
| MkDocs Site Publisher | Build and publish documentation to GitHub Pages. |

## MkDocs Site Publisher

Builds and publishes MkDocs documentation.

This workflow provides the standard documentation publishing pipeline used throughout **The Lupaxa Project**.

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

### Required Secrets

None.

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

| Workflow                  | Purpose                              |
| :------------------------ | :----------------------------------- |
| GitHub Release Generator  | Publish GitHub Releases.             |
| Python Dependency Updater | Detect outdated Python dependencies. |

## GitHub Release Generator

Creates GitHub Releases from repository tags.

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

Checks Python projects for outdated dependencies.

This workflow uses the **Standard Validation Interface** and executes the shared **CICDToolbox PUR** pipeline.

### Pipeline

CICDToolbox PUR

### Interface

Standard Validation Interface

### Example

```yaml
jobs:
  dependencies:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-dependency-updater.yml@master
```

[↑ Back to Contents](#contents)

# Repository Automation

Repository Automation workflows simplify the day-to-day management of GitHub repositories by automating common maintenance tasks.

Unlike validation workflows, these workflows interact directly with repositories, Issues, Pull Requests, workflow runs and external notification systems.

| Workflow                           | Purpose                                    |
| :--------------------------------- | :----------------------------------------- |
| Dependabot Manager                 | Automate Dependabot Pull Request handling. |
| First-Time Contributor Greetings   | Welcome first-time contributors.           |
| Stale Issue & Pull Request Handler | Manage inactive Issues and Pull Requests.  |
| Workflow Summary                   | Generate workflow summaries.               |
| Workflow Notifier                  | Send Slack workflow notifications.         |
| Workflow Clean Up                  | Maintain workflow history and artifacts.   |
| Workflow Scheduler Test            | Verify scheduled workflow execution.       |

## Dependabot Manager

Automates the handling of Pull Requests opened by **Dependabot**.

Rather than manually reviewing routine dependency updates, this workflow can automatically approve, label and merge eligible Pull Requests according to the
configured policy.

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

### Required Secrets

None.

### Example

```yaml
jobs:
  dependabot:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-dependabot-manager.yml@master
```

### Notes

This workflow only executes when the triggering actor is `dependabot[bot]`.

## First-Time Contributor Greetings

Welcomes users making their first contribution to a repository.

The workflow automatically posts friendly welcome messages when contributors open their first Issue or Pull Request.

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

Automatically manages inactive Issues and Pull Requests.

Repositories can define independent policies for Issues and Pull Requests, allowing stale discussions to be identified, labelled and eventually closed if no
further activity occurs.

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

### Optional Secrets

```text
slack_webhook_url
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

Generates a Markdown summary of the current workflow execution.

The generated report provides a concise overview of the workflow run and may optionally be uploaded as a workflow artifact.

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

Sends Slack notifications summarising workflow execution.

This workflow provides a consistent notification mechanism across **The Lupaxa Project**, allowing repositories to publish workflow results without
implementing their own notification logic.

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

Maintains GitHub Actions workflow history and workflow artifacts.

This is the most comprehensive reusable workflow within the repository and provides fine-grained control over workflow retention, artifact cleanup and
historical workflow management.

It is intended for scheduled execution to keep repositories tidy while preserving important workflow history.

### Features

- Workflow run retention policies.
- Artifact cleanup.
- Age-based cleanup.
- Workflow-specific retention.
- Branch preservation.
- Representative run preservation.
- Dry-run mode.
- Detailed Markdown reporting.
- Artifact upload.
- API throttling controls.
- Configurable verbosity.

### Configuration

Workflow Clean Up exposes a comprehensive configuration interface covering:

- Workflow retention periods.
- Artifact retention periods.
- Branch preservation rules.
- Protected workflow selection.
- Representative run preservation.
- Status-specific cleanup rules.
- Dry-run execution.
- Report generation.
- Progress reporting.
- GitHub API request throttling.

Rather than documenting every individual option here, repository maintainers should refer to the workflow source for the complete list of available inputs.

### Additional Permissions

```yaml
actions: write
```

### Required Secrets

None.

### Example

```yaml
jobs:
  cleanup:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-clean-up.yml@master
```

### Notes

Unlike most workflows in this repository, Workflow Clean Up executes a dedicated Lupaxa management utility rather than a shared validation pipeline.

It has been designed to support repositories ranging from small personal projects through to organisations containing hundreds of repositories and many
thousands of workflow runs.

## Workflow Scheduler Test

Provides a lightweight workflow for verifying scheduled GitHub Actions execution.

This workflow is primarily intended for testing and troubleshooting scheduled workflows.

### Features

- Displays workflow metadata.
- Displays runner information.
- Displays execution time.
- Displays GitHub context.
- Lightweight diagnostic output.

### Inputs

None.

### Additional Permissions

None.

### Required Secrets

None.

### Example

```yaml
jobs:
  scheduler-test:
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-scheduler-test.yml@master
```

[↑ Back to Contents](#contents)

# Frequently Asked Questions

## Which workflow should I use?

The table below provides a quick reference for selecting the appropriate workflow.

| I want to...                             | Workflow                             |
| :--------------------------------------- | :----------------------------------- |
| Validate repository metadata             | Citation Validator                   |
| Validate JSON files                      | JSON Validator                       |
| Validate Markdown documentation          | Markdown Linter                      |
| Validate YAML configuration              | YAML Linter                          |
| Validate hyperlinks                      | Link Checker                         |
| Lint Python projects                     | Python Linter                        |
| Run a complete Python CI pipeline        | Python Continuous Integration        |
| Run Python CI using Make                 | Python Continuous Integration (Make) |
| Scan Python projects for security issues | Python Security Scanner              |
| Detect outdated Python dependencies      | Python Dependency Updater            |
| Lint PHP, Perl, Puppet or Ruby projects  | Language Quality workflows           |
| Scan for repository secrets              | Secrets Scanner                      |
| Perform CodeQL analysis                  | Code Analysis                        |
| Publish documentation                    | MkDocs Site Publisher                |
| Generate GitHub Releases                 | GitHub Release Generator             |
| Welcome first-time contributors          | First-Time Contributor Greetings     |
| Manage Dependabot Pull Requests          | Dependabot Manager                   |
| Manage stale Issues and Pull Requests    | Stale Issue & Pull Request Handler   |
| Generate workflow summaries              | Workflow Summary                     |
| Send Slack notifications                 | Workflow Notifier                    |
| Clean workflow history                   | Workflow Clean Up                    |
| Test scheduled workflows                 | Workflow Scheduler Test              |

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
│   ├── Markdown Linter
│   ├── YAML Linter
│   └── Link Checker
│
├── Language Quality
│   └── Python Continuous Integration
│
├── Security
│   ├── Code Analysis
│   └── Secrets Scanner
│
├── Documentation
│   └── MkDocs Site Publisher
│
└── Repository Automation
    ├── Workflow Summary
    └── Workflow Notifier
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

# Contributing

Improvements to reusable workflows are always welcome.

When contributing:

- Maintain backwards compatibility wherever practical.
- Keep workflow interfaces consistent with existing conventions.
- Request the minimum permissions required.
- Pin third-party GitHub Actions to immutable commit SHAs.
- Update this document whenever workflow behaviour changes.

Following these principles helps ensure the workflow platform remains stable and predictable for every repository that consumes it.

<h1></h1>

<p align="center">
    <strong>
        &copy; The Lupaxa Project.
    </strong>
    <br />
    <em>
        Where exploration meets precision.<br />
        Where the untamed meets the engineered.
    </em>
</p>
