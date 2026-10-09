# Render environment-variable hints clearly

## Problem

When an option enables `show_envvar`, its error messages are confusing if the option accepts several environment-variable names. Empty environment-variable configurations also produce empty hints in help and errors.

## Reproduce

Create a command with a required `--measure` option that accepts `metric` or `imperial`, enables `show_envvar=True`, and uses `envvar=["APP_MEASURE", "MEASURE"]`. Invoke it without the option or either environment variable. The missing-option error currently displays the representation of the list, rather than a readable list of variable names. Supplying an invalid choice has the same problem.

Also inspect `--help` and a missing-option error when the configuration is `envvar=""` or `envvar=[]`. Empty configurations currently leave an empty environment hint.

## Expected behavior

- Error hints name each variable separately, in the configured order, with quotes around each name. A sequence containing `APP_MEASURE` and `MEASURE` should read `(env var: 'APP_MEASURE', 'MEASURE')`. Lists and tuples should behave alike; names containing spaces or commas must remain individually quoted.
- Empty strings and empty sequences behave like `envvar=None`: no empty hint appears in errors or help.
- If help uses an automatic environment prefix, an empty explicit configuration still permits that automatic name to appear, as it does with `envvar=None`.
- A single string environment-variable name, normal environment-variable resolution, and `show_envvar=False` retain their existing behavior.

## Scope and verification

Make a focused change to Click's public option behavior. Preserve option parsing, choice validation, help generation, and environment-variable precedence. Use the existing source tests and add focused regression tests as useful. Do not depend on a particular internal implementation or add a runtime dependency.
