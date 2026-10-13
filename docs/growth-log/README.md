# Growth Log

Lessons learned and recurring problems, using ECC's built-in `growth-log`
skill convention as-is (not a custom system — see the skill itself for the
full writing guide).

## Convention (from the ECC `growth-log` skill)

- **One file per day**: `YYYY-MM-DD.md`.
- **Pattern over narration**: each entry states root cause → transferable
  rule → a recognizable signal for next time. Not "fixed a bug in X."
- **Merge, don't duplicate**: before writing a new entry, check existing
  entries for the same root cause. Same cause, different symptom → add as
  another example under the existing entry.
- **Threshold**: only write an entry if the task involved real debugging,
  rework, rollback, or a non-obvious decision. Skip trivial fixes.

## For future ECC pipeline runs / agents

Don't read this whole log on every task. Skim filenames (dates won't help)
and entry headings for keywords relevant to the current task's area before
deciding whether to read an entry in full.
