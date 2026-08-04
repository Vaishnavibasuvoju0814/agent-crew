import logging
import sys
import time
from pathlib import Path
from unittest.mock import patch

# Ensure backend/ is on sys.path so 'app' package is importable when running
# `pytest backend` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents import researcher_node
from app.tools import format_search_results


def _patch_call_llm():
    # Return the received prompt so tests can inspect aggregated notes.
    return patch("app.agents.call_llm", side_effect=lambda system, user, max_tokens=1200: user)


def _base_state(sub_questions):
    return {
        "topic": "t",
        "sub_questions": sub_questions,
        "research_notes": "",
        "draft": "",
        "review_notes": "",
        "approved": False,
        "revised": False,
        "steps": [],
    }


def test_researcher_sequential_ordering_preserved():
    def slow_search(query):
        time.sleep(0.05)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=slow_search), _patch_call_llm():
        state = researcher_node(_base_state(["a", "b", "c"]))

    combined = state["research_notes"]
    assert combined.index("Sub-question: a") < combined.index("Sub-question: b") < combined.index("Sub-question: c")


def test_researcher_partial_failure_continues():
    def search(query):
        if query == "b":
            raise RuntimeError("search exploded")
        return [{"title": query, "url": "u", "snippet": "ok"}]

    with patch("app.agents.web_search", side_effect=search), _patch_call_llm():
        state = researcher_node(_base_state(["a", "b", "c"]))

    notes = state["research_notes"]
    assert "Sub-question: a" in notes
    assert "Sub-question: b" in notes
    assert "Search failed: search exploded" in notes
    assert "Sub-question: c" in notes
    assert state["steps"][-1]["agent"] == "researcher"


def test_researcher_empty_sub_questions():
    with _patch_call_llm():
        state = researcher_node(_base_state([]))

    assert state["research_notes"] == ""
    assert len(state["steps"]) == 1
    assert state["steps"][0]["agent"] == "researcher"


def test_researcher_concurrent_execution():
    timings = {}

    def search(query):
        timings[query] = time.perf_counter()
        time.sleep(0.1)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=search), _patch_call_llm():
        start = time.perf_counter()
        state = researcher_node(_base_state(["a", "b", "c"]))
        duration = time.perf_counter() - start

    # Sequential would be ~0.3s; concurrent should be closer to ~0.1s.
    assert duration < 0.25
    assert all(q in timings for q in ["a", "b", "c"])
    assert state["research_notes"]


def test_researcher_logs(caplog):
    def search(query):
        time.sleep(0.01)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=search), _patch_call_llm():
        with caplog.at_level(logging.DEBUG, logger="app.agents"):
            researcher_node(_base_state(["q1"]))

    assert any("Starting 1 concurrent research task(s)" in r.message for r in caplog.records)
    assert any("Submitting search for: q1" in r.message for r in caplog.records)
    assert any("Search completed for 'q1'" in r.message for r in caplog.records)


def test_format_search_results_empty():
    assert format_search_results([]) == "No results found."


def test_format_search_results_formats():
    results = [{"title": "t", "url": "u", "snippet": "s"}]
    assert "- t: s (u)" in format_search_results(results)


# ---------------------------------------------------------------------------
# Large concurrent workload tests (issue #43)
# ---------------------------------------------------------------------------

def _make_questions(n):
    """Return a list of n distinct question strings."""
    return [f"question_{i}" for i in range(n)]


def _fast_search(query):
    """Minimal stub: returns one result instantly."""
    return [{"title": query, "url": f"https://example.com/{query}", "snippet": f"snippet for {query}"}]


def test_researcher_20_concurrent_all_complete():
    """All 20 tasks must appear in research notes — no silent drops."""
    questions = _make_questions(20)

    with patch("app.agents.web_search", side_effect=_fast_search), _patch_call_llm():
        state = researcher_node(_base_state(questions))

    notes = state["research_notes"]
    for q in questions:
        assert f"Sub-question: {q}" in notes, f"Missing result for {q}"
    assert state["steps"][-1]["agent"] == "researcher"


