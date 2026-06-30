import pytest
from openevals.pipeline.batcher import Batcher
from openevals.types import EvaluationRequest


def _make(n: int):
    return [EvaluationRequest(prompt=f"p{i}", response=f"r{i}") for i in range(n)]


def test_splits_into_correct_batches():
    batcher = Batcher(batch_size=10)
    batches = batcher.create_batches(_make(25))
    assert len(batches) == 3
    assert [len(b) for b in batches] == [10, 10, 5]


def test_single_batch_when_under_limit():
    batches = Batcher(batch_size=50).create_batches(_make(10))
    assert len(batches) == 1
    assert len(batches[0]) == 10


def test_empty_input():
    assert Batcher().create_batches([]) == []


def test_exact_multiple():
    batches = Batcher(batch_size=5).create_batches(_make(15))
    assert len(batches) == 3
    assert all(len(b) == 5 for b in batches)
