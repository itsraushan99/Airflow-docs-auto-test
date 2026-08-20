from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return html.escape(text.replace("\n", " ").replace("|", "\\|"), quote=False)


def format_datetime(value: Any) -> str:
    if value is None:
        return "Not set"
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def format_schedule(dag: Any) -> str:
    timetable = getattr(dag, "timetable", None)
    if timetable is not None:
        summary = getattr(timetable, "summary", None)
        if summary:
            return str(summary)

    schedule_interval = getattr(dag, "schedule_interval", None)
    if schedule_interval is not None:
        return str(schedule_interval)

    schedule = getattr(dag, "schedule", None)
    if schedule is not None:
        return str(schedule)

    return "Not scheduled"


def format_task_dependencies(task: Any) -> str:
    downstream_task_ids = sorted(getattr(task, "downstream_task_ids", []))
    if not downstream_task_ids:
        return "None"
    return ", ".join(f"`{task_id}`" for task_id in downstream_task_ids)


# Maps internal operator class names to the Airflow UI display label
_OPERATOR_UI_LABELS: dict[str, str] = {
    "_PythonDecoratedOperator": "@task",
    "_BranchPythonDecoratedOperator": "@task.branch",
    "_ShortCircuitDecoratedOperator": "@task.short_circuit",
    "_SensorDecoratedOperator": "@task.sensor",
    "_PythonVirtualenvDecoratedOperator": "@task.virtualenv",
    "_BranchPythonVirtualenvDecoratedOperator": "@task.branch_virtualenv",
    "_ExternalPythonDecoratedOperator": "@task.external_python",
    "_BranchExternalPythonDecoratedOperator": "@task.branch_external_python",
}


def operator_ui_label(operator_class_name: str) -> str:
    """Return the Airflow UI display label for an operator class name."""
    return _OPERATOR_UI_LABELS.get(operator_class_name, operator_class_name)


