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
   - Called by other repos via `uses: the-lupaxa-project/workflows/.github/workflows/...@master`

2. **Local workflows**
   - Live in this repo: `.github/workflows/local-*.yml`
   - Use `uses: ./.github/workflows/reusable-*.yml` to call the shared logic.

A complete description of each reusable workflow is available in the [workflow catalogue](WORKFLOWS.md) which also includes input tables, behaviour notes, and consumer examples.

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
