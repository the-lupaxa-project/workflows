<p align="center">
    <a href="https://github.com/the-lupaxa-project">
        <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/the-lupaxa-project/readme-logo.png" alt="The Lupaxa Project Logo" />
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

Many workflows are generic and may also be suitable for use in other GitHub organisations; however, only use within The Lupaxa Project is officially supported.

## Documentation

The [`WORKFLOWS.md`](docs/WORKFLOWS.md) document provides a complete catalogue of available workflows together with links to the detailed documentation for each one.

## Contributing

Improvements, bug fixes, and new reusable workflows are welcome.

Please read the organisation-wide documentation before contributing:

- [Code of Conduct](https://github.com/the-lupaxa-project/.github/blob/master/CODE_OF_CONDUCT.md)
- [Contributing Guide](https://github.com/the-lupaxa-project/.github/blob/master/CONTRIBUTING.md)
- [Security Policy](https://github.com/the-lupaxa-project/.github/blob/master/SECURITY.md)

These documents are maintained in the central `.github` repository.

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
