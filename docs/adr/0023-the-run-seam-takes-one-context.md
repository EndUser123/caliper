# The run seam takes one context, not eleven parameters

`HarnessBackend.run` is the narrow seam
([0003](0003-cli-agent-backends-only.md)): one attempt in, one `AttemptResult`
out. It took that attempt as eleven parameters — `task_id`, `attempt`, `prompt`,
then eight keyword-only ones — and `CliHarness.run` packed them straight back
into the `RunContext` declared a hundred lines above it. The runner unpacked its
own `_RunEnv` into the same eleven keywords to make the call.

So the value already existed, and the interface was as wide as the type it
immediately rebuilt.

`run` now takes that value: `run(ctx: RunContext) -> AttemptResult`.

## This narrows the seam rather than widening it

[0018](0018-the-attempt-is-the-unit-of-parallelism.md) refused to thread a
cancellation token through `run`, because a token is a *fact* no backend varies
and the seam should not carry it. That test still applies and this change
passes it: no fact crosses that did not cross before. Only the arity changes.

[0020](0020-a-backend-declares-its-chores-rather-than-performing-them.md) had
already made `ctx` the currency of every hook — `seed_files(ctx)`,
`skills_root(ctx)`, `_command(ctx)`, `_environment(ctx)`. The seam was the last
place still speaking in loose parameters.

The cost is paid in tests, where it was largest: twenty fake harnesses each
restated the eleven-parameter signature, and one of them (`InfraErrorHarness`)
existed only to forward all eleven to `super()`. That forward is now
`super().run(ctx)`, and a fake is its body rather than its signature.

## What a mutable value crossing a seam obliges

A parameter list has no ownership question. A shared object does, and three
answers had to be written down rather than left to be discovered.

**The context owns its lists.** `__post_init__` copies `skill_refs`,
`extra_path` and `forbidden_files`. The runner holds one neighbourhood for the
whole run and hands it to every attempt, and the harness object is shared across
the worker threads ([0018](0018-the-attempt-is-the-unit-of-parallelism.md)), so
a backend that appended to what it was given would be editing the next
attempt's inputs on another thread. The old signature got this free by copying
in `CliHarness.run`; the guarantee now belongs to the value itself, so it holds
for every backend rather than for the one base class. `mcp_servers` is
deliberately shared — it is read-only to every backend that has one.

**The backend resolves its model onto a copy.** A request naming no model means
"whatever engine this backend was built with"
([0004](0004-engine-is-a-runtime-axis-not-a-spec-field.md)), and `CliHarness`
settles that once, up front, so every hook reads a `ctx.model` that is the model
the agent will actually run. It does so with `replace(ctx, ...)` rather than by
assigning to the caller's field: a backend writing back through the seam is the
thing the ownership rule above exists to prevent, and an exception for one field
would make the rule unreadable. Keeping `or` rather than `is None` preserves the
old behaviour for an empty-string model, which falls back exactly like an absent
one.

**The context is per invocation, not per attempt.** A retried attempt is a
second invocation ([0019](0019-an-attempt-may-be-invoked-more-than-once.md)), so
the runner builds the context *inside* the retry closure. Hoisting it out would
hand the retry whatever the failed invocation left behind — and the failed
invocation is the one whose leftovers are least worth keeping. Nothing about the
signature enforces this, so it is pinned by a test that drives a throttled
attempt through the runner and asserts the two invocations were handed different
contexts.

The third of these is the one to re-check if the runner's retry path is ever
restructured: it is a convention held by one line of placement, in a different
file from the seam it serves.
