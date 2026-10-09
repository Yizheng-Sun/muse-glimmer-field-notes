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
        metadata = importlib.import_module("packaging.metadata")
        for module, expected_file in (
            (packaging, package_file),
            (metadata, import_root / "packaging" / "metadata.py"),
        ):
            actual = Path(module.__file__).resolve()
            if actual != expected_file.resolve():
                raise RuntimeError(f"Imported {module.__name__} from {actual}; expected {expected_file}")
    except Exception as exc:
        print(f"SETUP ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(f"Python: {platform.python_version()}", flush=True)
    print(f"Source: {source}", flush=True)
    print(f"Imported: {metadata.__file__}", flush=True)
    Metadata = metadata.Metadata
    InvalidMetadata = metadata.InvalidMetadata

    class LicenseFileChecks(unittest.TestCase):
        def test_drive_relative_license_files_rejected(self) -> None:
            for path in ("C:LICENSE", "d:secrets/key.txt", "Z:licenses/LICENSE"):
                with self.subTest(path=path):
                    with self.assertRaises(InvalidMetadata) as caught:
                        Metadata.from_raw({"license_files": [path]}, validate=False).license_files
                    self.assertEqual(caught.exception.field, "license-file")

        def test_valid_relative_license_files_survive(self) -> None:
            for paths in (
                [],
                ["LICENSE"],
                ["licenses/LICENSE.MIT", "licenses/LICENSE.CC0"],
            ):
                with self.subTest(paths=paths):
                    parsed = Metadata.from_raw({"license_files": paths}, validate=False)
                    self.assertEqual(parsed.license_files, paths)

        def test_existing_invalid_paths_remain_invalid(self) -> None:
            for path in (
                "../LICENSE",
                "/licenses/LICENSE",
                "C:/licenses/LICENSE",
                "licenses\\LICENSE",
                "licenses/*",
            ):
                with self.subTest(path=path):
                    with self.assertRaises(InvalidMetadata):
                        Metadata.from_raw({"license_files": [path]}, validate=False).license_files

        def test_eager_validation_has_same_boundary(self) -> None:
            raw = {"metadata_version": "2.4", "name": "demo", "version": "1.0"}
            valid = Metadata.from_raw(dict(raw, license_files=["licenses/LICENSE"]))
            self.assertEqual(valid.license_files, ["licenses/LICENSE"])
            for path in ("C:LICENSE", "d:secrets/key.txt"):
                with self.subTest(path=path):
                    with self.assertRaises(metadata.ExceptionGroup) as caught:
                        Metadata.from_raw(dict(raw, license_files=[path]))
                    errors = caught.exception.exceptions
                    self.assertTrue(any(isinstance(error, InvalidMetadata) and error.field == "license-file" for error in errors))

    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(LicenseFileChecks)
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
