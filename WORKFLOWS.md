<p align="center">
    <a href="https://github.com/the-lupaxa-project">
        <img src="https://raw.githubusercontent.com/the-lupaxa-project/org-logos/master/orgs/the-lupaxa-project/readme-logo.png" alt="The Lupaxa Project Logo" width="256" />
    </a>
</p>

<h1 align="center">The Lupaxa Project: Workflow Catalog</h1>

<h2>Overview</h2>

This document describes the shared GitHub Actions reusable workflows provided by
The Lupaxa Project via the .github repository.

It covers:

- The branch / SHA policy for reusable workflows.
- Naming conventions for reusable and local workflows.
- A catalog of CICDToolbox-based and core governance / maintenance workflows.
- Detailed, copy-paste-ready minimal usage examples for every reusable workflow.

All workflows are designed to be:

- Reusable across all Lupaxa Project repositories and organisations.
- Secure by default, with strong controls around third-party actions.
- Consistent with organisational linting, documentation, and security standards.

<h2>Branch / SHA Policy and Security Hardening</h2>

<h3>General policy</h3>

Across **ALL** Lupaxa Project repositories, we require **ALL 3<sup>rd</sup> party actions** to be pinned to a specific commit SHA.

To help enforce this, we provide:

- reusable-ensure-sha-pinned-actions.yml to check and validate **ALL** actions are pinned correctly.
- Local security-hardening workflows in consuming repos that call this reusable workflow.

These security-hardening workflows:

- Scan all workflow files under .github/workflows/.
- Fail the build if they detect uses: entries that:
  - Point to 3<sup>rd</sup> actions without @&lt;SHA&gt;, or
  - Use @main, @master, or version tags that are not allow-listed.

