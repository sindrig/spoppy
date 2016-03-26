import unittest
from spoppy import util


class TestPlayer(unittest.TestCase):

    def test_get_duration_from_s(self):
        test_cases = {
            0: '00:00',
            9999999999999: '59:59',
            59: '00:59',
            60: '01:00',
            157: '02:37'
        }
        for seconds, expected in test_cases.items():
            self.assertEqual(
                util.get_duration_from_s(seconds), expected
            )

    def test_get_duration_from_s_raises(self):
        with self.assertRaises(TypeError):
            util.get_duration_from_s(None)
        with self.assertRaises(TypeError):
            util.get_duration_from_s(-1)
        with self.assertRaises(TypeError):
            util.get_duration_from_s('01:57')
