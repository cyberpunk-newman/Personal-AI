import unittest


class CompatibilityTests(unittest.TestCase):
    def test_legacy_imports_resolve_to_new_modules(self):
        from agent.ast_parser import extract_functions
        from agent.llm import ask_llm
        from agent.rag import build_index, embed
        from agent.retriever import retrieve

        self.assertTrue(callable(extract_functions))
        self.assertTrue(callable(ask_llm))
        self.assertTrue(callable(build_index))
        self.assertTrue(callable(embed))
        self.assertTrue(callable(retrieve))

    def test_app_exposes_main_entry_point(self):
        from app import main

        self.assertTrue(callable(main))

    def test_main_uses_workflow_without_direct_retriever_or_llm_dependencies(self):
        import main

        self.assertTrue(callable(main.run_workflow))
        self.assertFalse(hasattr(main, "retrieve"))
        self.assertFalse(hasattr(main, "ask_llm"))


if __name__ == "__main__":
    unittest.main()
