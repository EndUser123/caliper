# A seam carries only what its readers use

[0023](0023-the-run-seam-takes-one-context.md) narrowed the run seam's *arity*
by bundling what crossed it. This record is about the complement: four places
where something crossed a seam and nobody on the far side read it. Each was
carried because it had been carried before.

The rule they share: a seam's payload is what its readers use. A field nothing
reads is not documentation of intent, it is a second source of truth waiting to
disagree with the first.

## The engine is asked of the objects that have it

`runner.run()` took `backend`, `model`, `judge_backend` and `judge_model`
*beside* the harness and judge objects those strings described. Two spellings of
one fact, and only `RunMeta` wanted them.

`HarnessBackend` gains a `model` property and the `Judge` protocol gains
`backend` and `model`, so `RunMeta` asks the objects instead. This is
[0004](0004-engine-is-a-runtime-axis-not-a-spec-field.md) applied to the
runner's own signature: the engine is resolved once, when those objects are
built, and everything downstream reads it from there rather than being told it
again.

## `AttemptResult` drops the four fields nobody set or read

- `task_id` and `attempt` were an *echo*. The runner numbers the record from its
  own counter and always ignored what came back, so the seam's answer to "which
  attempt is this?" was a value the asker already held and discarded. The
  dataclass had said so in prose for a while — "deliberately carries no
  identity" — while carrying it.
- `cheated` and `cheat_evidence` were dead. Cheat detection moved to the sandbox
  ([0001](0001-attempt-outcome-taxonomy.md) via `caliper/sandbox.py`), and no
  backend has set either field since.

## One place decides an outcome

`assemble_attempt`'s early exits *are* the labels — timeout, infra, cheat,
not-checked, judge verdict — and it then called `classify_outcome` with
arguments shaped so the function could only return the branch the caller had
already chosen. The precedence was written twice, and the second copy was
reachable only through the first.

`judge_outcome` is the surviving half: the part that genuinely decides something
(what a judge's verdict means). [0001](0001-attempt-outcome-taxonomy.md) named
`classify_outcome` as the single seam where an attempt is labelled, and is
amended to name `assemble_attempt` instead. The rule that ADR is about — one
classification, in one place, from typed signals rather than string-sniffing —
is unchanged. Only the function's name and home move.

## Scratch state was a fact each backend could derive

`RunContext.extras` was a dict backends stashed per-attempt state in. Every use
turned out to be derivable or closable-over:

- hermes' home and claude-code's credential file are functions of the isolated
  home, not facts to remember.
- codex's judge output path is now closed over by `PromptCall.read`, a callable
  the backend supplies alongside the argv. A backend whose answer lives
  somewhere the process left behind names that location once, where it builds
  the command, instead of stashing it for a later hook to find.

`extras` existed so two hooks could pass something between themselves without
the base knowing. Giving the hook that *needs* the value the ability to carry it
removes the channel rather than the need.

## Costs accepted

**`Judge` grows two attributes.** It is a structural protocol with one
production implementation and test doubles conforming by shape, so every double
now declares `backend` and `model`. That is the price of asking the object
rather than being told: the shape is wider, and the fact has one home.

**`extras` was an escape hatch, and it is gone.** A future backend needing to
pass genuinely non-derivable state between hooks has no generic channel and must
either derive it, close over it as `PromptCall.read` does, or make the case for
adding a typed field. That is the intended friction — the dict's cost was that
it made the easy answer invisible — but it is friction, and this is the record
to reopen if it ever bites.
