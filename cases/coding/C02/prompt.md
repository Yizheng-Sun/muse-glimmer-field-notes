# Keep abbreviations in generated command summaries

## Problem

Generated short help stops too early when the first sentence contains an abbreviation. A command whose long help is `Compare apples vs. pears.` appears in its parent group's help with the summary `Compare apples vs.`.

## Reproduce

```python
import click
from click.testing import CliRunner

command = click.Command("compare", help="Compare apples vs. pears.")
group = click.Group("tools", commands={"compare": command})
print(CliRunner().invoke(group, ["--help"]).output)
print(command.get_short_help_str(35))
```

The complete first sentence fits the available width, so both summaries should include `pears.`. The same problem occurs with abbreviations such as `e.g.` followed by lowercase text.

## Expected behavior

- A period at the end of a word ends the first sentence only when it ends the text or the following word does not start with a lowercase character. A lowercase following word continues the sentence. For example, `Pick a fruit. Next action follows.` and `Pick a fruit. 3 remain.` both shorten to `Pick a fruit.`, while `Pick a fruit. more remain.` stays complete when it fits.
- Only the first paragraph contributes to a generated summary. Whitespace is collapsed, and the initial no-rewrap marker `\b` is omitted.
- If the first sentence exceeds the requested width, shorten at a word boundary and include `...` within that width. Do not split hyphenated words or individual long words. For example, `Weigh apples vs. pears and plums.` at width 20 becomes `Weigh apples vs....`; `well-behaved.` at width 8 becomes `...`.
- When shortening is necessary but the width is below three characters, return the complete `...` marker. Text that already fits still stays unchanged: `ab` at width 2 remains `ab`.
- Empty help stays empty, and an explicit `short_help` keeps its existing behavior. Group help and `Command.get_short_help_str` must show the same corrected summaries.

## Scope and verification

Make a focused change to generated short help without adding a runtime dependency. Preserve existing help formatting and explicitly supplied summaries. Use the source's existing tests and add regression coverage as useful. The requirement concerns the output and allows any implementation that produces it.
