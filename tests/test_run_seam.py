"""The seam every backend implements: one attempt in, one result out.

What the caller hands across it, what the backend may assume about it, and what
must not survive from one invocation to the next. The four adapters' own files
test what each *does* with an attempt; this file tests the handover itself.
"""

from __future__ import annotations

import json
import subprocess

from caliper.harness.base import RunContext
from caliper.harness.claude_code import ClaudeCodeHarness

from conftest import patch_cli_calls


def _agent_says(text: str):
    def fake_run(cmd, **kwargs):
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"content": [{"type": "text", "text": text}]},
                    }
                ),
                json.dumps({"type": "result", "result": text}),
            ]
        )
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    return fake_run


class _Recording(ClaudeCodeHarness):
    """A real backend that remembers the context each invocation was handed."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.seen: list[RunContext] = []
        # What ``extras`` held when the invocation began, captured before this
        # invocation writes to it.
        self.extras_on_entry: list[dict] = []

    def _command(self, ctx: RunContext):
        self.seen.append(ctx)
        self.extras_on_entry.append(dict(ctx.extras))
        ctx.extras["stashed"] = ctx.attempt
        return super()._command(ctx)


def _run(harness: ClaudeCodeHarness, tmp_path, **overrides):
    fields = {
        "task_id": "task-001",
        "attempt": 1,
        "prompt": "Review the diff",
        "skill_refs": [],
        "model": None,
        "timeout": 30,
        "isolated_home": str(tmp_path / "home"),
        "extra_path": [],
    }
    return harness.run(RunContext(**{**fields, **overrides}))


def test_the_backends_own_model_answers_a_request_that_names_none(
    monkeypatch, tmp_path
) -> None:
    """``None`` means "whatever engine this backend was built with".

    The engine is resolved once at the run seam (docs/adr/0004), never per spec,
    so the caller says nothing and the backend supplies its own.
    """
    patch_cli_calls(monkeypatch, _agent_says("done"))
    harness = _Recording(model="backend-default")

    _run(harness, tmp_path)

    assert harness.seen[0].model == "backend-default"


def test_a_named_model_is_not_overridden_by_the_backends_own(
    monkeypatch, tmp_path
) -> None:
    patch_cli_calls(monkeypatch, _agent_says("done"))
    harness = _Recording(model="backend-default")

    _run(harness, tmp_path, model="asked-for")

    assert harness.seen[0].model == "asked-for"


def test_scratch_state_does_not_survive_into_the_next_invocation(
    monkeypatch, tmp_path
) -> None:
    """``extras`` is per-invocation scratch, and a retry is a second invocation.

    The harness object is shared across the runner's worker threads and reused
    across a retried attempt, so a backend stashing per-attempt state (a
    credential it saw, a config dir it made) must not find the previous
    invocation's still there.
    """
    patch_cli_calls(monkeypatch, _agent_says("done"))
    harness = _Recording()

    _run(harness, tmp_path, attempt=1)
    _run(harness, tmp_path, attempt=2)

    # Not "extras is empty": the template legitimately fills it earlier in the
    # same invocation. What must be absent is the previous invocation's stash.
    assert "stashed" not in harness.extras_on_entry[1]
    assert harness.seen[0].extras is not harness.seen[1].extras


def test_the_context_owns_its_lists(tmp_path) -> None:
    """A backend cannot reach back through the seam and edit the caller's state.

    The runner holds one neighbourhood for the whole run and hands it to every
    attempt; the harness object is shared across worker threads. A backend that
    appended to what it was given would otherwise be editing the next attempt's
    inputs, on another thread.
    """
    neighbourhood = []
    forbidden = ["answer.md"]
    ctx = RunContext(
        task_id="task-001",
        attempt=1,
        prompt="hi",
        skill_refs=neighbourhood,
        model=None,
        timeout=30,
        isolated_home=str(tmp_path),
        extra_path=[],
        forbidden_files=forbidden,
    )

    ctx.skill_refs.append("intruder")
    ctx.forbidden_files.append("intruder")

    assert neighbourhood == []
    assert forbidden == ["answer.md"]
