import os
import tempfile
import unittest
from pathlib import Path

from poc.step0_probe import ProbeError, load_env_file, select_judge0_language, validate_pseudocode_evaluation


class EnvironmentFileTests(unittest.TestCase):
    def test_loads_values_without_overwriting_process_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("STEP0_NEW=value\nSTEP0_EXISTING=from-file\n", encoding="utf-8")
            os.environ["STEP0_EXISTING"] = "from-process"
            os.environ.pop("STEP0_NEW", None)
            try:
                load_env_file(path)
                self.assertEqual(os.environ["STEP0_NEW"], "value")
                self.assertEqual(os.environ["STEP0_EXISTING"], "from-process")
            finally:
                os.environ.pop("STEP0_NEW", None)
                os.environ.pop("STEP0_EXISTING", None)


class Judge0LanguageSelectionTests(unittest.TestCase):
    def test_selects_latest_supported_versions(self) -> None:
        languages = [
            {"id": 70, "name": "Python (2.7.17)"},
            {"id": 71, "name": "Python (3.8.1)"},
            {"id": 100, "name": "Python (3.12.5)"},
            {"id": 54, "name": "C++ (GCC 9.2.0)"},
            {"id": 105, "name": "C++ (GCC 14.1.0)"},
        ]

        self.assertEqual(select_judge0_language(languages, "python")["id"], 100)
        self.assertEqual(select_judge0_language(languages, "cpp")["id"], 105)


class HuggingFaceSchemaTests(unittest.TestCase):
    def test_accepts_expected_schema(self) -> None:
        value = {"passed": True, "score": 95, "feedback": "Good flow.", "missing_steps": []}
        self.assertEqual(validate_pseudocode_evaluation(value), value)

    def test_rejects_extra_fields(self) -> None:
        with self.assertRaises(ProbeError):
            validate_pseudocode_evaluation(
                {"passed": True, "score": 95, "feedback": "Good.", "missing_steps": [], "extra": 1}
            )

    def test_rejects_boolean_score(self) -> None:
        with self.assertRaises(ProbeError):
            validate_pseudocode_evaluation(
                {"passed": True, "score": True, "feedback": "Good.", "missing_steps": []}
            )


if __name__ == "__main__":
    unittest.main()
