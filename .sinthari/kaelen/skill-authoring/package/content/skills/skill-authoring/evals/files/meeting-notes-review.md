# Review of meeting-notes (skill-review, round 1)

**B1 (blocking)** — The body saves to `.claude/notes/<date>.md`: an assistant-specific path. On another host
the notes go nowhere. Fix: let the user (or the project) say where notes live; default to a path the
project owns.

**B2 (blocking)** — "Always assign an owner to every action item" contradicts "Never invent an owner" when
the transcript does not name one. An agent that follows both freezes or invents. Fix: when no owner is
named, mark the item "owner: to be decided" and list it under Open questions.

**B3 (blocking)** — `references/format.md` is cited but not bundled.

**M1 (improvement)** — No worked example and no failure-modes section.
