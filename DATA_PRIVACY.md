# Data privacy boundary

This public repository is intentionally **code-only at the row level**. The
supplied Kestrel Home files stay under `data/raw/`, which is excluded from Git.
The trained artifact, row-level `predictions.csv`, logs, integrity manifest,
and confidential submission ZIP are also excluded.

Never force-add those excluded files or change the ignore rules to publish
them. Reviewers with the original task pack can place the eight source files in
`data/raw/` and reproduce the model and deliverables from the README. The full
confidential submission must be transferred only through the approved private
channel.
