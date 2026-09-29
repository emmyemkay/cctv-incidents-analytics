from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_liveness(self):
        response = self.client.get("/health/live/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertIn("X-Request-ID", response)

    def test_readiness(self):
        response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"]["database"]["status"], "ok")
