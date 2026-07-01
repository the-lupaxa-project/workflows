<p align="center">
    <a href="https://github.com/the-lupaxa-project">
        <img src="https://raw.githubusercontent.com/the-lupaxa-project/org-logos/master/orgs/the-lupaxa-project/readme-logo.png" alt="The Lupaxa Project Logo" width="256" />
    </a>
</p>

<h1 align="center">The Lupaxa Project: Reusable Workflows</h1>

This repository acts as a **central catalog of reusable workflows** for:

- Standardised linting
- Security scanning
- Workflow hardening
- Release preparation & tagging
- Dependency automation
- Slack notifications
- Check-jobs validation
- Code quality enforcement

There are two layers:

1. **Reusable workflows**
   - Live in this repo: `.github/workflows/reusable-*.yml`
   - Called by other repos via `uses: the-lupaxa-project/workflows/.github/workflows/<reusable-workflow>@master`

2. **Local workflows**
   - Live in this repo: `.github/workflows/local-*.yml`
   - Use `uses: ./.github/workflows/reusable-*.yml` to call the shared logic.

A complete description of each reusable workflow is available in the [workflow catalogue](WORKFLOWS.md) which also includes input tables, behaviour notes, and consumer examples.

<h2>General policy</h2>

Across **ALL** Lupaxa Project repositories, we require **ALL 3<sup>rd</sup> party actions** to be pinned to a specific commit SHA **NOT** a version tag.

To help enforce this, we provide:

- reusable-github-actions-security.yml to check and validate **ALL** actions are pinned correctly.
- Local security-hardening workflows in consuming repos that call this reusable workflow.

These security-hardening workflows:

- Scan all workflow files under .github/workflows/.
- Fail the build if they detect uses: entries that:
  - Point to 3<sup>rd</sup> actions without @&lt;SHA&gt;, or
  - Use @&lt;BRANCH&gt;, or version tags (@&lt;TAG&gt;) that are not allow-listed.

> [!NOTE]
> **There is one deliberate exception:**
>
> Calls to the-lupaxa-project/workflows/.github/workflows/*.yml are **explicitly** allow-listed in the security-hardening configuration.

This allows all Lupaxa Project repos to reference organisation workflows using @master, for example:

```yml
  uses: the-lupaxa-project/workflows/.github/workflows/reusable-github-actions-security.yml@master
```

This provides:

- Automatic updates to shared workflows via the this repo.
- Strong SHA pinning for all other third-party actions.

<h2>Naming Conventions</h2>

<h3>Reusable workflows</h3>

- Location: the-lupaxa-project/workflows/.github/workflows/
- Naming pattern: reusable-&lt;NAME&gt;.yml
- Purpose: reusable primitives and bundles that other repos call.

<h4>Examples</h4>

- reusable-code-analysis.yml
- reusable-markdown-linter.yml
- reusable-secrets-scanner.yml
- reusable-yaml-linter.yml

<h3>Consuming workflows</h3>

- Location: .github/workflows/ in a consuming repository.
- Naming pattern: &lt;NAME&gt;.yml
- Purpose: thin orchestration wrappers that:
- Define triggers (on:),
- Group jobs logically,
- Call one or more reusable-*.yml workflows via uses:.

<h4>Consumption Example</h4>

- code-analysis.yml
- markdown-linter.yml
- security-scanner.yml
- yaml-linter.yml

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