> [!NOTE]
> **There is one deliberate exception:**
>
> Calls to the-lupaxa-project/.github/.github/workflows/*.yml are **explicitly** allow-listed in the security-hardening configuration.

This allows all Lupaxa Project repos to reference organisation workflows using @master, for example:

```yml
  uses: the-lupaxa-project/.github/.github/workflows/reusable-markdown-lint.yml@master
```

This provides:

- Automatic updates to shared workflows via the .github repo.
- Strong SHA pinning for all other third-party actions.

<h2>Naming Conventions</h2>

<h3>Reusable workflows</h3>

- Location: the-lupaxa-project/.github/.github/workflows/
- Naming pattern: reusable-&lt;NAME&gt;.yml
- Purpose: reusable primitives and bundles that other repos call.

<h4>Examples</h4>

- reusable-codeql.yml
- reusable-markdown-lint.yml
- reusable-security-hardening.yml
- reusable-yaml-lint.yml

<h3>Consuming workflows</h3>

- Location: .github/workflows/ in a consuming repository.
- Naming pattern: &lt;NAME&gt;.yml
- Purpose: thin orchestration wrappers that:
- Define triggers (on:),
- Group jobs logically,
- Call one or more reusable-*.yml workflows via uses:.

<h4>Consumption Example</h4>

- codeql.yml
- markdown-lint.yml
- security-hardening.yml
- yaml-lint.yml

<h2>CI/CD Toolbox based Reusable Workflows</h2>

These workflows wrap tools from the [Lupaxa CI/CD Toolbox](https://github.com/lapaxa-actions-toolbox)￼GitHub organisation and all follow the same pattern:

- They call the tool’s pipeline.sh via curl | bash.
- They accept the standard inputs:
  - include_files — comma-separated paths / globs / regex (tool-specific).
  - exclude_files — comma-separated paths / globs / regex to skip.
  - report_only — if true, do not fail the build even on errors.
  - show_errors — show detailed error output.
  - show_skipped — show skipped files.
  - no_color — disable coloured output.

These map to environment variables used by CICDToolbox pipelines:

- INCLUDE_FILES
- EXCLUDE_FILES
- REPORT_ONLY
- SHOW_ERRORS
- SHOW_SKIPPED
- NO_COLOR

<h3>Catalog — CI/CD Toolbox based Workflows</h3>

| Workflow file                               | Purpose                                | Example                                      |
| :------------------------------------------ | :------------------------------------- | :------------------------------------------: |
| [reusable-awesomebot.yml][001]              | Check Markdown links.                  | [Example](#reusable-awesomebot)              |
| [reusable-bandit.yml][002]                  | Python security scanning.              | [Example](#reusable-bandit)                  |
| [reusable-hadolint.yml][003]                | Dockerfile linting.                    | [Example](#reusable-hadolint)                |
| [reusable-json-lint.yml][004]               | JSON linting.                          | [Example](#reusable-json-lint)               |
| [reusable-markdown-lint.yml][005]           | Markdown linting.                      | [Example](#reusable-markdown-lint)           |
| [reusable-perl-lint.yml][006]               | Perl linting.                          | [Example](#reusable-perl-lint)               |
| [reusable-php-lint.yml][007]                | PHP linting.                           | [Example](#reusable-php-lint)                |
| [reusable-puppet-lint.yml][008]             | Puppet manifest linting.               | [Example](#reusable-puppet-lint)             |
| [reusable-pur.yml][009]                     | Update Python requirements.            | [Example](#reusable-pur)                     |
| [reusable-pycodestyle.yml][010]             | Python style checking (PEP 8).         | [Example](#reusable-pycodestyle)             |
| [reusable-pydocstyle.yml][011]              | Python docstring style checking.       | [Example](#reusable-pydocstyle)              |
| [reusable-pylama.yml][012]                  | Python meta-linting (Pylama).          | [Example](#reusable-pylama)                  |
| [reusable-pylint.yml][013]                  | Python linting (Pylint).               | [Example](#reusable-pylint)                  |
| [reusable-reek.yml][014]                    | Ruby code smell analysis.              | [Example](#reusable-reek)                    |
| [reusable-rubocop.yml][015]                 | Ruby linting and formatting.           | [Example](#reusable-rubocop)                 |
| [reusable-shellcheck.yml][016]              | Shell script linting.                  | [Example](#reusable-shellcheck)              |
| [reusable-validate-citations-file.yml][017] | Validate CITATION.cff metadata files.  | [Example](#reusable-validate-citations-file) |
| [reusable-yaml-lint.yml][018]               | YAML linting.                          | [Example](#reusable-yaml-lint)               |

[001]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-awesomebot.yml
[002]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-bandit.yml
[003]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-hadolint.yml
[004]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-json-lint.yml
[005]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-markdown-lint.yml
[006]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-perl-lint.yml
[007]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-php-lint.yml
[008]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-puppet-lint.yml
[009]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-pur.yml
[010]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-pycodestyle.yml
[011]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-pydocstyle.yml
[012]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-pylama.yml
[013]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-pylint.yml
[014]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-reek.yml
[015]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-rubocop.yml
[016]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-shellcheck.yml
[017]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-validate-citations-file.yml
[018]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-yaml-lint.yml

<h2>Core Governance & Maintenance Workflows</h2>

These workflows are not CI/CD Toolbox based, but provide core services like dependency updates, stale handling, CodeQL analysis, and security-hardening.

<h3>Catalog — Core Workflows</h3>

| Workflow file                                      | Purpose                                                                                             | Example                                             |
| :------------------------------------------------- | :-------------------------------------------------------------------------------------------------- | :-------------------------------------------------: |
| [reusable-check-job-status.yml][101]               | Validates results of upstream jobs and fails the run if any did not succeed.                        | [Example](#reusable-check-job-status)               |
| [reusable-codeql.yml][102]                         | CodeQL security and quality scanning.                                                               | [Example](#reusable-codeql)                         |
| [reusable-dependabot.yml][103]                     | Wrapper to standardise Dependabot config across repos.                                              | [Example](#reusable-dependabot)                     |
| [reusable-ensure-sha-pinned-actions.yml][104]      | Enforce SHA-pinned actions, with an allow-list for the-lupaxa-project/.github workflows on @master. | [Example](#reusable-ensure-sha-pinned-actions)      |
| [reusable-generate-release.yml][105]               | Create GitHub Releases with changelog.                                                              | [Example](#reusable-generate-release)               |
| [reusable-greetings.yml][106]                      | Greet first-time issue and PR authors.                                                              | [Example](#reusable-greetings)                      |
| [reusable-publish-mkdocs.yml][107]                 | Generate and publish mkdocs to GitHug Pages.                                                        | [Example](#reusable-publish-mkdocs)                 |
| [reusable-purge-deprecated-workflow-runs.yml][108] | Purge obsolete / cancelled / failed / skipped workflow runs.                                        | [Example](#reusable-purge-deprecated-workflow-runs) |
| [reusable-python-make-ci.yml][109]                 | Test and Lint Python code (using Makefile).                                                         | [Example](#reusable-python-make-ci)                 |
| [reusable-slack-workflow-status.yml][110]          | Posts final workflow status to Slack via webhook.                                                   | [Example](#reusable-slack-workflow-status)          |
| [reusable-stale.yml][111]                          | Mark and close stale issues/PRs.                                                                    | [Example](#reusable-stale)                          |

[101]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-check-job-status.yml
[102]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-codeql.yml
[103]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-dependabot.yml
[104]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-ensure-sha-pinned-actions.yml
[105]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-generate-release.yml
[106]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-greetings.yml
[107]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-publish-mkdocs.yml
[108]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-purge-deprecated-workflow-runs.yml
[109]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-python-make-ci.yml
[110]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-slack-workflow-status.yml
[111]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-stale.yml

<h2>Minimal Usage Examples (Alphabetical by Workflow File)</h2>

All examples assume you are calling from another (consuming) repo in the organisation and using:

```yaml
uses: the-lupaxa-project/.github/.github/workflows/<reusable-workflow>.yml@master
```

> [!NOTE]
> This is the standard way to consume these reuable workflows.

You can adapt triggers (on:), paths, and inputs for your specific project.

<h3 id="reusable-awesomebot">Markdown Link Checking (reusable-awesomebot.yml)</h3>

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Markdown Link Check

on:
  pull_request:
    paths:
      - "**/*.md"
  push:
    branches:
      - "**"
  paths:
    - "**/*.md"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  awesomebot:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-awesomebot.yml@master
