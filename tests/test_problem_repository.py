import unittest
from unittest.mock import patch

from api.problem_service import (
    list_problem_summaries,
    load_manifest,
    load_public_problem,
)
from api.problem_repository import database_url


class PersistentProblemBankReadTest(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "",
            "POSTGRES_URL": (
                "postgresql://postgres:secret@db.example.test:6543/postgres"
                "?sslmode=require&supa=base-pooler.x"
            ),
        },
    )
    def test_vercel_supabase_metadata_is_removed_from_connection_url(self) -> None:
        self.assertEqual(
            database_url(),
            (
                "postgresql://postgres:secret@db.example.test:6543/postgres"
                "?sslmode=require"
            ),
        )

    @patch("api.problem_service.load_database_manifest")
    @patch("api.problem_service.database_enabled", return_value=True)
    def test_database_manifest_reads_are_not_process_cached(
        self, _database_enabled_mock, load_database_manifest_mock
    ) -> None:
        load_database_manifest_mock.return_value = {
            "schema_version": "1.0.0",
            "bank_version": 7,
            "problems": [],
        }

        self.assertEqual(load_manifest()["bank_version"], 7)
        self.assertEqual(load_manifest()["bank_version"], 7)
        self.assertEqual(load_database_manifest_mock.call_count, 2)

    @patch("api.problem_service.load_database_public_problem")
    @patch("api.problem_service.database_enabled", return_value=True)
    def test_public_problem_is_loaded_from_database_when_configured(
        self, _database_enabled_mock, load_database_public_problem_mock
    ) -> None:
        load_database_public_problem_mock.return_value = {
            "id": "persistent-problem",
            "title": "Persistent problem",
        }

        problem = load_public_problem("persistent-problem")

        self.assertEqual(problem["title"], "Persistent problem")
        load_database_public_problem_mock.assert_called_once_with(
            "persistent-problem"
        )

    @patch("api.problem_service.list_database_problem_summaries")
    @patch("api.problem_service.database_enabled", return_value=True)
    def test_database_summaries_use_one_repository_query(
        self, _database_enabled_mock, list_database_problem_summaries_mock
    ) -> None:
        list_database_problem_summaries_mock.return_value = [
            {
                "id": "persistent-problem",
                "title": "Persistent problem",
                "difficulty": "hard",
            }
        ]

        summaries = list_problem_summaries("hard")

        self.assertEqual(summaries[0]["id"], "persistent-problem")
        list_database_problem_summaries_mock.assert_called_once_with("hard")


if __name__ == "__main__":
    unittest.main()