def mermaid_label(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", "<br/>").replace("|", "&#124;").replace('"', "#quot;")


def collect_dag_details(dag: Any) -> dict[str, Any]:
    tasks = sorted(getattr(dag, "tasks", []), key=lambda item: item.task_id)
    return {
        "dag_id": dag.dag_id,
        "description": getattr(dag, "description", None) or "No description provided.",
        "schedule": format_schedule(dag),
        "start_date": format_datetime(getattr(dag, "start_date", None)),
        "end_date": format_datetime(getattr(dag, "end_date", None)),
        "catchup": getattr(dag, "catchup", None),
        "max_active_runs": getattr(dag, "max_active_runs", None),
        "tags": sorted(getattr(dag, "tags", []) or []),
        "owner": getattr(dag, "owner", None) or "Not set",
        "task_count": len(tasks),
        "tasks": [
            {
                "task_id": task.task_id,
                "operator": task.__class__.__name__,
                "owner": getattr(task, "owner", None) or "Not set",
                "retries": getattr(task, "retries", None),
                "trigger_rule": getattr(task, "trigger_rule", None),
                "pool": getattr(task, "pool", None) or "default_pool",
                "downstream": format_task_dependencies(task),
                "downstream_task_ids": sorted(getattr(task, "downstream_task_ids", [])),
                "doc": getattr(task, "doc_md", None) or getattr(task, "doc", None) or "",
            }
            for task in tasks
        ],
    }


def load_dagbag(dags_dir: Path) -> Any:
    from airflow.models.dagbag import DagBag

    return DagBag(dag_folder=str(dags_dir), include_examples=False, safe_mode=False)


def render_import_errors(import_errors: dict[str, str]) -> list[str]:
    if not import_errors:
        return []
    lines = ["## Import Errors", "", "| File | Error |", "| --- | --- |"]
    for file_path, error in sorted(import_errors.items()):
        lines.append(f"| `{markdown_escape(file_path)}` | `{markdown_escape(error)}` |")
    lines.append("")
    return lines


def render_task_graph(dag_info: dict[str, Any]) -> list[str]:
    tasks = dag_info["tasks"]
    if not tasks:
        return ["### Task Graph", "", "No tasks found.", ""]

    node_ids = {task["task_id"]: f"task_{index}" for index, task in enumerate(tasks, start=1)}
    lines = ["### Task Graph", "", "```mermaid", "flowchart TD"]

    for task in tasks:
        label = f"{task['task_id']}<br/>{operator_ui_label(task['operator'])}"
        lines.append(f"    {node_ids[task['task_id']]}[\"{mermaid_label(label)}\"]")

    for task in tasks:
        for downstream_task_id in task["downstream_task_ids"]:
            downstream_node_id = node_ids.get(downstream_task_id)
            if downstream_node_id is not None:
                lines.append(f"    {node_ids[task['task_id']]} --> {downstream_node_id}")

    lines.extend(["```", ""])
    return lines


def render_dag_section(dag_info: dict[str, Any]) -> list[str]:
    tags = ", ".join(f"`{tag}`" for tag in dag_info["tags"]) or "None"
    lines = [
        f"## `{markdown_escape(dag_info['dag_id'])}`",
        "",
        str(dag_info["description"]),
        "",
        "| Property | Value |",
        "| --- | --- |",
        f"| Schedule | `{markdown_escape(dag_info['schedule'])}` |",
        f"| Start date | `{markdown_escape(dag_info['start_date'])}` |",
        f"| End date | `{markdown_escape(dag_info['end_date'])}` |",
        f"| Catchup | `{markdown_escape(dag_info['catchup'])}` |",
        f"| Max active runs | `{markdown_escape(dag_info['max_active_runs'])}` |",
        f"| Owner | `{markdown_escape(dag_info['owner'])}` |",
        f"| Tags | {tags} |",
        f"| Task count | `{dag_info['task_count']}` |",
        "",
    ]

    lines.extend(render_task_graph(dag_info))

    if dag_info["tasks"]:
        lines.extend(
            [
                "### Tasks",
                "",
                "| Task ID | Operator | Owner | Retries | Trigger Rule | Pool | Downstream |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for task in dag_info["tasks"]:
            lines.append(
                "| "
                f"`{markdown_escape(task['task_id'])}` | "
                f"`{markdown_escape(task['operator'])}` | "
                f"`{markdown_escape(task['owner'])}` | "
                f"`{markdown_escape(task['retries'])}` | "
                f"`{markdown_escape(task['trigger_rule'])}` | "
                f"`{markdown_escape(task['pool'])}` | "
                f"{task['downstream']} |"
            )
        lines.append("")
    else:
        lines.extend(["### Tasks", "", "No tasks found.", ""])

    documented_tasks = [task for task in dag_info["tasks"] if task["doc"]]
    if documented_tasks:
        lines.extend(["### Task Documentation", ""])
        for task in documented_tasks:
            lines.extend([f"#### `{markdown_escape(task['task_id'])}`", "", str(task["doc"]), ""])

    return lines


def render_dag_doc(dag_info: dict[str, Any], import_errors: dict[str, str], source_file: Path) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        f"# DAG Documentation — `{markdown_escape(dag_info['dag_id'])}`",
        "",
        f"Generated at `{generated_at}` from `{markdown_escape(source_file)}`.",
        "",
        *render_import_errors(import_errors),
        *render_dag_section(dag_info),
    ]
    return "\n".join(lines).rstrip() + "\n"


def doc_output_path(output_dir: Path, dag_file: Path) -> Path:
    return output_dir / f"{dag_file.stem}_docs.md"


def generate_dag_file_documentation(
    dag_file: Path,
    output_dir: Path,
    json_output_path: Path | None = None,
) -> Path:
    from airflow.models.dagbag import DagBag

    dagbag = DagBag(dag_folder=str(dag_file.parent), include_examples=False, safe_mode=False)

    # Only keep DAGs that originate from this specific file
    dags = [
        collect_dag_details(dag)
        for dag in sorted(dagbag.dags.values(), key=lambda d: d.dag_id)
        if Path(dag.fileloc).resolve() == dag_file.resolve()
    ]
    import_errors = {
        str(path): str(error)
        for path, error in dagbag.import_errors.items()
        if Path(path).resolve() == dag_file.resolve()
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = doc_output_path(output_dir, dag_file)

    if not dags and not import_errors:
        print(f"No DAGs found in {dag_file}, skipping.")
        return out_path

    # One file may contain multiple DAGs — write one combined doc per source file
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dag_ids = ", ".join(f"`{d['dag_id']}`" for d in dags)
    lines: list[str] = [
        f"# DAG Documentation — {dag_ids}",
        "",
        f"Generated at `{generated_at}` from `{markdown_escape(dag_file)}`.",
        "",
        *render_import_errors(import_errors),
    ]
    for dag_info in dags:
        lines.extend(render_dag_section(dag_info))

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    if json_output_path is not None:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        json_output_path.write_text(
            json.dumps({"dags": dags, "import_errors": import_errors}, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    return out_path


def generate_documentation(dags_dir: Path, output_dir: Path, json_output_path: Path | None = None) -> None:
    """Generate one doc file per DAG source file in dags_dir."""
    dag_files = sorted(dags_dir.glob("*.py"))
    for dag_file in dag_files:
        out = generate_dag_file_documentation(dag_file, output_dir, json_output_path)
        print(f"Wrote documentation to {out}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate markdown documentation for Airflow DAGs.")
    parser.add_argument("--dags-dir", default="dags", type=Path, help="Directory containing Airflow DAG files.")
    parser.add_argument(
        "--output-dir",
        default=Path("Documentation"),
        type=Path,
        help="Directory to write per-DAG documentation files.",
    )
    parser.add_argument(
        "--dag-file",
        type=Path,
        default=None,
        help="Process a single DAG file only (for targeted regeneration).",
    )
    parser.add_argument("--json-output", type=Path, help="Optional JSON summary file to write.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dag_file is not None:
        out = generate_dag_file_documentation(args.dag_file, args.output_dir, args.json_output)
        print(f"Wrote DAG documentation to {out}")
    else:
        generate_documentation(args.dags_dir, args.output_dir, args.json_output)


if __name__ == "__main__":
    main()
