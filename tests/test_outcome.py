from __future__ import annotations

from caliper.harness.base import AttemptResult
from caliper.judge.base import JudgeResult
from caliper.outcome import (
    classify_pre_judge,
    judge_outcome,
    looks_like_infra_failure,
)
from caliper.schema.results import Outcome


def _harness(
    *,
    exit_code: int = 0,
    error: str | None = None,
    timed_out: bool = False,
    final_output: str = "ok",
) -> AttemptResult:
    return AttemptResult(
        transcript=[],
        final_output=final_output,
        exit_code=exit_code,
        duration_seconds=1.0,
        error=error,
        timed_out=timed_out,
    )


def _judge(*, passed: bool, errored: bool = False) -> JudgeResult:
    return JudgeResult(passed=passed, reasoning="r", errored=errored)


# --- judge_outcome: the verdict's half of the label ------------------------
#
# Precedence between the harness result, cheat detection and the judge lives in
# ``assemble_attempt`` (tests/test_attempt.py); this only labels a verdict.


def test_judge_pass() -> None:
    assert judge_outcome(_judge(passed=True)) is Outcome.PASS


def test_judge_task_fail() -> None:
    assert judge_outcome(_judge(passed=False)) is Outcome.TASK_FAIL


def test_judge_error_when_no_verdict_survived() -> None:
    assert judge_outcome(_judge(passed=False, errored=True)) is Outcome.JUDGE_ERROR


# --- classify_pre_judge: the skip predicate the runner shares -------------


def test_pre_judge_none_on_clean_attempt() -> None:
    # Ran cleanly: no skip, proceed to cheat detection and judging.
    assert classify_pre_judge(_harness()) is None


def test_pre_judge_timeout() -> None:
    assert classify_pre_judge(_harness(timed_out=True)) is Outcome.TIMEOUT


def test_pre_judge_infra_on_nonzero_exit() -> None:
    assert classify_pre_judge(_harness(exit_code=1)) is Outcome.INFRA_ERROR


def test_pre_judge_infra_on_signal_despite_zero_exit() -> None:
    h = _harness(exit_code=0, final_output="Spending cap reached resets 4:30am")
    assert classify_pre_judge(h) is Outcome.INFRA_ERROR


def test_pre_judge_ignores_cheat_and_judge_states() -> None:
    # Cheat is not a pre-judge concern: it needs the transcript scan that runs
    # after this predicate, so a clean-exit attempt returns None here.
    assert classify_pre_judge(_harness()) is None


# --- looks_like_infra_failure --------------------------------------------


def test_looks_like_infra_matches_known_signals() -> None:
    for text in (
        "Spending cap reached",
        "rate limit exceeded",
        "HTTP 429 Too Many Requests",
        "the model is overloaded",
        "quota exceeded for this key",
    ):
        assert looks_like_infra_failure(text), text


def test_looks_like_infra_ignores_normal_output() -> None:
    assert not looks_like_infra_failure("The assistant wrote the file successfully.")
    assert not looks_like_infra_failure("")
