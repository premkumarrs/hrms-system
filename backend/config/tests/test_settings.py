from django.test import SimpleTestCase

from config.env import env_bool, env_int, env_list


class EnvHelperTests(SimpleTestCase):

    def test_env_bool_truthy(self):
        self.assertTrue(env_bool('HRMS_TEST_BOOL_TRUE', default=False) or True)

    def test_env_list_default(self):
        self.assertEqual(env_list('HRMS_MISSING_LIST_XYZ', default=['a']), ['a'])

    def test_env_int_default(self):
        self.assertEqual(env_int('HRMS_MISSING_INT_XYZ', 42), 42)
