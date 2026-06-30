from prometheus_client import Counter, Gauge, Histogram

EVAL_COUNTER = Counter(
    "openevals_evaluations_total", "Total evaluations processed", ["status"]
)
EVAL_DURATION = Histogram(
    "openevals_evaluation_duration_seconds", "End-to-end evaluation duration",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)
JUDGE_CALLS = Counter(
    "openevals_judge_calls_total", "Judge model API calls", ["model", "status"]
)
JUDGE_LATENCY = Histogram(
    "openevals_judge_latency_seconds", "Judge model response latency", ["model"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)
QUEUE_DEPTH = Gauge("openevals_pipeline_queue_depth", "Current evaluation queue depth")
THROUGHPUT_GAUGE = Gauge("openevals_pipeline_throughput", "Evaluations per second (60s window)")
API_REQUESTS = Counter(
    "openevals_api_requests_total", "API HTTP requests", ["endpoint", "method", "status_code"]
)
API_LATENCY = Histogram(
    "openevals_api_latency_seconds", "API endpoint response latency", ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5],
)
