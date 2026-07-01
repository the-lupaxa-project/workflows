<p align="center">
    <a href="https://github.com/the-lupaxa-project">
        <img src="https://raw.githubusercontent.com/the-lupaxa-project/org-logos/master/orgs/the-lupaxa-project/readme-logo.png" alt="The Lupaxa Project Logo" width="256" />
    </a>
</p>

<h1 align="center">The Lupaxa Project: Workflow Catalog</h1>

| Workflow file                                           | Purpose                                                                                          | Example                                                   |
| :------------------------------------------------------ | :----------------------------------------------------------------------------------------------- | :-------------------------------------------------------: |
| [reusable-citation-validator.yml][001]                  | Validates repository citation files against the required format and standards.                   | [Example](#reusable-citation-validator)                   |
| [reusable-code-analysis.yml][002]                       | Performs GitHub CodeQL security and quality analysis on supported languages.                     | [Example](#reusable-code-analysis)                        |
| [reusable-dependabot-manager.yml][003]                  | Automates the review, approval and management of Dependabot pull requests.                       | [Example](#reusable-dependabot-manager)                   |
| [reusable-dockerfile-linter.yml][004]                   | Lints Dockerfiles to identify syntax errors, best practice violations and potential issues.      | [Example](#reusable-dockerfile-linter)                    |
| [reusable-first-time-contributor-greetings.yml][005]    | Welcomes first-time issue authors and pull request contributors.                                 | [Example](#reusable-first-time-contributor-greetings)     |
| [reusable-github-actions-security.yml][006]             | Verifies that GitHub Actions are securely pinned to immutable commit SHAs.                       | [Example](#reusable-github-actions-security)              |
| [reusable-github-release-generator.yml][007]            | Automatically generates and publishes GitHub Releases with a generated changelog.                | [Example](#reusable-github-release-generator)             |
| [reusable-json-validator.yml][008]                      | Validates JSON files to ensure they are syntactically correct and well-formed.                   | [Example](#reusable-json-validator)                       |
| [reusable-link-checker.yml][009]                        | Checks documentation and source files for broken, unreachable and invalid hyperlinks.            | [Example](#reusable-link-checker)                         |
| [reusable-markdown-linter.yml][010]                     | Lints Markdown files to enforce consistent formatting and documentation standards.               | [Example](#reusable-markdown-linter)                      |
| [reusable-mkdocs-site-publisher.yml][011]               | Builds MkDocs documentation sites and publishes them to GitHub Pages..                           | [Example](#reusable-mkdocs-site-publisher)                |
| [reusable-perl-linter.yml][012]                         | Lints Perl source files to identify syntax errors, coding issues and style violations.           | [Example](#reusable-perl-linter)                          |
| [reusable-php-linter.yml][013]                          | Lints PHP source files to identify syntax errors, coding issues and style violations.            | [Example](#reusable-php-linter)                           |
| [reusable-puppet-linter.yml][014]                       | Lints Puppet manifests to identify syntax errors, coding issues and style violations.            | [Example](#reusable-puppet-linter)                        |
| [reusable-python-ci.yml][015]                           | Runs a complete Python quality assurance pipeline across multiple Python versions.               | [Example](#reusable-python-ci)                            |
| [reusable-python-code-auditor.yml][016]                 | Audits Python source code for quality issues using multiple static analysis tools.               | [Example](#reusable-python-code-auditor)                  |
| [reusable-python-dependency-updater.yml][017]           | Checks Python dependencies for available updates and reports outdated packages.                  | [Example](#reusable-python-dependency-updater)            |
| [reusable-python-docstring-checker.yml][018]            | Checks Python docstrings for completeness and compliance with documentation standards.           | [Example](#reusable-python-docstring-checker)             |
| [reusable-python-linter.yml][019]                       | Lints Python source code to identify errors, code smells and maintainability issues.             | [Example](#reusable-python-linter)                        |
| [reusable-python-makefile-ci][020]                      | Runs Python project CI through configurable Make targets across multiple Python versions.        | [Example](#reusable-python-makefile-ci)                   |
| [reusable-python-security-scanner.yml][021]             | Scans Python source code for common security vulnerabilities and insecure coding practices.      | [Example](#reusable-python-security-scanner)              |
| [reusable-python-style-guide-checker.yml][022]          | Checks Python source code for compliance with the PEP 8 style guide.                             | [Example](#reusable-python-style-guide-checker)           |
| [reusable-ruby-code-smell-detector.yml][023]            | Detects code smells and maintainability issues in Ruby source code.                              | [Example](#reusable-ruby-code-smell-detector)             |
| [reusable-ruby-linter.yml][024]                         | Lints Ruby source code to identify coding issues, style violations and potential problems.       | [Example](#reusable-ruby-linter)                          |
| [reusable-secrets-scanner.yml][025]                     | Scans repositories for exposed secrets and sensitive credentials.                                | [Example](#reusable-secrets-scanner)                      |
| [reusable-shell-script-linter.yml][026]                 | Lints shell scripts to identify syntax errors, portability issues and common scripting mistakes. | [Example](#reusable-shell-script-linter)                  |
| [reusable-slack-notifier.yml][027]                      | Sends configurable GitHub Actions workflow notifications to Slack.                               | [Example](#reusable-slack-notifier)                       |
| [reusable-stale-issue-and-pull-request-handle.yml][028] | Marks and closes inactive issues and pull requests using configurable stale policies.            | [Example](#reusable-stale-issue-and-pull-request-handler) |
| [reusable-workflow-clean-up.yml][029]                   | Cleans up old workflow runs and artifacts using configurable retention policies.                 | [Example](#reusable-workflow-clean-up)                    |
| [reusable-workflow-run-purger.yml][029]                 | Removes obsolete and unwanted GitHub Actions workflow runs.                                      | [Example](#reusable-workflow-run-purger)                  |
| [reusable-workflow-summary.yml][030]                    | Generates a comprehensive Markdown summary of a GitHub Actions workflow run.                     | [Example](#reusable-workflow-summary)                     |
| [reusable-yaml-linter.yml][031]                         | Lints YAML files to identify syntax errors, formatting issues and style violations.              | [Example](#reusable-yaml-linter)                          |

[001]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-citation-validator.yml
[002]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-code-analysis.yml
[003]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-dependabot-manager.yml
[004]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-dockerfile-linter.yml
[005]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-first-time-contributor-greetings.yml
[006]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-github-actions-security.yml
[007]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-github-release-generator.yml
[008]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-json-validator.yml
[009]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-link-checker.yml
[010]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-markdown-lint.yml
[011]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-mkdocs-site-publisher.yml
[012]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-perl-linter.yml
[013]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-php-linter.yml
[014]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-puppet-linter.yml
[015]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-python-ci.yml
[016]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-python-code-auditor.yml
[017]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-python-dependency-updater.yml
[018]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-python-docstring-checker.yml
[019]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-python-linter.yml
[020]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-python-makefile-ci.yml
[021]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-python-security-scanner.yml
[022]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-python-style-guide-checker.yml
[023]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-ruby-code-smell-detector.yml
[024]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-ruby-linter.yml
[025]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-secrets-scanner.yml
[026]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-shell-script-linter.yml
[027]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-slack-notifier.yml
[028]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-stale-issue-and-pull-request-handle.yml
[029]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-workflow-run-purger.yml
[030]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-workflow-summary.yml
[031]: https://github.com/the-lupaxa-project/.github/tree/master/.github/workflows/reusable-yaml-linter.yml

<h2>Minimal Usage Examples (Alphabetical by Workflow File)</h2>

All examples assume you are calling from another (consuming) repo in the organisation and using:

```yaml
uses: the-lupaxa-project/workflows/.github/workflows/<reusable-workflow>.yml@master
```

> [!NOTE]
> This is the standard way to consume these reuable workflows.

<h2 id="reusable-citation-validator">CITATION File Validation</h2>

**Reusable Citation Validator** validates citation files across a repository to ensure they conform to the expected format and standards before changes are
merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable diagnostic
output to aid troubleshooting. This workflow helps maintain accurate, consistent and well-formed citation metadata throughout a project, making it particularly
useful for documentation repositories and projects that rely on structured citation files.

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-citation-validator.yml@master
```

<h2 id="reusable-code-analysis">Code Analysis</h2>

**Reusable Code Analysis performs** static code analysis using GitHub CodeQL to identify security vulnerabilities, coding errors and quality issues across one
or more programming languages. It automatically initialises the CodeQL environment, builds the project where required, and runs the full security-and-quality
query suite before publishing the results to GitHub’s Security tab. By supporting multiple languages through a simple input parameter, this workflow provides a
consistent, centralised approach to code analysis across repositories while helping to identify potential issues early in the development lifecycle.

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
name: Code Analysis

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-code-analysis.yml@master
    with:
      languages: "python,javascript"
```

<h2 id="reusable-dependabot-manager">Dependabot Manager</h2>

**Reusable Dependabot Manager** automates the handling of Dependabot pull requests by applying configurable approval, labelling and merge policies based on
the type of dependency update. Patch and minor updates can be automatically approved and merged, while major version updates can be labelled and annotated for
manual review without being merged automatically. By centralising Dependabot management into a single reusable workflow, this workflow helps streamline
dependency maintenance, reduces manual effort and ensures that automated updates are processed consistently across repositories while still allowing
appropriate oversight for potentially breaking changes.

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-dependabot-manager.yml@master
```

<h2 id="reusable-dockerfile-linter">Dockerfile Linting</h2>

**Reusable Dockerfile Linter** analyses Dockerfiles to identify syntax errors, maintainability issues and deviations from Docker best practices before they
reach production. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable
diagnostic output to suit different development and CI workflows. By enforcing consistent, high-quality Dockerfile standards across repositories, this workflow
helps produce more secure, efficient and maintainable container images while reducing common configuration mistakes.

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
name: Dockerfile Linter

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-dockerfile-linter.yml@master
```

<h2 id="reusable-first-time-contributor-greetings">First Time Contributor Greetings</h2>

**Reusable First-Time Contributor Greetings** automatically posts a friendly welcome message whenever someone opens their first issue or submits their first
pull request to a repository. Custom messages can be configured independently for issues and pull requests, allowing projects to provide contributor guidance,
links to documentation, or community information. This workflow helps create a welcoming first impression, encourages community participation, and provides a
consistent onboarding experience for new contributors across all repositories.

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-first-time-contributor-greeting.yml@master
    secrets:
      repo-token: ${{ secrets.GITHUB_TOKEN }}
```

<h2 id="reusable-github-actions-security">GitHub Actions Security</h2>

**Reusable GitHub Actions Security** validates GitHub Actions workflows to ensure third-party actions are pinned to immutable commit SHAs rather than mutable
tags or branches, helping to protect repositories from supply chain attacks. It supports configurable allow lists for trusted repositories and an optional
dry-run mode that reports issues without failing the workflow. By enforcing secure action pinning across repositories, this workflow promotes GitHub Actions
security best practices and helps maintain a consistent, auditable and secure CI/CD environment.

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-github-actions-security.yml@master
```

<h2 id="reusable-github-release-generator">GitHub Release Generator</h2>

**Reusable GitHub Release Generator** automates the creation of GitHub Releases from repository tags by generating a release changelog, determining the
appropriate release name, and publishing the release using the GitHub Releases API. It supports custom tag and release names, draft and pre-release modes,
and can use either the default GitHub token or a supplied token for publishing. This workflow provides a consistent, fully automated release process across
repositories, ensuring every tagged release includes a well-formatted changelog and standardised release metadata.

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-github-release-generator.yml@master
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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-github-release-generator.yml@master
    secrets:
      github-token: ${{ secrets.GITHUB_TOKEN }}
```

<h2 id="reusable-json-validator">JSON Validator</h2>

**Reusable JSON Validator** validates JSON files throughout a repository to ensure they are syntactically correct and conform to the JSON specification before
changes are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable
diagnostic output to suit different development and CI workflows. By detecting malformed or invalid JSON early in the development process, this workflow helps
prevent configuration errors, deployment failures and application issues caused by incorrectly formatted JSON documents.

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
name: JSON Linter

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-json-linter.yml@master
```

<h2 id="reusable-link-checker">Link Checker</h2>

**Reusable Link Checker** scans repository files for hyperlinks and verifies that they resolve correctly, helping to identify broken, redirected or otherwise
invalid links before changes are merged. It supports configurable command-line options, link whitelisting, file inclusion and exclusion patterns, optional
report-only mode, and configurable diagnostic output to accommodate different CI requirements. By automatically validating links across documentation and source
files, this workflow helps maintain accurate, reliable documentation and improves the overall quality and user experience of a project.

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
name: Link Checker

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-link-checker.yml@master
```

<h2 id="reusable-markdown-linter">Markdown Linter</h2>

**Reusable Markdown Linter** analyses Markdown files to identify formatting inconsistencies, style violations and documentation issues before they are merged
into the repository. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable
diagnostic output to suit different development and CI workflows. By enforcing consistent Markdown standards across documentation, this workflow helps improve
readability, maintainability and the overall quality of project documentation.

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
name: Markdown Linter

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-markdown-linter.yml@master
```

<h2 id="reusable-mkdocs-site-publisher">Mkdocs Site Publisher</h2>

**Reusable MkDocs Site Publisher** builds an MkDocs documentation site in strict mode and publishes the generated static site to GitHub Pages. It supports
configurable Python versions, optional installation of project development extras, fallback installation of MkDocs and Material for MkDocs, and optional
clean-up of existing GitHub Pages deployments before publishing. This workflow provides a consistent documentation publishing pipeline for MkDocs-based
projects, helping repositories produce reliable, validated and automatically deployed project documentation.

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-mkdocs-site-publisher.yml@master
    secrets: inherit
    with:
      python-version: "3.13"
```

<h2 id="reusable-perl-linter">Perl Linter</h2>

**Reusable Perl Linter** analyses Perl source files to detect syntax errors, coding issues and deviations from established coding standards before changes are
merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable diagnostic
output to suit different development and CI workflows. By enforcing consistent coding practices and identifying potential issues early, this workflow helps
improve the reliability, readability and maintainability of Perl applications and scripts.

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
name: Perl Linter

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-perl-linter.yml@master
```

<h2 id="reusable-php-linter">PHP Linter</h2>

**Reusable PHP Linter** analyses PHP source files to detect syntax errors, coding issues and deviations from established coding standards before changes are
merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable diagnostic
output to suit different development and CI workflows. By identifying potential problems early in the development process, this workflow helps improve the
reliability, readability and maintainability of PHP applications while promoting consistent coding practices across repositories.

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
name: PHP Linter

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-php-linter.yml@master
```

<h2 id="reusable-puppet-linter">Puppet Linter</h2>

**Reusable Puppet Linter** analyses Puppet manifests to detect syntax errors, coding issues and deviations from established Puppet coding standards before
changes are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable
diagnostic output to suit different development and CI workflows. By enforcing consistent coding practices and identifying potential configuration issues
early, this workflow helps improve the reliability, maintainability and quality of infrastructure-as-code managed with Puppet.

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
name: Puppet Linter

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-puppet-linter.yml@master
```

<h2 id="reusable-python-ci">Python CI</h2>

**Reusable Python CI** provides a comprehensive continuous integration workflow for Python projects by testing code across a configurable matrix of Python
versions. It installs project dependencies, performs syntax validation, executes static analysis with Ruff and mypy, and runs the project’s test suite using
pytest where available. The workflow supports validating specific files or directories, making it suitable for both small libraries and large applications.
By combining compatibility testing, code quality checks and automated testing into a single reusable workflow, it helps ensure Python projects remain reliable,
maintainable and compatible with multiple Python releases.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input           | Type   | Required | Default                                | Description                                                |
| :-------------- | :----- | :------: | :------------------------------------- | :--------------------------------------------------------- |
| python-versions | string | No       | '["3.10","3.11","3.12","3.13","3.14"]' | JSON array of Python versions.                             |
| script-path     | string | Yes      |                                        | Comma-separated list of files and/or directories to check. |

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-make-ci.yml@master
    secrets: inherit
```

<h2 id="reusable-python-code-auditor">Python Code Auditor</h2>

**Reusable Python Code Auditor** performs comprehensive static analysis of Python source code using Pylama, providing a unified interface to multiple code
quality checkers. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable
diagnostic output to suit different development and CI workflows. By combining the results of multiple analysis tools into a single audit, this workflow helps
identify code quality issues, potential defects and maintainability concerns early in the development process, encouraging consistent, high-quality Python code
across repositories.

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
name: Python Code Auditor

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-code-auditor.yml@master
```

<h2 id="reusable-python-dependency-updater">Python Dependency Updater</h2>

**Reusable Python Dependency Updater** analyses Python project dependencies to identify packages with newer versions available using pur. It supports
configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable diagnostic output to suit
different development and CI workflows. By highlighting outdated dependencies early, this workflow helps keep Python projects up to date, simplifies
dependency maintenance, and encourages the timely adoption of bug fixes, security patches and new features while leaving control of the update process to the
repository maintainer.

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
name: Python Dependency Updater

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-dependency-updater.yml@master
```

<h2 id="reusable-python-docstring-checker">Python Docstring Checker</h2>

**Reusable Python DocString Checker** analyses Python source code to ensure docstrings are present and conform to recognised documentation conventions using
pydocstyle. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable diagnostic
output to suit different development and CI workflows. By enforcing consistent, high-quality API documentation throughout a codebase, this workflow improves
code readability, simplifies maintenance and helps developers produce well-documented Python projects.

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
name: Python Docstring Checker

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-docstring-checker.yml@master
```

<h2 id="reusable-python-makefile-ci">Python Makefile CI</h2>

**Reusable Python CI via Make** provides a Makefile-driven continuous integration workflow for Python projects that already standardise development tasks
through make targets. It runs across a configurable matrix of Python versions, installs development dependencies using a configurable install target, and
executes linting, type checking, testing or any other project-defined checks through a configurable CI target. This workflow is ideal for repositories that
use a shared Make-based build system, allowing each project to control its own CI behaviour while still benefiting from a consistent reusable GitHub Actions
workflow.

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
    uses: the-lupaxa-project/.github/.github/workflows/reusable-python-makefile-ci.yml@master
    secrets: inherit
```

<h2 id="reusable-python-linter">Python Linter</h2>

**Reusable Python Linter** analyses Python source code using Pylint to identify programming errors, code smells, potential bugs and deviations from established
coding standards before changes are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking
validation, and configurable diagnostic output to suit different development and CI workflows. By enforcing consistent coding practices and highlighting
maintainability issues early in the development lifecycle, this workflow helps improve the quality, reliability and long-term maintainability of Python projects.

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
name: Python Linter

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
    uses: the-lupaxa-project/workkflows/.github/workflows/reusable-python-linter.yml@master
```

<h2 id="reusable-python-security-scanner">Python Security Scanner</h2>

**Reusable Python Security Scanner** analyses Python source code using Bandit to identify common security vulnerabilities, insecure coding patterns and
potential weaknesses before changes are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking
validation, and configurable diagnostic output to suit different development and CI workflows. By detecting security issues early in the software development
lifecycle, this workflow helps developers produce more secure Python applications and reduce the risk of introducing exploitable vulnerabilities into production
code.

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
name: Python Security Scanner

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-security-scanner.yml@master
```

<h2 id="reusable-python-style-guide-checker">Python Style Guide Checker</h2>

**Reusable Python Style Guide Checker** analyses Python source code using pycodestyle to verify compliance with the PEP 8 style guide and identify formatting
inconsistencies before changes are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking
validation, and configurable diagnostic output to suit different development and CI workflows. By enforcing a consistent coding style across Python projects,
this workflow improves code readability, simplifies maintenance and encourages adherence to widely accepted Python development standards.

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
name: Python Style Guide Checker

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-python-style-guide-checker.yml@master
```

<h2 id="reusable-ruby-code-smell-detector">Ruby Code Smell Detector</h2>

**Reusable Ruby Code Smell Detector** analyses Ruby source code using Reek to identify code smells, design issues and maintainability concerns before changes
are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable diagnostic
output to suit different development and CI workflows. By highlighting areas of code that may benefit from refactoring, this workflow helps developers improve
code quality, readability and long-term maintainability while encouraging cleaner object-oriented design principles.

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
name: Ruby Code Smell Detector

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-ruby-code-smell-detector.yml@master
```

<h2 id="reusable-ruby-linter">Ruby Linter</h2>

**Reusable Ruby Linter** analyses Ruby source code using RuboCop to identify syntax errors, coding issues, style violations and opportunities for improvement
before changes are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and
configurable diagnostic output to suit different development and CI workflows. By enforcing consistent Ruby coding standards and highlighting potential issues
early in the development process, this workflow helps improve code quality, readability and maintainability across Ruby projects.

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
name: Ruby Linter

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-ruby-linter.yml@master
```

<h2 id="reusable-secrets-scanner">Secrets Scanner</h2>

**Reusable Secrets Scanner** uses TruffleHog to detect exposed secrets, API keys, tokens, passwords and other sensitive credentials within a repository’s
history or recent changes. It supports scanning entire repositories or specific paths, comparing commits or branches, and passing additional TruffleHog
options for customised scanning behaviour. By automatically identifying potential secret leaks before code is merged or released, this workflow helps
strengthen repository security, reduce the risk of credential exposure, and support secure software development practices across all projects.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input      | Type   | Required | Default                      | Description                                                                   |
| :--------- | :----- | :------: | :--------------------------- | :---------------------------------------------------------------------------- |
| path       | string | No       | "."                          | Repository path to scan (relative to workspace)                               |
| base       | string | No       | ""                           | Base ref (maps to --since-commit); leave empty for default PR/push behaviour. |
| head       | string | No       | ""                           | Head ref (maps to --branch); leave empty for default PR/push behaviour.       |
| extra_args | string | No       | "--results=verified,unknown" | Extra arguments passed to TruffleHog CLI.                                     |

<br>
</details>

<h4>Minimal Usage Example</h4>

```yaml
name: Secrets Scanner

on:
  push:
    branches:
      - "**"

  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  secrets-scanner:
    name: Secrets Scanner
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-secrets-scanner.yml
    secrets: inherit

```

<h2 id="reusable-shell-script-linter">Shell Script Linter</h2>

**Reusable Shell Script Linter** analyses shell scripts using ShellCheck to identify syntax errors, portability issues, common scripting mistakes and potential
reliability problems before changes are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking
validation, and configurable diagnostic output to suit different development and CI workflows. By enforcing shell scripting best practices and detecting issues
early, this workflow helps produce more reliable, maintainable and portable shell scripts across a wide range of Unix-like environments.

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
name: Shell Script Linter

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-shell-script-linter.yml@master
```

<h2 id="reusable-slack-notifier">Slack Notifier</h2>

**Reusable Slack Notifier** sends rich, configurable Slack notifications summarising the outcome of GitHub Actions workflow runs. Notifications can be filtered
by workflow result, optionally include individual job statuses and commit messages, and exclude selected jobs to keep alerts focused and relevant. The workflow
automatically avoids notifications for Dependabot activity and external pull requests, reducing unnecessary noise while ensuring important workflow events are
communicated to development teams. It provides a consistent and informative notification mechanism for monitoring CI/CD pipelines across all repositories.

This reusable workflow intentionally contains no guardrails. Its philosophy is simple:

`If you called me, you meant it.`

All logic and guardrails around if we should send the message to slack comes from the consuming workflow.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input                  | Type    | Required | Default | Description                                                                                                                                                   |
| :--------------------- | :------ | :------: | :------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| include_jobs           | string  | No       | "true"  | Controls inclusion of per-job status details. Valid values: "true", "false", "on-failure".                                                                    |
| include_commit_message | boolean | No       | true    | If true, include the commit message in the Slack notification.                                                                                                |
| notify_on_results      | string  | No       | "all"   | Comma-separated list of results to notify on (e.g. "failure,cancelled,timed_out").                                                                            |
| ignore_jobs            | string  | No       | ""      | Comma-separated list of job names to exclude from the per-job Slack fields. Names are normalised (segment after the last "/") and matched case-insensitively. |

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

<h2 id="reusable-stale-issue-and-pull-request-handler">Stale Issue and Pull Request Handler (reusable-stale.yml)</h2>

**Reusable Stale Issue & Pull Request Handler** manages inactive issues and pull requests by automatically marking them as stale after a configurable period
of inactivity and closing them if no further activity occurs. It supports separate stale and close policies for issues and pull requests, custom messages,
configurable labels, and exemption labels for items that should remain open. By applying consistent stale management across repositories, this workflow helps
reduce backlog noise, keeps issue and pull request queues manageable, and ensures abandoned work is handled in a predictable and transparent way.

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-stale-issue-and-pull-request-handle.yml@master
```

<h2 id="reusable-workflow-clean-up">Workflow Clean Up</h2>

**Reusable Workflow Clean Up** removes old GitHub Actions workflow runs and, optionally, old workflow artifacts according to configurable retention and
preservation rules. It supports dry-run mode, branch-based preservation, representative run retention, forced clean-up of non-default branch runs, delete caps,
throttling delays, progress reporting and configurable verbosity. By generating a Markdown clean-up report and optionally uploading it as an artifact, this
workflow provides an auditable and controlled way to reduce Actions history clutter, manage artifact storage and apply consistent repository maintenance policies.

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-clean-up.yml@master
```

<h2 id="reusable-workflow-run-purger">Workflow Run Purger</h2>

**Reusable Workflow Run Purger** automates the removal of obsolete, cancelled, skipped and optionally failed GitHub Actions workflow runs to help keep
repository Actions history clean and manageable. It also supports configurable age-based retention policies, allowing different workflows to be retained for
different periods using flexible rules. By regularly purging unnecessary workflow runs, this workflow reduces clutter within the Actions interface, improves
repository maintenance, and helps organisations apply consistent workflow retention policies across all repositories.

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-run-purger.yml@master
```

<h2 id="reusable-workflow-summary">Workflow Summary</h2>

**Reusable Workflow Summary** generates a detailed Markdown report summarising the outcome of a GitHub Actions workflow run. It categorises jobs by result,
records key workflow metadata—including repository, branch, commit, trigger and execution details—and can optionally upload the generated report as a workflow
artifact for future reference. Individual jobs can be excluded from the summary to reduce noise, making this workflow particularly useful for creating
consistent, easy-to-read execution reports that simplify troubleshooting, auditing and build review across repositories.

<details>
<summary><strong>Click to expand: Inputs Accepted by this workflow</strong></summary>
<br>

| Input                   | Type    | Required | Default | Description                                                                                                                                      |
| :---------------------- | :------ | :------: | :------ | :----------------------------------------------------------------------------------------------------------------------------------------------- |
| artifact_retention_days | number  | No       | 90      | Number of days to retain the uploaded Markdown summary artifact. Must not exceed the repository, organisation, or enterprise limit.              |
| ignore_jobs             | string  | No       | ""      | Comma-separated list of job names to exclude from the summary. Names are normalised (segment after the last "/") and matched case-insensitively. |
| upload_artifact         | boolean | No       | true    | Upload the generated Markdown summary as a workflow artifact.                                                                                    |

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
  markdown-linter:
  uses: the-lupaxa-project/workflows/.github/workflows/reusable-markdown-linter.yml@master

  yaml-linter:
  uses: the-lupaxa-project/workflows/.github/workflows/reusable-yaml-linter.yml@master

  # IMPORTANT!: this is a *job-level* uses, not under steps:
  generate-workflow-summary:
    name: Generate-workflow-summary
    needs:
      - markdown-linter
      - yaml-linter
    if: always()
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-workflow-summary.yml@master
    secrets: inherit
```

> [!NOTE]
> This workflow automatically writes a GitHub Job Summary to the run’s main page, reporting the outcome of each job and providing useful GitHub metadata for context.

<h2 id="reusable-yaml-linter">YAML Linter</h2>

**Reusable YAML Linter** analyses YAML files to detect syntax errors, formatting inconsistencies and deviations from established YAML best practices before
changes are merged. It supports configurable file inclusion and exclusion patterns, optional report-only mode for non-blocking validation, and configurable
diagnostic output to suit different development and CI workflows. By validating YAML configuration files early in the development process, this workflow helps
prevent configuration errors, deployment failures and automation issues while promoting consistent, maintainable YAML across repositories.

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
name: YAML Linter

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
    uses: the-lupaxa-project/workflows/.github/workflows/reusable-yaml-linter.yml@master
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
