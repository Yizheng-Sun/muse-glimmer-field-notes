# Reject drive-relative license-file paths

## Problem

License-file metadata requires paths relative to the project. Windows drive-relative forms such as `C:LICENSE` and `d:secrets/key.txt` currently pass validation even though they can refer to a location on a particular drive outside the project directory.

## Reproduce

```python
from packaging.metadata import Metadata

parsed = Metadata.from_raw({"license_files": ["C:LICENSE"]}, validate=False)
print(parsed.license_files)
```

Reading `license_files` currently accepts the drive-relative path. The same issue occurs when complete metadata is validated eagerly.

## Expected behavior

Reading the field in the example must raise `InvalidMetadata`. Reject drive-relative license-file paths regardless of the drive letter's case. Eager metadata validation must report the same invalid field.

Valid project-relative paths such as `LICENSE` and `licenses/LICENSE.MIT` must remain accepted and retain their spelling. Existing rejection of absolute paths, parent-directory escapes, backslash-delimited paths and glob patterns must keep working. This validation should give the same result when run on Windows, macOS or Linux.

## Scope and verification

Make a bounded correction to metadata path validation and add regression coverage. The existing license-file tests in `tests/test_metadata.py` are available for verification. Work within the supplied source snapshot; no filesystem access outside that snapshot or public-internet access is needed.
