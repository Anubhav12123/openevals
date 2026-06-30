from __future__ import annotations

import importlib as _importlib
from typing import Dict, Type

from openevals.metrics.base import BaseMetric

_BUILTIN: Dict[str, str] = {
    "faithfulness": "openevals.metrics.faithfulness:FaithfulnessMetric",
    "relevance": "openevals.metrics.relevance:RelevanceMetric",
    "hallucination": "openevals.metrics.hallucination:HallucinationMetric",
    "toxicity": "openevals.metrics.toxicity:ToxicityMetric",
    "latency": "openevals.metrics.latency:LatencyMetric",
    "coherence": "openevals.metrics.coherence:CoherenceMetric",
    "context_precision": "openevals.metrics.context_precision:ContextPrecisionMetric",
    "context_recall": "openevals.metrics.context_recall:ContextRecallMetric",
    "answer_similarity": "openevals.metrics.answer_similarity:AnswerSimilarityMetric",
    "conciseness": "openevals.metrics.conciseness:ConcisenessMetric",
    "citation_accuracy": "openevals.metrics.citation_accuracy:CitationAccuracyMetric",
    "bias_detection": "openevals.metrics.bias_detection:BiasDetectionMetric",
}


class MetricRegistry:
    """Plugin-based metric registry using Python entry points."""

    def get(self, name: str) -> BaseMetric:
        if name in _BUILTIN:
            module_path, class_name = _BUILTIN[name].rsplit(":", 1)
            module = _importlib.import_module(module_path)
            cls: Type[BaseMetric] = getattr(module, class_name)
            return cls()
        # Check entry points for third-party plugins
        try:
            import importlib.metadata

            for ep in importlib.metadata.entry_points(group="openevals.metrics"):
                if ep.name == name:
                    cls = ep.load()
                    return cls()
        except Exception:
            pass
        raise ValueError(
            f"Unknown metric: '{name}'. Available: {list(_BUILTIN.keys())}"
        )

    def list_available(self) -> list[str]:
        names = list(_BUILTIN.keys())
        try:
            import importlib.metadata

            for ep in importlib.metadata.entry_points(group="openevals.metrics"):
                if ep.name not in names:
                    names.append(ep.name)
        except Exception:
            pass
        return names