def test_researcher_50_concurrent_all_complete():
    """All 50 tasks must appear in research notes — no silent drops."""
    questions = _make_questions(50)

    with patch("app.agents.web_search", side_effect=_fast_search), _patch_call_llm():
        state = researcher_node(_base_state(questions))

    notes = state["research_notes"]
    for q in questions:
        assert f"Sub-question: {q}" in notes, f"Missing result for {q}"
    assert state["steps"][-1]["agent"] == "researcher"


def test_researcher_20_concurrent_ordering_preserved():
    """Output order must match input order regardless of completion order."""
    questions = _make_questions(20)

    # Reverse-stagger sleep times so later questions finish first.
    def staggered_search(query):
        idx = int(query.split("_")[1])
        delay = (20 - idx) * 0.005  # question_0 sleeps longest
        time.sleep(delay)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=staggered_search), _patch_call_llm():
        state = researcher_node(_base_state(questions))

    notes = state["research_notes"]
    positions = [notes.index(f"Sub-question: question_{i}") for i in range(20)]
    assert positions == sorted(positions), "Output order does not match input order"


def test_researcher_50_concurrent_ordering_preserved():
    """Output order must match input order for 50 questions with varied latency."""
    questions = _make_questions(50)

    def staggered_search(query):
        idx = int(query.split("_")[1])
        delay = (50 - idx) * 0.002  # question_0 sleeps longest
        time.sleep(delay)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=staggered_search), _patch_call_llm():
        state = researcher_node(_base_state(questions))

    notes = state["research_notes"]
    positions = [notes.index(f"Sub-question: question_{i}") for i in range(50)]
    assert positions == sorted(positions), "Output order does not match input order"


def test_researcher_20_concurrent_stable_under_load():
    """20 concurrent tasks complete in well under sequential time."""
    questions = _make_questions(20)
    per_task_sleep = 0.05  # 0.05 s × 20 = 1.0 s sequential

    def slow_search(query):
        time.sleep(per_task_sleep)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=slow_search), _patch_call_llm():
        start = time.perf_counter()
        state = researcher_node(_base_state(questions))
        duration = time.perf_counter() - start

    # ThreadPoolExecutor caps at 8 workers, so expect ~ceil(20/8)*0.05 = 0.15 s.
    # Allow 0.6 s to keep the test stable on slow CI.
    assert duration < 0.6, f"Took {duration:.2f}s — concurrency may not be working"
    assert state["research_notes"]


def test_researcher_50_concurrent_stable_under_load():
    """50 concurrent tasks complete in well under sequential time."""
    questions = _make_questions(50)
    per_task_sleep = 0.02  # 0.02 s × 50 = 1.0 s sequential

    def slow_search(query):
        time.sleep(per_task_sleep)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=slow_search), _patch_call_llm():
        start = time.perf_counter()
        state = researcher_node(_base_state(questions))
        duration = time.perf_counter() - start

    # 8 workers × batches: ceil(50/8)*0.02 = 0.14 s. Allow 0.6 s for CI headroom.
    assert duration < 0.6, f"Took {duration:.2f}s — concurrency may not be working"
    assert state["research_notes"]


def test_researcher_large_workload_partial_failures_dont_drop_successes():
    """With 30 questions where every 5th fails, the rest still appear in notes."""
    questions = _make_questions(30)

    def selective_fail(query):
        idx = int(query.split("_")[1])
        if idx % 5 == 0:
            raise RuntimeError(f"simulated failure for {query}")
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=selective_fail), _patch_call_llm():
        state = researcher_node(_base_state(questions))

    notes = state["research_notes"]
    for i, q in enumerate(questions):
        assert f"Sub-question: {q}" in notes, f"Entry missing for {q}"
        if i % 5 == 0:
            assert "Search failed" in notes or f"question_{i}" in notes