```

<h3 id="reusable-bandit">Python Security (reusable-bandit.yml)</h3>

Reusable wrapper for the `reusable-bandit.yml` to perform static security analysis on Python code, flagging common vulnerabilities and insecure patterns.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Python Security (Bandit)

on:
  pull_request:
    paths:
      - "**/*.py"
  push:
    branches:
      - "**"
    paths:
      - "**/*.py"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  bandit:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-bandit.yml@master
```

<h3 id="reusable-check-job-status">Check Job Status (reusable-check-job-status.yml)</h3>

Reusable wrapper for the `reusable-check-job-status.yml` to summarise the results of upstream jobs (success, failure, skipped, cancelled, timed_out) and fails the workflow
if any required job did not succeed, giving a single, consolidated status report.

The workflow:

- Accepts a JSON representation of the needs context.
- Uses an enhanced check-jobs.sh script to:
- List every upstream job with its result (success, failure, cancelled, skipped, or timed_out)
- Emit appropriate GitHub error/warning annotations
- Exit non-zero if any upstream job did not succeed

> [!IMPORTANT]
> This is a *job-level* uses, not under steps!

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default                                                                                          | Description                                    |
| :------------ | :------ | :------: | :----------------------------------------------------------------------------------------------- | :--------------------------------------------- |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Example with job status summary

on:
  pull_request:
    paths:
      - "**/*.py"
  push:
    branches:
      - "**"
    paths:
      - "**/*.py"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  markdown:
  uses: the-lupaxa-project/.github/.github/workflows/reusable-markdown-lint.yml@master

  yaml:
  uses: the-lupaxa-project/.github/.github/workflows/reusable-yaml-lint.yml@master

  # 🔴 IMPORTANT: this is a *job-level* uses, not under steps:
  check-status:
    name: Check Jobs Status
    needs:
      - markdown
      - yaml
    if: always()
    uses: the-lupaxa-project/.github/.github/workflows/reusable-check-job-status.yml@master
    secrets: inherit
```

> [!NOTE]
> This workflow automatically writes a GitHub Job Summary to the run’s main page, reporting the outcome of each job and providing useful GitHub metadata for context.

<h3 id="reusable-codeql">CodeQL Security and Quality (reusable-codeql.yml)</h3>

Reusable wrapper for the `reusable-codeql.yml` to standardise CodeQL security analysis workflow with a language matrix, suitable for running GitHub’s
code scanning across one or more supported languages in a consistent way.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input      | Type   | Required | Default | Description                                                                   |
| :--------- | :----- | :------- | :------ | :---------------------------------------------------------------------------- |
| languages  | string | Yes      |         | Comma-separated list of CodeQL languages e.g. "python", "python, javascript". |

> [!NOTE]
> We always append +security-and-quality to the queries passed to CodeQL.

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: CodeQL Analysis

on:
  push:
    branches-ignore:
      - "dependabot/"
    paths-ignore:
      - "**/*.md"
      - "**/*.cff"
  pull_request:
    branches:
      - "**"
  paths-ignore:
    - "**/*.md"
    - "**/*.cff"
  schedule:
    - cron: "4 3 * * 1"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  actions: read
  contents: read
  security-events: write

jobs:
  codeql:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-codeql.yml@master
    with:
      languages: "python,javascript"
```

<h3 id="reusable-dependabot">Dependabot (reusable-dependabot.yml)</h3>

