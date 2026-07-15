from modules.planning.context import build_generation_context, select_generation_mode
import unittest


class PlanningContextTests(unittest.TestCase):
    def test_explicit_single_task_language_wins(self) -> None:
        mode, reason = select_generation_mode("只要一个任务，不要拆分")
        self.assertEqual(mode, "single_task")
        self.assertEqual(reason, "explicit_single_keyword")

    def test_complex_goal_defaults_to_workflow(self) -> None:
        mode, reason = select_generation_mode("帮我规划一个从零学习 FastAPI 并完成项目的路径")
        self.assertEqual(mode, "workflow_chain")
        self.assertIn(reason, {"workflow_keyword", "length_threshold"})

    def test_profile_context_clamps_preferences_and_exposes_capabilities(self) -> None:
        context = build_generation_context(
            {"specialization": "后端", "learning_goal": "完成产品"},
            [{
                "attr_id": "focus",
                "attr_name": "专注",
                "attr_value": 25,
                "max_value": 100,
                "description": "持续工作",
            }],
            {"response_style": "简洁", "response_temperature": 140},
        )
        self.assertIn("生成温度偏好(0~100): 100", context)
        self.assertIn("专注 (id=focus, value=25/100, weakness=0.75", context)


if __name__ == "__main__":
    unittest.main()
