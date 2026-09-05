"""Integration checks using temporary files inside this repository only."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parent.parent


class CheckConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="check fixture ", dir=REPO / "tests")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        (self.repo / "scripts").mkdir()
        self.script = self.repo / "scripts/check-config.py"
        shutil.copyfile(REPO / "scripts/check-config.py", self.script)
        self.global_config = self.repo / "machine.gitconfig"
        self.global_config.write_text("")
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=str(self.global_config), GIT_CONFIG_NOSYSTEM="1")
        for directory in ("common", "macos", "linux", "windows"):
            (self.repo / directory).mkdir()
            (self.repo / directory / "gitconfig").write_text("")

    def write(self, relative, content):
        path = self.repo / relative
        path.write_text(content)
        return path

    def git_set(self, path, key, value):
        subprocess.run(
            ["git", "config", "--file", str(path), "--add", key, value],
            env=self.env, check=True, capture_output=True,
        )

    def run_check(self, platform="macos"):
        # Detect writes to the inputs, including content-preserving rewrites.
        def snapshot():
            return {
                str(path): (path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode)
                for path in self.repo.rglob("*") if path.is_file()
            }
        before = snapshot()
        result = subprocess.run(
            [sys.executable, "-B", str(self.script), "--platform", platform],
            cwd=self.repo, env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(before, snapshot(), "The checker changed its input files")
        return result

    def test_missing_different_and_local_only_are_separate(self):
        self.write("common/gitconfig", '[alias]\n example = status -sb\n[core]\n editor = nano\n')
        self.global_config.write_text('[core]\n editor = vim\n[sequence]\n editor = code --wait\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Missing locally (1):\n  git alias example not found", result.stdout)
        self.assertIn('Different values (1):\n  core.editor\n    repo:  "nano"\n    local: "vim"', result.stdout)
        self.assertIn("Only local; absent from this platform's references (1):\n  sequence.editor", result.stdout)

    def test_only_selected_platform_overrides_common(self):
        self.write("common/gitconfig", '[core]\n editor = common-editor\n')
        for platform, editor in (("macos", "nano"), ("linux", "vi"), ("windows", "notepad")):
            self.write(f"{platform}/gitconfig", f'[core]\n editor = {editor}\n')
        for platform, editor in (("macos", "nano"), ("linux", "vi"), ("windows", "notepad")):
            with self.subTest(platform=platform):
                self.global_config.write_text(f'[core]\n editor = {editor}\n')
                result = self.run_check(platform)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("1 reference settings match.", result.stdout)

    def test_includes_booleans_and_helper_resets(self):
        self.write("common/gitconfig", '[pull]\n rebase = true\n[fetch]\n prune = true\n')
        self.write("macos/gitconfig", '[credential]\n helper =\n helper = osxkeychain\n')
        self.global_config.write_text('[pull]\n rebase = false\n[credential]\n helper = old-helper\n')
        machine = self.write("machine extra.gitconfig", '[pull]\n rebase = YES\n[fetch]\n prune\n[credential]\n helper =\n helper = osxkeychain\n')
        self.git_set(self.global_config, "include.path", str(machine))
        self.git_set(machine, "credential.https://gist.github.com.helper", "")
        self.git_set(machine, "credential.https://gist.github.com.helper", "!/opt/homebrew/bin/gh auth git-credential")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("3 reference settings match.", result.stdout)
        self.assertIn("Only local; absent from this platform's references (1):", result.stdout)
        self.assertIn("credential.https://gist.github.com.helper", result.stdout)
        self.assertNotIn("old-helper", result.stdout)
        self.assertNotIn("  include.path", result.stdout)

    def test_reference_includes_do_not_count_as_installed_copies(self):
        common = self.write("common/gitconfig", '[core]\n editor = nano\n[alias]\n hidden = status\n again = reference-alias\n')
        self.global_config.write_text('[core]\n editor = vim\n[alias]\n again = machine-alias\n')
        self.git_set(self.global_config, "include.path", str(common))
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Reference files still loaded by your global config:", result.stdout)
        self.assertIn("git alias hidden not found", result.stdout)
        self.assertIn('local: "vim"', result.stdout)
        self.assertIn('alias.again\n    repo:  "reference-alias"\n    local: "machine-alias"', result.stdout)
        self.assertNotIn("Ignored:", result.stdout)

    def test_multiline_aliases_are_compared_without_execution(self):
        value = '!printf "hello # world\\t"\n# second line'
        self.git_set(self.repo / "common/gitconfig", "alias.example", value)
        self.git_set(self.global_config, "alias.example", value)
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 reference settings match.", result.stdout)
        self.assertIn("Missing locally (0):", result.stdout)

    def test_helper_order_matters(self):
        self.write("macos/gitconfig", '[credential]\n helper = first\n helper = second\n')
        self.global_config.write_text('[credential]\n helper = second\n helper = first\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('repo:  ["first", "second"]', result.stdout)
        self.assertIn('local: ["second", "first"]', result.stdout)

    def test_no_global_file_reports_missing_settings(self):
        self.write("common/gitconfig", '[core]\n editor = nano\n')
        self.global_config.unlink()
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("core.editor not found", result.stdout)

    def test_invalid_config_is_an_error_not_an_empty_report(self):
        self.global_config.write_text('[broken\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertIn("Cannot compare Git configuration:", result.stderr)
        self.assertNotIn("Missing locally", result.stdout)

    def test_repository_local_config_is_out_of_scope(self):
        self.write("common/gitconfig", '[core]\n editor = nano\n')
        self.global_config.write_text('[core]\n editor = nano\n')
        subprocess.run(['git', 'init', '-q', str(self.repo)], env=self.env, check=True, capture_output=True)
        self.git_set(self.repo / '.git/config', 'core.editor', 'wrong-editor')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 reference settings match.", result.stdout)
        self.assertNotIn("wrong-editor", result.stdout)


if __name__ == "__main__":
    unittest.main()