Reusable wrapper for the `reusable-dependabot.yml` to centralise Dependabot configuration that can be triggered from other workflows to ensure dependency
update checks are applied consistently across all supported ecosystems.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default                                                                                          | Description                                    |
| :------------ | :------ | :------: | :----------------------------------------------------------------------------------------------- | :--------------------------------------------- |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Dependabot

on:
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  dependabot:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-dependabot.yml@master
```

<h3 id="reusable-ensure-sha-pinned-actions">Enforce SHA-Pinned Actions (reusable-ensure-sha-pinned-actions.yml)</h3>

Reusable wrapper for the `reusable-ensire-sha-pinned-action.yml` that inspects all workflow files and enforces SHA-pinned actions, allowing a controlled allow-list
(such as the-lupaxa-project/.github) while blocking branch/tag references elsewhere.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input      | Type    | Required | Default | Description                                                                                                                                                                             |
| :--------- | :------ | :------: | :------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| allow_list | string  | No       |         | Optional newline-separated list of owner[/repo] patterns that are allowed to use non-SHA refs (e.g. "the-lupaxa-project/.github"). Each line should be either "owner/" or "owner/repo". |
| dry_run    | boolean | No       | false   | If true, only report unpinned actions but do not fail the job.                                                                                                                          |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Ensure SHA-Pinned Actions

on:
  pull_request:
    paths:
      - ".github/workflows/*.yml"
      - ".github/workflows/*.yaml"
  push:
    branches:
      - "**"
    paths:
      - ".github/workflows/*.yml"
      - ".github/workflows/*.yaml"
  workflow_dispatch:

jobs:
  ensure-sha:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-ensure-sha-pinned-actions.yml@master
```

<h3 id="reusable-generate-release">Generate Release (reusable-generate-release.yml)</h3>

Reusable wrapper for the `reusable-generate-release.yml` to create generic GitHub releases that takes a tag, generates a changelog, and creates a GitHub
Release via softprops/action-gh-release, so any repo can get consistent, documented releases.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input        | Type    | Required | Default               | Description                                                                                         |
| :----------- | :------ | :------: | :-------------------- | :-------------------------------------------------------------------------------------------------- |
| tag          | string  | No       | github.ref            | Tag ref to release, e.g. "refs/tags/v1.2.3". If omitted, uses github.ref from the calling workflow. |
| release_name | string  | No       | <tag without refs/*/> | Optional explicit release name. If empty, the tag name stripped of the refs/*/ prefix is used.      |
| draft        | boolean | No       | false                 | If true, create the release as a draft.                                                             |
| prerelease   | boolean | No       | false                 | If true, mark the release as a pre-release.                                                         |

<br>
</details>

<h4>Minimal Usage Example (production Release)</h4>

```yaml
name: Generate Release

on:
  push:
    tags:
      - "v[0-9]+.[0-9]+.[0-9]+"
      - '!v[0-9].[0-9]+.[0-9]+rc[0-9]+'

permissions:
  contents: write

jobs:
  create-release:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-generate-release.yml@master
    secrets:
      github-token: ${{ secrets.GITHUB_TOKEN }}
```

<h4>Minimal Usage Example (Test Release)</h4>

```yaml
name: Generate Test Release

on:
  push:
    tags:
      - 'v[0-9].[0-9]+.[0-9]+rc[0-9]+'

permissions:
  contents: write

jobs:
  create-release:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-github-release.yml@master
    secrets:
      github-token: ${{ secrets.GITHUB_TOKEN }}
```

<h3 id="reusable-greetings">First Interaction Greetings (reusable-greetings.yml)</h3>

Reusable wrapper around actions/first-interaction to post a friendly, standardised greeting on a contributor’s first issue and/or pull request in a repository.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default                                                                                          | Description                                    |
| :------------ | :------ | :------: | :----------------------------------------------------------------------------------------------- | :--------------------------------------------- |
| issue-message | string  | No       | "Thank you for raising your first issue - all contributions to this project are welcome!"        | Message posted on a user's first issue.        |
| pr-message    | string  | No       | "Thank you for raising your first pull request - all contributions to this project are welcome!" | Message posted on a user's first pull request. |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Greetings

on:
  pull_request:
  issues:
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  issues: write
  pull-requests: write

jobs:
  greetings:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-greetings.yml@master
    secrets:
      repo-token: ${{ secrets.GITHUB_TOKEN }}
```

<h3 id="reusable-hadolint">Dockerfile Linting (reusable-hadolint.yml)</h3>

Runs the CICDToolbox hadolint pipeline to lint Dockerfiles and Docker-related build files for best practices, portability, and common mistakes.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Dockerfile Lint (Hadolint)

on:
  pull_request:
    paths:
      - "Dockerfile"
      - "**/Dockerfile*"
  push:
    branches:
      - "**"
    paths:
      - "Dockerfile"
      - "**/Dockerfile*"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  hadolint:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-hadolint.yml@master
```

