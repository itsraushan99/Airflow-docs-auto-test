from __future__ import annotations

import sys
from pathlib import Path

import pendulum
from airflow.decorators import dag, task


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))


@dag(
    dag_id="generate_dag_documentation",
    description="Generate markdown documentation for all Airflow DAGs in this project.",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 8, 16, tz="Asia/Calcutta"),
    catchup=False,
    tags=["documentation", "automation"],
)
def generate_dag_documentation():
    @task
    def build_documentation() -> str:
        from generate_dag_docs import generate_documentation

        output_dir = PROJECT_ROOT / "Documentation"
        generate_documentation(PROJECT_ROOT / "dags", output_dir)
        return str(output_dir)

    @task
    def notify_completion(output_dir: str) -> None:
        from pathlib import Path

        doc_files = sorted(Path(output_dir).glob("*_docs.md"))
        if not doc_files:
            print("No documentation files were generated.")
            return
        print(f"Documentation generation complete. {len(doc_files)} file(s) written:")
        for doc_file in doc_files:
            print(f"  - {doc_file.name}")

    notify_completion(build_documentation())


generate_dag_documentation()
