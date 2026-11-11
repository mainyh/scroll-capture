# Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

Windows release binaries of ScrollCapture (`ScrollCapture-vX.Y.Z-win-x64.exe` and the `.exe` inside the
`.zip`) are signed through the SignPath Foundation program once the project is accepted. Releases published
before that are unsigned.

## What gets signed

- Only `ScrollCapture.exe`, built from the source code in this repository.
- Builds run on GitHub-hosted runners by the [release workflow](.github/workflows/release.yml) when a
  `vX.Y.Z` tag is pushed. The workflow builds from the tagged commit, runs the tests, and submits the unsigned
  executable to SignPath. Nothing is built or signed on a personal machine.
- Every signing request is approved manually by an approver (see below) before the signed file is published.
- The signed executable carries the product name `ScrollCapture` and the release version in its file metadata.

## Team roles

| Role | Members |
|---|---|
| Committers and reviewers | [@mainyh](https://github.com/mainyh) (owner) |
| Approvers | [@mainyh](https://github.com/mainyh) |

- **Committers** may change the source code directly.
- **Reviewers**: every change from someone who is not a committer (for example a pull request) is reviewed
  by a committer before it is merged.
- **Approvers**: each signing request is approved by an approver.

All team members use multi-factor authentication for GitHub and SignPath.

## Privacy policy

This program will not transfer any information to other networked systems unless specifically requested by
the user or the person installing or operating it.

In detail:

- ScrollCapture captures the screen and saves images **only on your computer**, in the folder you choose.
- Settings (`settings.json`) and a log file (`scrollcapture.log`) are stored in `%APPDATA%\ScrollCapture`.
  They never leave your computer.
- The program makes no network connections. The only exception is when you click a link in the About tab
  (GitHub page, open-source notices), which opens your web browser.
- Copying to the clipboard only happens when you press **Copy**.

## Installation and removal

ScrollCapture is portable: it is not installed and does not change system settings.
To remove it, delete `ScrollCapture.exe` and the folder `%APPDATA%\ScrollCapture`.

## Reporting a problem

If you believe a signed ScrollCapture binary is malicious or was not built from this repository, please
[open an issue](https://github.com/mainyh/scroll-capture/issues) or contact SignPath Foundation
(https://signpath.org/).