<h3 id="reusable-json-lint">JSON Linting (reusable-json-lint.yml)</h3>

Invokes the CICDToolbox json-lint pipeline to validate JSON files, catching syntax errors and formatting issues in configuration and data files.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: JSON Lint

on:
  pull_request:
    paths:
      - "**/*.json"
  push:
    branches:
      - "**"
    paths:
      - "**/*.json"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  json:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-json-lint.yml@master
```

<h3 id="reusable-markdown-lint">Markdown Linting (reusable-markdown-lint.yml)</h3>

Standard Markdown linting workflow using the CICDToolbox markdown-lint pipeline and the shared .markdownlint.yml configuration for consistent prose and formatting rules.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Markdown Lint

on:
  pull_request:
    paths:
      - "**/*.md"
  push:
    branches:
      - "**"
    paths:
      - "**/*.md"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  markdown:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-markdown-lint.yml@master
```

<h3 id="reusable-perl-lint">
    Perl Linting (reusable-perl-lint.yml)
</h3>

Uses the CICDToolbox perl-lint pipeline to run linting checks over Perl scripts and modules, enforcing style and catching common issues.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Perl Lint

  on:
    pull_request:
      paths:
        - "**/*.pl"
        - "**/*.pm"
    push:
      branches:
        - "**"
      paths:
        - "**/*.pl"
        - "**/*.pm"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  perl-lint:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-perl-lint.yml@master
```

<h3 id="reusable-php-lint">PHP Linting (reusable-php-lint.yml)</h3>

Runs the CICDToolbox php-lint pipeline to syntax-check and lint PHP files, helping keep PHP projects clean and error-free.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: PHP Lint

on:
  pull_request:
    paths:
      - "**/*.php"
  push:
    branches:
      - "**"
    paths:
      - "**/*.php"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  php-lint:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-php-lint.yml@master
```

<h3 id="reusable-puppet-lint">
    Puppet Manifest Linting (reusable-puppet-lint.yaml)
</h3>

Wraps the CICDToolbox puppet-lint pipeline to validate Puppet manifests, enforcing style and best practices for configuration management code.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Puppet Lint

on:
  pull_request:
    paths:
      - "**/*.pp"
  push:
    branches:
      - "**"
    paths:
      - "**/*.pp"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  puppet-lint:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-puppet-lint.yml@master
```

<h3 id="reusable-pur">Python Requirements Updates (reusable-pur.yml)</h3>

Uses the CICDToolbox pur pipeline to update Python requirements*.txt files, ensuring dependencies are brought up to date in a controlled way before commit or release.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Python Requirements (pur)

on:
  pull_request:
    paths:
      - "**/*.py"
      - "**/requirements.txt"
  push:
    branches:
      - "**"
    paths:
      - "**/*.py"
      - "**/*.requirements.txt"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: write

jobs:
  pur:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-pur.yml@master
```

<h3 id="reusable-publish-mkdocs">Publish Mkdocs (reusable-publish-mkdocs.yml)</h3>

Reusable wrapper for the `reusable-generate-mkdocs.yml` to publish Mkdocs to GitHub Pages.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input          | Type    | Required | Default | Description                                  |
| :------------- | :------ | :------: | :------ | :------------------------------------------- |
| python-version | string  | No       | 3.13    | Any supported version of Python.             |
| use-dev-extras | string  | No       | true    | Try to install ".[dev]" from pyproject.toml. |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Docs

on:
  push:
    branches:
      - master
    paths:
      - "docs/**"
      - "mkdocs.yml"
      - "pyproject.toml"
      - ".github/workflows/docs.yml"
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  docs:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-publish-mkdocs.yml@master
    secrets: inherit
    with:
      python-version: "3.13"
```

<h3 id="reusable-purge-deprecated-workflow-runs">Purge Old Workflow Runs (reusable-purge-deprecated-workflow-runs.yml)</h3>

Reusable wrapper around otto-de/purge-deprecated-workflow-runs to clean up old, obsolete, cancelled, failed, or skipped workflow runs, keeping repository Actions history tidy.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input             | Type    | Required | Default | Description                                                                                       |
| :---------------- | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------ |
| token             | string  | No       |         | Optional token to use for the purge. If omitted, the workflow uses github.token.                  |
| remove_obsolete   | boolean | No       | true    | If true, remove workflow runs that are no longer associated with an existing workflow definition. |
| remove_cancelled  | boolean | No       | true    | If true, delete cancelled workflow runs.                                                          |
| remove_failed     | boolean | No       | true    | If true, delete failed workflow runs.                                                             |
| remove_skipped    | boolean | No       | true    | If true, delete skipped workflow runs.                                                            |
| remove_older_than | string  | No       |         | Optional multi-line spec passed to remove-older-than. Example: 30d * or 7d Some Workflow Name.    |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Purge Deprecated Workflow Runs

on:
  workflow_dispatch:
    schedule:
      - cron: "33 3 * * 1"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  actions: write

jobs:
  purge-deprecated-workflows:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-purge-deprecated-workflow-runs.yml@master
```

