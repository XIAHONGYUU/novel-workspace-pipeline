# Security Policy

## Supported Version

This repository currently supports security fixes on the active `main` branch only.

| Version | Supported |
| --- | --- |
| `main` | Yes |

## Reporting A Vulnerability

Please do not open a public issue for a security-sensitive problem.

Use one of these paths instead:

1. Open a private GitHub security advisory if that option is available for the repository.
2. If private advisory reporting is not available, contact the repository owner directly through GitHub first.
3. If neither path is available, open a minimal public issue without exploit details and only state that you need a private contact channel.

## What To Include

Please include:

- affected file or script
- reproduction steps
- expected impact
- whether the issue requires local execution, crafted input, or leaked workspace content
- any suggested mitigation if you already tested one

## Scope Notes

This repository is mostly local workflow code, validators, and scaffolding scripts. The most likely security-relevant issues are:

- path handling mistakes
- unsafe shell execution assumptions
- accidental exposure of local workspace content
- unexpected writes outside the intended workspace

## Response Goal

The goal is to acknowledge a report quickly, confirm impact, and land a fix on `main` when the report is valid.
