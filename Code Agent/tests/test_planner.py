import unittest

from agents.planner import Planner, TaskPlan, TaskType


class PlannerTests(unittest.TestCase):
    def test_builds_stable_ordered_plan_without_executing_tasks(self):
        plan = Planner().plan("  Why does login fail?  ")

        self.assertEqual(plan.goal, "Why does login fail?")
        self.assertEqual(
            [task.type for task in plan.tasks],
            [
                TaskType.CODE_SEARCH,
                TaskType.CODE_ANALYSIS,
                TaskType.ANSWER_GENERATION,
            ],
        )
        self.assertEqual([task.id for task in plan.tasks], ["task_1", "task_2", "task_3"])
        self.assertEqual(
            set(plan.to_dict()),
            {"goal", "tasks"},
        )

    def test_plan_round_trip_preserves_external_structure(self):
        serialized = Planner().plan("question").to_dict()

        restored = TaskPlan.from_dict(serialized)

        self.assertEqual(restored.to_dict(), serialized)

    def test_empty_question_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            Planner().plan("   ")

    def test_missing_plan_fields_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly goal and tasks"):
            TaskPlan.from_dict({"goal": "question"})

    def test_unknown_task_type_is_rejected(self):
        data = Planner().plan("question").to_dict()
        data["tasks"][0]["type"] = "dependency_analysis"

        with self.assertRaisesRegex(ValueError, "Unsupported task type"):
            TaskPlan.from_dict(data)

    def test_duplicate_task_ids_are_rejected(self):
        data = Planner().plan("question").to_dict()
        data["tasks"][1]["id"] = "task_1"

        with self.assertRaisesRegex(ValueError, "unique"):
            TaskPlan.from_dict(data)

    def test_out_of_order_tasks_are_rejected(self):
        data = Planner().plan("question").to_dict()
        data["tasks"][0], data["tasks"][1] = data["tasks"][1], data["tasks"][0]

        with self.assertRaisesRegex(ValueError, "must follow"):
            TaskPlan.from_dict(data)


if __name__ == "__main__":
    unittest.main()