<h3 id="reusable-python-make-ci">Python Linting and Testing (using Make) (reusable-python-make-ci.yml)</h3>

Reusable wrapper for the `reusable-python-make-ci.yml` to Lint and Test python code using standardised Make.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input           | Type   | Required | Default                                | Description                            |
| :-------------- | :----- | :------: | :------------------------------------- | :------------------------------------- |
| python-versions | string | No       | '["3.10","3.11","3.12","3.13","3.14"]' | JSON array of Python versions.         |
| install-target  | string | No       | 'install-dev'                          | Make target for installing dev deps.   |
| ci-target       | string | No       | 'check'                                | Make target that runs lint/type/tests. |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: CI

on:
  push:
    branches:
      - "master"
  pull_request:
    branches:
      - "master"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  python-ci:
    name: Lint & Test
    uses: the-lupaxa-project/.github/.github/workflows/reusable-python-make-ci.yml@master
    secrets: inherit
```

<h3 id="reusable-pycodestyle">Python Style (reusable-pycodestyle.yml)</h3>

Runs the CICDToolbox pycodestyle pipeline to enforce PEP 8-style guidelines on Python code, catching layout and style violations.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Python Style (pycodestyle)

on:
  pull_request:
    paths:
      - "**/*.py"
  push:
    branches:
      - "**"
    paths:
      - "**/*.py"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  pycodestyle:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-pycodestyle.yml@master
```

<h3 id="reusable-pydocstyle">Python Docstrings (reusable-pydocstyle.yml)</h3>

Invokes the CICDToolbox pydocstyle pipeline to check Python docstrings against a configured convention, improving API documentation consistency.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Python Docstrings (pydocstyle)

on:
  pull_request:
    paths:
      - "**/*.py"
  push:
    branches:
      - "**"
    paths:
      - "**/*.py"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  pydocstyle:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-pydocstyle.yml@master
```

<h3 id="reusable-pylama">Python Meta-Linting (reusable-pylama.yml)</h3>

Uses the CICDToolbox pylama pipeline as a meta-linter that combines multiple Python linters into a single, unified quality gate.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Python Meta Lint (Pylama)

on:
  pull_request:
    paths:
      - "**/*.py"
  push:
    branches:
      - "**"
    paths:
    - "**/*.py"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  pylama:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-pylama.yml@master
```

<h3 id="reusable-pylint">Python Linting (reusable-pylint.yml)</h3>

Runs the CICDToolbox pylint pipeline to perform deep static analysis on Python code, enforcing coding standards and catching a wide range of potential issues.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Python Lint (Pylint)

on:
  pull_request:
    paths:
      - "**/*.py"
  push:
    branches:
      - "**"
    paths:
      - "**/*.py"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  pylint:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-pylint.yml@master
```

<h3 id="reusable-reek">Ruby Code Smells (reusable-reek.yml)</h3>

Wraps the CICDToolbox reek pipeline to detect "code smells" in Ruby code, helping highlight complexity and maintainability problems.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Ruby Code Smells (Reek)

on:
  pull_request:
    paths:
      - "**/*.rb"
  push:
    branches:
      - "**"
    paths:
      - "**/*.rb"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  reek:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-reek.yml@master
```

<h3 id="reusable-rubocop">Ruby Linting (reusable-rubocop.yml)</h3>

Runs the CICDToolbox rubocop pipeline to provide Ruby linting and auto-formatting checks according to a shared configuration.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Ruby Lint (Rubocop)

on:
  pull_request:
    paths:
      - "**/*.rb"
  push:
    branches:
      - "**"
    paths:
      - "**/*.rb"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  rubocop:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-rubocop.yml@master
