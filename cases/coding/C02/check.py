#!/usr/bin/env python3
"""Reviewer-side public short-help behavior check for a specified Click source."""

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

    class ShortHelpTests(unittest.TestCase):
        def short(self, text, width=45):
            return click.Command("sample", help=text).get_short_help_str(width)

        def test_abbreviations_and_sentence_boundaries(self):
            cases = [
                ("Compare apples vs. pears.", 35, "Compare apples vs. pears."),
                ("List items e.g. books.", 35, "List items e.g. books."),
                ("Pick a fruit. Next action follows.", 45, "Pick a fruit."),
                ("Pick a fruit. 3 remain.", 45, "Pick a fruit."),
                ("Pick a fruit. more remain.", 45, "Pick a fruit. more remain."),
                ("The version is v2.5 today.", 45, "The version is v2.5 today."),
                ("One sentence.", 45, "One sentence."),
            ]
            for text, width, expected in cases:
                with self.subTest(text=text, width=width):
                    self.assertEqual(self.short(text, width), expected)

        def test_word_aware_width_and_ellipsis(self):
            cases = [
                ("Weigh apples vs. pears and plums.", 20, "Weigh apples vs...."),
                ("123 567 90123.", 10, "123 567..."),
                ("123 5678 xxxxxx", 10, "123..."),
                ("well-behaved.", 8, "..."),
                ("supercalifragilistic", 10, "..."),
                ("ab cd", 3, "..."),
                ("ab cd", 2, "..."),
                ("ab cd", -1, "..."),
                ("ab", 2, "ab"),
                ("", 2, ""),
                ("123 567 90", 10, "123 567 90"),
            ]
            for text, width, expected in cases:
                with self.subTest(text=text, width=width):
                    value = self.short(text, width)
                    self.assertEqual(value, expected)
                    self.assertLessEqual(len(value), max(width, 3))

        def test_first_paragraph_whitespace_and_no_rewrap_marker(self):
            cases = [
                ("  Compare\t apples\nvs. pears.  ", "Compare apples vs. pears."),
                ("Compare apples vs. pears.\n\nIgnore this paragraph.", "Compare apples vs. pears."),
                ("\b\nCompare apples vs. pears.", "Compare apples vs. pears."),
                ("\b", ""),
                ("\n\t  ", ""),
            ]
            for text, expected in cases:
                with self.subTest(text=text):
                    self.assertEqual(self.short(text), expected)

        def test_explicit_short_help_and_empty_command_controls(self):
            command = click.Command(
                "sample", help="A generated sentence.", short_help="Explicit vs. help."
            )
            self.assertEqual(command.get_short_help_str(2), "Explicit vs. help.")
            self.assertEqual(click.Command("empty").get_short_help_str(), "")

        def test_group_help_uses_complete_summary(self):
            command = click.Command("compare", help="Compare apples vs. pears.")
            group = click.Group("tools", commands={"compare": command})
            result = CliRunner().invoke(group, ["--help"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Compare apples vs. pears.", result.output)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ShortHelpTests)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    print(f"SOURCE: {source}")
    print(f"RESULT: {'PASS' if result.wasSuccessful() else 'FAIL'}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
