import unittest

from api.index import app
from api.health import app as health_app


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_health_endpoint(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")
        self.assertEqual(response.json["service"], "timeattack-api")
        self.assertEqual(response.json["runtime"], "python")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertTrue(response.headers["X-Request-ID"])

    def test_not_found_uses_common_error_shape(self) -> None:
        response = self.client.get("/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"]["code"], 404)
        self.assertTrue(response.json["error"]["request_id"])

    def test_vercel_health_entrypoint_exports_the_same_app(self) -> None:
        self.assertIs(health_app, app)


if __name__ == "__main__":
    unittest.main()