```

<h3 id="reusable-shellcheck">Shell Script Linting (reusable-shellcheck.yml)</h3>

Invokes the CICDToolbox shellcheck pipeline to lint shell scripts (.sh, .bash, etc.), catching unsafe constructs and portability problems.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: ShellCheck

on:
  pull_request:
    paths:
      - "**/*.sh"
      - "**/*.bash"
      - "**/*.ksh"
      - "**/*.dash"
  push:
    branches:
      - "**"
    paths:
      - "**/*.sh"
      - "**/*.bash"
      - "**/*.ksh"
      - "**/*.dash"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  shellcheck:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-shellcheck.yml@master
```

<h3 id="reusable-slack-workflow-status">Slack Workflow Status Notifications (reusable-slack-workflow-status.yml)</h3>

Posts a Slack notification summarising workflow status using Gamesight/slack-workflow-status, with support for toggles like manual opt-out, "no-slack" markers, and tag-run skipping.

This reusable workflow intentionally contains no guardrails. Its philosophy is simple:

`If you called me, you meant it.`

All logic and guardrails around if we should send the message to slack comes from the consuming workflow.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input                  | Type    | Required | Default | Description                                                                                |
| :--------------------- | :------ | :------: | :------ | :----------------------------------------------------------------------------------------- |
| include_jobs           | string  | No       | "true"  | Controls inclusion of per-job status details. Valid values: "true", "false", "on-failure". |
| include_commit_message | boolean | No       | true    | If true, include the commit message in the Slack notification.                             |

<br>
</details>

<h4>Minimal Usage Example (Minimum Guardrails)</h4>

Minimum Guardrail List:

- Ensure Slack is globally enabled
- Ensure webhook secret exists
- Skip notify on PRs from forks

```yaml
name: Example CI with Slack

on:
  push:
    branches:
      - "**"
  pull_request:
  workflow_dispatch:
    inputs:
      enable_slack:
        description: "Send Slack notification for this manual run?"
        required: false
        type: boolean
        default: true

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  SLACK_ENABLED: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Do build / tests
        run: echo "Build goes here"

  slack-workflow-status:
    name: Slack Workflow Status
    needs:
      - build

  if: >
    always() &&                          # Always evaluate this block, even if earlier jobs fail.
    env.SLACK_ENABLED == true &&         # Global toggle set by the repo author.
    secrets.SLACK_WEBHOOK_URL != '' &&   # Skip if webhook isn't configured at repo/org level.

    # --- Prevent Slack for pull requests coming from forks ---
    # Forks should NEVER have access to internal Slack systems.
    (
      github.event_name != 'pull_request' ||
      github.event.pull_request.head.repo.full_name == github.repository
    ) &&

    uses: the-lupaxa-project/.github/.github/workflows/reusable-slack-workflow-status.yml@master
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

<h4>Minimal Usage Example (Extended Guardrails)</h4>

Guardrail List:

- Ensure Slack is globally enabled
- Ensure webhook secret exists
- Skip notify on PRs from forks
- Skip notify when commit message contains “[no-slack]”
- Skip notify when PR title contains “[no-slack]”
- Skip notify when manually dispatched AND manually disabled
- Skip notify for tag builds

```yaml
name: Example CI with Slack

on:
  push:
    branches:
      - "**"
  pull_request:
  workflow_dispatch:
    inputs:
      enable_slack:
        description: "Send Slack notification for this manual run?"
        required: false
        type: boolean
        default: true

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  SLACK_ENABLED: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Do build / tests
        run: echo "Build goes here"

  slack-workflow-status:
    name: Slack Workflow Status
    needs:
      - build

  if: >
    always() &&                          # Always evaluate this block, even if earlier jobs fail.
    env.SLACK_ENABLED == true &&         # Global toggle set by the repo author.
    secrets.SLACK_WEBHOOK_URL != '' &&   # Skip if webhook isn't configured at repo/org level.

    # --- Prevent Slack for pull requests coming from forks ---
    # Forks should NEVER have access to internal Slack systems.
    (
      github.event_name != 'pull_request' ||
      github.event.pull_request.head.repo.full_name == github.repository
    ) &&

    # --- Allow manual workflow_dispatch to turn Slack on/off ---
    # If this is a manually-triggered run, only notify Slack if the user opted in.
    (
      github.event_name != 'workflow_dispatch' ||
      github.event.inputs.enable_slack == true
    ) &&

    # --- Skip Slack notifications when commit message contains “[no-slack]” ---
    # Developers can prevent Slack noise on minor commits.
    (
      github.event_name != 'push' ||
      !contains(github.event.head_commit.message, '[no-slack]')
    ) &&

    # --- Skip Slack on PRs when title contains “[no-slack]” ---
    (
      github.event_name != 'pull_request' ||
      !contains(github.event.pull_request.title, '[no-slack]')
    ) &&

    # --- Skip tag builds (commonly used for release tagging) ---
    (
      github.ref == '' ||
      !startsWith(github.ref, 'refs/tags/')
    )

    uses: the-lupaxa-project/.github/.github/workflows/reusable-slack-workflow-status.yml@master
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

