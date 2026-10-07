<p align="center">
    <a href="https://github.com/the-lupaxa-project">
        <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/the-lupaxa-project/readme-logo.png" alt="Organisation Logo" />
    </a>
</p>

<h1 align="center">Workflows Repository</h1>

This repository contains the shared reusable GitHub Actions workflows used throughout **The Lupaxa Project**.

By centralising reusable workflows in a single repository, all repositories across every Lupaxa GitHub organisation can share a consistent, secure, and
maintainable CI/CD platform while avoiding duplication.

## Purpose

This repository provides:

- Reusable GitHub Actions workflows.
- Shared CI/CD automation.
- Common quality assurance pipelines.
- Security and compliance workflows.
- Release and documentation automation.
- Workflow maintenance and repository management utilities.

Each workflow is designed to be reusable, configurable, and version controlled so improvements and fixes can be adopted consistently across the project.

## Workflow Architecture

The reusable workflows in this repository are intended to be called from workflows within individual repositories using GitHub's `workflow_call` feature.

A typical repository contains a small local workflow responsible for defining when a workflow should run. That workflow delegates the implementation to one of
the reusable workflows maintained here.

This approach provides:

- Consistent behaviour across repositories.
- Centralised maintenance.
- Reduced duplication.
- Simpler repository-level workflows.
- Easier adoption of improvements and bug fixes.

## Repository Contents

The repository contains:

| Path                                     | Purpose                                    |
| :--------------------------------------- | :----------------------------------------- |
| [.github/workflows/](.github/workflows/) | Reusable GitHub Actions workflows.         |
| [docs/WORKFLOWS.md](docs/WORKFLOWS.md)   | Index of all available reusable workflows. |

## Workflow Naming Convention

All reusable workflows follow a consistent naming convention.

| Item       | Convention                                                                   |
| :--------- | :--------------------------------------------------------------------------- |
| Location   | `.github/workflows/`                                                         |
| Filename   | `reusable-<workflow-name>.yml`                                               |
| Invocation | `uses: the-lupaxa-project/workflows/.github/workflows/<workflow>.yml@master` |

This convention provides a predictable interface for every reusable workflow within the repository.

## Compatibility

These workflows are developed primarily for repositories within **The Lupaxa Project**.

Many workflows are generic and may also be suitable for use in other GitHub organisations; however, only use within **The Lupaxa Project** is officially supported.

## Documentation

The [`WORKFLOWS.md`](docs/WORKFLOWS.md) document provides a complete catalogue of available workflows together with links to the detailed documentation for each one.

### GitHub Release Generator

[`reusable-github-release-generator.yml`](.github/workflows/reusable-github-release-generator.yml)
creates GitHub Releases from tags. The release **body is short fixed text** (not
a commit changelog). Use GitHub’s compare control on the releases page for
diffs. Bodies end with a period:

| Tag pattern                    | Body                              |
| :----------------------------- | :-------------------------------- |
| `0.1.0`                        | `Initial Release.`                |
| `1.0.0`                        | `Initial Production Release.`     |
| stable `> 0.1.0` and `< 1.0.0` | `Incremental Release.`            |
| stable `> 1.0.0`               | `Incremental Production Release.` |
| `*-rcN`                        | `Release Candidate N.`            |
| `*-draftN`                     | `Draft Release N.`                |
| `*-devN`                       | `Development Release N.`          |
| otherwise                      | empty                             |

Suffix tags (`-rc` / `-draft` / `-dev`) take precedence. Full details:
[WORKFLOWS.md — GitHub Release Generator](docs/WORKFLOWS.md#github-release-generator).

## Contributing

Improvements, bug fixes, and new reusable workflows are welcome.

Please read the organisation-wide documentation before contributing:

- [Code of Conduct](https://github.com/the-lupaxa-project/.github/blob/master/docs/CODE_OF_CONDUCT.md)
- [Contributing Guide](https://github.com/the-lupaxa-project/.github/blob/master/docs/CONTRIBUTING.md)
- [Security Policy](https://github.com/the-lupaxa-project/.github/blob/master/docs/SECURITY.md)

These documents are maintained in the central `.github` repository.

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
