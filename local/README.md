# Machine-specific examples

`gitconfig.example` contains optional settings to copy into the machine's
global Git config. It is a reference file, not an active configuration layer.

An existing `local/gitconfig` remains ignored and is left untouched. If an
older setup includes it, it remains active until you remove that include.
For new setups, keep machine-specific settings in the global config outside
this checkout, and actual credentials in the operating system credential store.