<h3 id="reusable-stale">Stale Issues and PRs (reusable-stale.yml)</h3>

Reusable wrapper around actions/stale to automatically mark and optionally close stale issues and pull requests, using organisation-standard labels and timeouts.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input                   | Type    | Required | Default                                                                                                                                  | Description                                                       |
| :---------------------- | :------ | :------: | :--------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------- |
| stale-issue-message     | string  | No       | "This issue is stale because it has been open 30 days with no activity. Remove stale label or comment or this will be closed in 5 days." | Message when an issue becomes stale.                              |
| close-issue-message     | string  | No       | "This issue was closed because it has been stalled for 5 days with no activity."                                                         | Message when an issue is closed as stale.                         |
| days-before-issue-stale | number  | No       | 30                                                                                                                                       | Number of days before an issue is marked stale.                   |
| days-before-issue-close | number  | No       | 5                                                                                                                                        | Number of days after staleness before an issue is closed.         |
| stale-issue-label       | string  | No       | "state: stale"                                                                                                                           | Label applied to stale issues.                                    |
| close-issue-label       | string  | No       | "resolution: closed"                                                                                                                     | Label applied to issues closed due to staleness.                  |
| exempt-issue-labels     | string  | No       | "state: blocked,state: keep"                                                                                                             | Comma-separated list of labels that exempt issues from staleness. |
| stale-pr-message        | boolean | No       | "This PR is stale because it has been open 45 days with no activity. Remove stale label or comment or this will be closed in 10 days."   | Message when a PR becomes stale.                                  |
| close-pr-message        | boolean | No       | "This PR was closed because it has been stalled for 10 days with no activity."                                                           | Message when a PR is closed as stale.                             |
| days-before-pr-stale    | number  | No       | 45                                                                                                                                       | Number of days before a PR is marked stale.                       |
| days-before-pr-close    | number  | No       | 10                                                                                                                                       | Number of days after staleness before a PR is closed.             |
| stale-issue-label       | boolean | No       | "state: stale"                                                                                                                           | Label applied to stale PRs.                                       |
| close-issue-label       | boolean | No       | "resolution: closed"                                                                                                                     | Label applied to PRs closed due to staleness.                     |
| exempt-issue-labels     | boolean | No       | "state: blocked,state: keep"                                                                                                             | Comma-separated list of labels that exempt PRs from staleness.    |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Stale Issue & PR Handler

on:
  schedule:
    - cron: "35 5 * * *"
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: write
  issues: write
  pull-requests: write

jobs:
  stale:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-stale.yml@master
```

<h3 id="reusable-validate-citations-file">CITATION File Validation (reusable-validate-citations-file.yml)</h3>

Runs the CICDToolbox validate-citations-file pipeline to validate CITATION.cff files, ensuring project citation metadata is present and correctly structured.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Citation File Validation

on:
  pull_request:
    paths:
      - "CITATION.cff"
  push:
    branches:
      - "**"
    paths:
      - "CITATION.cff"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  citations:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-validate-citations-file.yml@master
```

<h3 id="reusable-yaml-lint">YAML Linting (reusable-yaml-lint.yml)</h3>

Standard YAML linting workflow using the CICDToolbox yaml-lint pipeline and the shared .yamllint.yml configuration, enforcing consistent YAML style and spacing.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input         | Type    | Required | Default | Description                                                                                        |
| :------------ | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------- |
| include_files | string  | No       |         | Comma-separated list of regex patterns to include. Empty = auto-discover files.                    |
| exclude_files | string  | No       |         | Comma-separated list of regex patterns to exclude from scanning.                                   |
| report_only   | boolean | No       | false   | If true, never fail the job – still report issues but exit with status 0.                          |
| show_errors   | boolean | No       | true    | If true, print per-file error details in the output.                                               |
| show_skipped  | boolean | No       | false   | If true, list files that were discovered but skipped (e.g. excluded by patterns).                  |
| no_color      | boolean | No       | false   | If true, disable ANSI colours in the pipeline output (useful for plain log parsers or CI systems). |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: YAML Lint

on:
  pull_request:
    paths:
      - "**/*.yml"
      - "**/*.yaml"
  push:
    branches:
      - "**"
    paths:
      - "**/*.yml"
      - "**/*.yaml"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  yaml:
    uses: the-lupaxa-project/.github/.github/workflows/reusable-yaml-lint.yml@master
```

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
