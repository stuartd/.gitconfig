#!/bin/sh

set -eu

if ! command -v git >/dev/null 2>&1; then
	echo "Git is required but was not found on PATH." >&2
	exit 1
fi

case "$(uname -s)" in
	Darwin)
		platform="macos"
		platform_name="macOS"
		;;
	Linux)
		platform="linux"
		platform_name="Linux"
		;;
	*)
		echo "Unsupported platform. Use scripts/install.ps1 on Windows." >&2
		exit 1
		;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "${script_dir}/.." && pwd)
common_config="${repo_root}/common/gitconfig"
platform_config="${repo_root}/${platform}/gitconfig"
local_config="${repo_root}/local/gitconfig"
local_example="${repo_root}/local/gitconfig.example"
global_ignore_source="${repo_root}/common/gitignore"
global_ignore_target="${HOME}/.gitignore"

if [ ! -f "${local_config}" ]; then
	cp "${local_example}" "${local_config}"
	chmod 600 "${local_config}"
	echo "Created ${local_config}"
fi

remove_include() {
	git config --global --fixed-value --unset-all include.path "$1" 2>/dev/null || true
}

for config_path in "${common_config}" "${platform_config}" "${local_config}"; do
	remove_include "${config_path}"
	git config --global --add include.path "${config_path}"
done

if [ ! -e "${global_ignore_target}" ] && [ ! -L "${global_ignore_target}" ]; then
	ln -s "${global_ignore_source}" "${global_ignore_target}"
	echo "Linked ${global_ignore_target} -> ${global_ignore_source}"
elif [ -L "${global_ignore_target}" ] &&
	[ "$(readlink "${global_ignore_target}")" = "${global_ignore_source}" ]; then
	echo "Global ignore link is already current."
else
	echo "Kept existing ${global_ignore_target}; merge common/gitignore manually if wanted."
fi

echo "Installed common, ${platform_name}, and local Git configuration."
echo "Verify with: git config --global --includes --show-origin --list"
