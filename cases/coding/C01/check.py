#!/usr/bin/env python3
"""Reviewer-side public-behavior check; no dependency beyond the pinned Click source."""

import argparse
import importlib
import pathlib
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=pathlib.Path)
    args = parser.parse_args()
    source = args.source.resolve()
    try:
        if sys.version_info < (3, 10):
            raise RuntimeError("Python >=3.10 is required by the pinned source")
        source_dir = source / "src"
        if not (source_dir / "click" / "__init__.py").is_file():
            raise RuntimeError("--source must contain src/click/__init__.py")
        sys.path.insert(0, str(source_dir))
        click = importlib.import_module("click")
        actual = pathlib.Path(click.__file__).resolve()
        if not actual.is_relative_to(source_dir):
            raise RuntimeError(f"Click imported from {actual}, outside requested source")
        CliRunner = importlib.import_module("click.testing").CliRunner
    except Exception as exc:
        print(f"SETUP ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    variable_a = "GLIMMER_CASE_MEASURE_A"
    variable_b = "GLIMMER_CASE_MEASURE_B"

    class EnvvarDisplayTests(unittest.TestCase):
        def invoke(self, envvar, args=(), show_envvar=True, prefix=None, env=None):
            option = click.Option(
                ["--measure"],
                envvar=envvar,
                show_envvar=show_envvar,
                required=True,
                type=click.Choice(["metric", "imperial"]),
            )
            cli = click.Command(
                "measure", params=[option], callback=lambda measure: click.echo(measure)
            )
            clean_env = {
                variable_a: None,
                variable_b: None,
                "GLIMMER CASE": None,
                "GLIMMER,CASE": None,
                "GLIMMER_CASE_MEASURE": None,
            }
            if env:
                clean_env.update(env)
            return CliRunner().invoke(
                cli, list(args), env=clean_env, auto_envvar_prefix=prefix
            )

        def test_sequences_in_missing_and_invalid_errors(self):
            for container in (list, tuple):
                for variables in (
                    [variable_a],
                    [variable_a, variable_b],
                    ["GLIMMER CASE", "GLIMMER,CASE"],
                ):
                    for args in ((), ("--measure", "nonsense")):
                        with self.subTest(container=container.__name__, variables=variables, args=args):
                            result = self.invoke(container(variables), args)
                            self.assertEqual(result.exit_code, 2, result.output)
                            hint = ", ".join(f"'{name}'" for name in variables)
                            self.assertIn(f"(env var: {hint})", result.output)
                            self.assertNotIn("env var: '[", result.output)
                            self.assertNotIn("env var: '(", result.output)

        def test_string_error_display_remains(self):
            result = self.invoke(variable_a)
            self.assertEqual(result.exit_code, 2, result.output)
            self.assertIn(f"(env var: '{variable_a}')", result.output)

        def test_empty_error_envvars_match_none(self):
            for envvar in (None, "", [], ()):
                with self.subTest(envvar=envvar):
                    result = self.invoke(envvar)
                    self.assertEqual(result.exit_code, 2, result.output)
                    self.assertIn("Missing option '--measure'", result.output)
                    self.assertNotIn("env var:", result.output)

        def test_empty_help_envvars_and_auto_prefix(self):
            for envvar in (None, "", [], ()):
                for prefix in (None, "GLIMMER_CASE"):
                    with self.subTest(envvar=envvar, prefix=prefix):
                        result = self.invoke(envvar, ("--help",), prefix=prefix)
                        self.assertEqual(result.exit_code, 0, result.output)
                        self.assertIn("--measure", result.output)
                        if prefix is None:
                            self.assertNotIn("env var:", result.output)
                        else:
                            self.assertIn("env var: GLIMMER_CASE_MEASURE", result.output)
                        self.assertNotIn("[env var: ]", result.output)

        def test_nonempty_help_and_hidden_hint_controls(self):
            result = self.invoke([variable_a, variable_b], ("--help",))
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn(variable_a, result.output)
            self.assertIn(variable_b, result.output)
            for args in ((), ("--help",)):
                hidden = self.invoke([variable_a, variable_b], args, show_envvar=False)
                self.assertEqual(hidden.exit_code, 0 if args else 2, hidden.output)
                self.assertNotIn("env var:", hidden.output)

        def test_environment_resolution_remains(self):
            for envvar in ([variable_a, variable_b], (variable_a, variable_b)):
                result = self.invoke(envvar, env={variable_b: "metric"})
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(result.output.strip(), "metric")
            result = self.invoke(variable_a, env={variable_a: "imperial"})
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(result.output.strip(), "imperial")

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(EnvvarDisplayTests)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    print(f"SOURCE: {source}")
    print(f"RESULT: {'PASS' if result.wasSuccessful() else 'FAIL'}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
