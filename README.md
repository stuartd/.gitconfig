# Cross-platform Git configuration

This repository keeps shared Git preferences separate from platform and
machine-specific settings:

```text
common/   Shared Git configuration and global ignore rules
macos/    macOS overrides
windows/  Windows overrides
local/    Ignored settings for one machine
scripts/  Installation helpers
```

The shared configuration reflects the Git preferences in use when this
repository was created. Later includes win, so the effective order is:

```text
existing global config -> common -> platform -> local
```

## Install on macOS

Clone the repository to a stable location, then run:

```sh
./scripts/install.sh
```

The installer:

- creates `local/gitconfig` from the example when it does not exist;
- adds the common, macOS, and local files to the global Git include list;
- links `~/.gitignore` to `common/gitignore` when that path is unused; and
- leaves any existing `~/.gitconfig` settings and global ignore file intact.

If an existing `~/.gitignore` is retained, either merge the rules from
`common/gitignore` yourself or change `core.excludesFile` in
`local/gitconfig`.

## Install on Windows

Run PowerShell from the repository:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1
```

The PowerShell installer performs the equivalent setup for the common,
Windows, and local configuration. When `~/.gitignore` does not exist, it
copies the tracked global ignore file there.

## Machine-local settings

Edit `local/gitconfig` for settings that should not follow you to another
computer, such as:

- a work email selected with `includeIf`;
- a signing-key identifier;
- an editor installed at a machine-specific path; or
- a credential helper supplied by GitHub CLI or another local tool.

`local/gitconfig` and every other unapproved file under `local/` are ignored.
Confirm this before adding private settings:

```sh
git check-ignore -v local/gitconfig
```

## Credentials

Do not put passwords, access tokens, private keys, or credential-bearing
remote URLs in any Git configuration file. The platform files use the native
credential store:

- macOS uses Keychain through `osxkeychain`;
- Windows uses Git Credential Manager through `manager`.

Authentication tools may be configured in the ignored `local/gitconfig`.
The example shows the shape of a GitHub CLI override without containing a
credential. Private key files, environment files, and common credential file
names are also ignored at the repository root.

Before committing, review both tracked and ignored state:

```sh
git status --short
git status --short --ignored
git diff --cached
```

## Verify the active configuration

Show each setting together with the file that supplied it:

```sh
git config --global --includes --show-origin --list
```

Useful spot checks:

```sh
git config --global --get user.email
git config --global --get core.autocrlf
git config --global --get-all credential.helper
```

Keep the checkout in a stable location. If it is moved, remove the old
`include.path` entries from `~/.gitconfig`, then re-run the relevant
installer.
