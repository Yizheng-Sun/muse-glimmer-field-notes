"""Reviewer-side behavior check. Run with --source pointing to a source snapshot."""
from __future__ import annotations

import argparse
import importlib
import platform
import sys
import unittest
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    try:
        if sys.version_info < (3, 10):
            raise RuntimeError("packaging requires Python 3.10 or later")
        import_root = source / "src"
        package_file = import_root / "packaging" / "__init__.py"
        if not package_file.is_file():
            raise FileNotFoundError(f"Not a packaging source snapshot: {source}")
        sys.path.insert(0, str(import_root))
        packaging = importlib.import_module("packaging")
        requirements = importlib.import_module("packaging.requirements")
        for module, expected_file in (
            (packaging, package_file),
            (requirements, import_root / "packaging" / "requirements.py"),
        ):
            actual = Path(module.__file__).resolve()
            if actual != expected_file.resolve():
                raise RuntimeError(f"Imported {module.__name__} from {actual}; expected {expected_file}")
    except Exception as exc:
        print(f"SETUP ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(f"Python: {platform.python_version()}", flush=True)
    print(f"Source: {source}", flush=True)
    print(f"Imported: {requirements.__file__}", flush=True)
    Requirement = requirements.Requirement
    InvalidRequirement = requirements.InvalidRequirement

    class RequirementUrlChecks(unittest.TestCase):
        def test_line_breaks_in_urls_are_rejected(self) -> None:
            for line_break in ("\n", "\r", "\r\n"):
                for tail in ("", "injected==1"):
                    with self.subTest(line_break=repr(line_break), tail=tail):
                        with self.assertRaises(InvalidRequirement):
                            Requirement("demo @ https://example.invalid/demo.whl" + line_break + tail)

        def test_valid_direct_urls_and_horizontal_whitespace(self) -> None:
            for url in (
                "https://example.invalid/demo.whl",
                "file:///tmp/demo.whl",
                "https://example.invalid/demo.whl#sha256=abc",
            ):
                for trailing in ("", " ", "\t"):
                    with self.subTest(url=url, trailing=repr(trailing)):
                        requirement = Requirement("demo @ " + url + trailing)
                        self.assertEqual(requirement.name, "demo")
                        self.assertEqual(requirement.url, url)
                        self.assertNotIn("\n", str(requirement))
                        self.assertNotIn("\r", str(requirement))

        def test_valid_url_markers_and_ordinary_requirements(self) -> None:
            requirement = Requirement('demo @ https://example.invalid/demo.whl ; python_version >= "3.10"')
            self.assertEqual(requirement.url, "https://example.invalid/demo.whl")
            self.assertIsNotNone(requirement.marker)
            ordinary = Requirement("demo>=1.0")
            self.assertEqual(ordinary.name, "demo")
            self.assertIsNone(ordinary.url)
            self.assertEqual(str(ordinary.specifier), ">=1.0")

    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(RequirementUrlChecks)
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
