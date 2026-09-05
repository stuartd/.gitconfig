# Git configuration reference

This repository is a reference for setting up Git the way I like it.
It contains configuration to review and copy manually, plus a read-only
comparison script. There is no installer, and Git should not include files
directly from this checkout.

If an earlier installer added includes for this checkout, they remain active
until you remove them yourself. Preserve any settings you want in your own
Git config before removing those includes.

```text
common/gitconfig         Shared preferences
common/gitignore         Suggested global ignore rules
macos/gitconfig          macOS preferences
linux/gitconfig          Linux preferences
windows/gitconfig        Windows preferences
local/gitconfig.example  Examples of machine-specific settings
scripts/check-config.py  Compare the references with global Git settings
```

## Comparing a machine

The checker requires Git and Python 3.9 or newer, with no extra Python packages.
On macOS or Linux, run:

```sh
python3 scripts/check-config.py
```

On Windows, run:

```powershell
py -3 scripts/check-config.py
```

It detects the current platform and compares `common/gitconfig` plus that
platform's file against the machine's **global** Git configuration. To select
the reference platform explicitly, add `--platform macos`, `--platform linux`,
or `--platform windows`.

The report lists missing settings (for example, `git alias example not found`),
settings with different values, and local settings absent from the selected
references. Local-only settings can be intentional, such as a Gist credential
helper with a machine-specific path. All preference keys are compared by default.

The checker follows global config includes, but excludes values loaded from
this checkout's common and platform reference files so they do not count as
independently configured local values. It lists any such sources separately.
Other included files, including an existing `local/gitconfig`, remain part of
the local comparison. Include directives themselves are not preferences.

For scalar preferences it compares the last value; for credential helper keys
it compares the ordered list after empty resets. Boolean spellings such as
`true` and `yes` are treated as equivalent for the reference Boolean settings.
Other values are compared as text. It does not execute aliases or helpers,
simulate authentication for a remote, or check whether an editor is installed.
Repository-local and system config are outside the comparison.

The script only reports differences. It never changes files, and differences
do not cause a failing exit status; errors reading the configuration do.

## Setting up a machine

Review `common/gitconfig` and the file for the current operating system, then
edit the machine's global configuration:

```sh
git config --global --edit
```

Copy the settings you want into that file. If a setting already exists with a
different value, choose which value to keep and edit the existing entry.
Keep machine-specific settings there too, including editor paths, identities,
signing keys, and GitHub CLI credential helpers.

The platform files use:

- macOS: `nano`, LF input normalization, and the Keychain credential helper;
- Linux: `nano`, LF input normalization, and the in-memory credential cache;
- Windows: CRLF working files and Git Credential Manager, leaving editor
  selection to the machine's existing configuration.

Check that the editor and credential helper you choose are installed.
The full set of shared preferences requires Git 2.44 or newer.

Credential helpers are ordered: an empty `helper` resets earlier helpers.
Put machine-specific GitHub/Gist helper blocks after the general platform
helper block so their overrides remain effective. `local/gitconfig.example`
contains examples to copy, including a GitHub CLI helper.

For global ignore rules, review `core.excludesFile` before copying it. Merge
the patterns from `common/gitignore` into your existing global ignore file,
or copy them to a file outside this checkout and set `core.excludesFile` to
that location.

## Checking the result

Show the global settings and their source files:

```sh
git config --global --includes --show-origin --list
```

Settings copied into the global config should have that file as their source,
rather than a path inside this repository. Once any old repo includes have
been removed, updating or moving this checkout does not change your installed
preferences; apply future changes manually.

Keep passwords, access tokens, and private keys out of these reference files.
Machine-specific paths and helper commands belong in the machine's own config.

## Checking the comparison script

```sh
python3 -B -m unittest discover -s tests -v
```

The checks create and clean up fixtures inside this repository and do not
modify the machine's Git configuration.
