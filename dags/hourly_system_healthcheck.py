from airflow.sdk import dag, task
from pendulum import datetime


@dag(
    start_date=datetime(2026, 8, 1),
    schedule="@hourly",
    catchup=False,
    default_args={"owner": "platform-team", "retries": 1},
    tags=["example", "monitoring", "hourly"],
)
def hourly_system_healthcheck():
    """Check local component health metrics and fail if any component is unhealthy."""

    @task
    def collect_component_status() -> list[dict]:
        return [
            {"component": "scheduler", "status": "healthy", "latency_ms": 42},
            {"component": "api_server", "status": "healthy", "latency_ms": 55},
            {"component": "triggerer", "status": "healthy", "latency_ms": 31},
        ]

    @task
    def evaluate_health(statuses: list[dict]) -> dict:
        unhealthy = [item for item in statuses if item["status"] != "healthy"]
        slow = [item for item in statuses if item["latency_ms"] > 500]
        return {
            "healthy": not unhealthy and not slow,
            "checked_components": len(statuses),
            "unhealthy_components": unhealthy,
            "slow_components": slow,
        }

    @task
    def log_health_report(report: dict) -> None:
        if not report["healthy"]:
            raise ValueError(f"Health check failed: {report}")
        print(f"All {report['checked_components']} components are healthy.")

    log_health_report(evaluate_health(collect_component_status()))


hourly_system_healthcheck()
