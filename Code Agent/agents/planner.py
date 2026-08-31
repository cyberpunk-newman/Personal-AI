from dataclasses import dataclass
from enum import Enum
from typing import Any


class TaskType(str, Enum):
    """Task types supported by the Phase 3 analysis workflow."""

    CODE_SEARCH = "code_search"
    CODE_ANALYSIS = "code_analysis"
    ANSWER_GENERATION = "answer_generation"


@dataclass(frozen=True)
class PlanTask:
    """One ordered, executable task in an analysis plan."""

    id: str
    type: TaskType
    description: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Task id must not be empty.")
        if not isinstance(self.type, TaskType):
            raise ValueError("Task type must be a supported TaskType.")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Task description must not be empty.")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PlanTask":
        """Create a task from its strict external representation."""
        if not isinstance(value, dict) or set(value) != {"id", "type", "description"}:
            raise ValueError("Task must contain exactly id, type, and description.")
        try:
            task_type = TaskType(value["type"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unsupported task type: {value.get('type')!r}.") from exc
        return cls(
            id=value["id"],
            type=task_type,
            description=value["description"],
        )

    def to_dict(self) -> dict[str, str]:
        """Return the stable external representation of this task."""
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
        }


@dataclass(frozen=True)
class TaskPlan:
    """Validated plan consumed by the workflow orchestrator."""

    goal: str
    tasks: tuple[PlanTask, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise ValueError("Plan goal must not be empty.")
        if not isinstance(self.tasks, tuple) or not self.tasks:
            raise ValueError("Plan must contain at least one task.")
        if any(not isinstance(task, PlanTask) for task in self.tasks):
            raise ValueError("Plan tasks must be PlanTask instances.")

        task_ids = [task.id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task ids must be unique.")

        expected_types = [
            TaskType.CODE_SEARCH,
            TaskType.CODE_ANALYSIS,
            TaskType.ANSWER_GENERATION,
        ]
        actual_types = [task.type for task in self.tasks]
        if actual_types != expected_types:
            raise ValueError(
                "Plan tasks must follow code_search, code_analysis, "
                "answer_generation order."
            )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TaskPlan":
        """Create and validate a plan from its strict external representation."""
        if not isinstance(value, dict) or set(value) != {"goal", "tasks"}:
            raise ValueError("Plan must contain exactly goal and tasks.")
        if not isinstance(value["tasks"], list):
            raise ValueError("Plan tasks must be a list.")
        return cls(
            goal=value["goal"],
            tasks=tuple(PlanTask.from_dict(task) for task in value["tasks"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the stable external representation of this plan."""
        return {
            "goal": self.goal,
            "tasks": [task.to_dict() for task in self.tasks],
        }


def validate_task_plan(plan: Any) -> TaskPlan:
    """Reject objects that do not satisfy the task-plan contract."""
    if not isinstance(plan, TaskPlan):
        raise ValueError("Planner must return a TaskPlan.")
    return plan


class Planner:
    """Build a plan without executing retrieval or analysis work."""

    def plan(self, query: str) -> TaskPlan:
        """Decompose a question into the current workflow's ordered tasks."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Question must not be empty.")

        goal = query.strip()
        return TaskPlan(
            goal=goal,
            tasks=(
                PlanTask(
                    id="task_1",
                    type=TaskType.CODE_SEARCH,
                    description=f"Find code relevant to: {goal}",
                ),
                PlanTask(
                    id="task_2",
                    type=TaskType.CODE_ANALYSIS,
                    description=f"Analyze the retrieved code for: {goal}",
                ),
                PlanTask(
                    id="task_3",
                    type=TaskType.ANSWER_GENERATION,
                    description=f"Generate the final answer for: {goal}",
                ),
            ),
        )


def plan_question(query: str) -> TaskPlan:
    """Public Planner entry point."""
    return Planner().plan(query)
