from django.test import TestCase
from django.urls import reverse


class HealthEndpointTests(TestCase):

    def test_health_liveness(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_health_readiness(self):
        response = self.client.get('/api/health/ready/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['database'])
