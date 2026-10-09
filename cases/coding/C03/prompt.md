# Reject line breaks inside direct-reference requirements

## Problem

A parsed dependency requirement may later be written as one line in a requirements file or lockfile. A direct-reference URL containing a line break is currently accepted, and text after the break becomes part of the stored URL. Serializing that requirement can therefore produce an unexpected extra dependency line.

## Reproduce

```python
from packaging.requirements import Requirement

requirement = Requirement("demo @ https://example.invalid/demo.whl\ninjected==1")
print(requirement.url)
print(str(requirement))
```

The URL and serialized requirement currently contain the newline and `injected==1`. No network request is needed to reproduce the parsing problem.

## Expected behavior

Constructing a `Requirement` must raise `InvalidRequirement` when its direct-reference URL contains a line break, including LF, CR and CRLF, either at the end or followed by more text.

Valid direct-reference URLs, file URLs, URL fragments and a URL followed by a valid environment marker must keep working. Trailing spaces or tabs must remain accepted, and ordinary version requirements must keep their existing behavior.

## Scope and verification

Make a bounded correction to parsing and add regression coverage. The existing requirement tests in `tests/test_requirements.py` are available for verification. Work within the supplied source snapshot; public-internet access is not needed for this task.
