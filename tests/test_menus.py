import unittest
from unittest.mock import Mock

from spoppy import menus


class OptionTests(unittest.TestCase):

    def setUp(self):
        self.dct = {
            '1': menus.MenuValue('A', Mock()),
            '2': menus.MenuValue('B', Mock()),
            '3': menus.MenuValue('C', Mock()),
            's': menus.MenuValue('Search', Mock()),
            'kk': menus.MenuValue('þþ', Mock()),
            'ko': menus.MenuValue('þ', Mock()),
            'q': menus.MenuValue('o', Mock()),
            'o': menus.MenuValue('q', Mock()),
        }
        self.op = menus.Options(self.dct)

    def test_options_filter_empty(self):
        self.assertEqual(self.op, self.op.filter(''))

    def test_filter_by_key(self):
        tc = self.op.filter('1')
        self.assertEqual(len(tc), 1)
        self.assertIn('1', tc)
        tc = self.op.filter('k')
        self.assertEqual(len(tc), 2)
        self.assertIn('kk', tc)
        self.assertIn('ko', tc)
        tc = self.op.filter('s')
        self.assertEqual(len(tc), 1)
        self.assertIn('s', tc)

    def test_filter_by_name(self):
        tc = self.op.filter('þ')
        self.assertEqual(len(tc), 2)
        self.assertIn('kk', tc)
        self.assertIn('ko', tc)
        tc = self.op.filter('þþ')
        self.assertEqual(len(tc), 1)
        self.assertIn('kk', tc)
        tc = self.op.filter('Sea')
        self.assertEqual(len(tc), 1)
        self.assertIn('s', tc)

    def test_filter_is_case_insensitive(self):
        self.assertEqual(self.op.filter('Search'), self.op.filter('search'))

    def test_filter_returns_empty_if_no_match(self):
        self.assertEqual(len(self.op.filter('asdf')), 0)

    def test_get_possibilities_from_name_and_key(self):
        tc = self.op.get_possibilities('q')
        self.assertEqual(len(tc), 2)
        self.assertEqual(sorted(tc), sorted(['q', 'o']))

    def test_possibility_not_duplicated(self):
        tc = self.op.get_possibilities('s')
        self.assertEqual(len(tc), 1)
        self.assertIn('s', tc)

    def test_possiblities_with_spaces(self):
        op = menus.Options({
            '    a': menus.MenuValue('þ', Mock()),
            'b    ': menus.MenuValue('þ', Mock()),
            '    c    ': menus.MenuValue('þ', Mock()),
        })
        for key in 'a', 'b', 'c':
            tc = op.get_possibilities(key)
            self.assertEqual(len(tc), 1)
            self.assertNotEqual(tc, [key])
            self.assertIn(key, tc[0])

    def test_possibilities_only_start_of_words(self):
        # Also testing for case insesitivity
        op = menus.Options({
            'match1': menus.MenuValue('Sindri', Mock()),
            'not1': menus.MenuValue('iSindri', Mock()),
            'match2': menus.MenuValue('This is sindri', Mock()),
            'not2': menus.MenuValue('This is notSindri', Mock()),
        })
        possibilities = op.get_possibilities('Sindri')
        self.assertEqual(sorted(possibilities), sorted(['match1', 'match2']))

    def test_matches_by_correct_key(self):
        op = menus.Options({
            'k': menus.MenuValue('1', Mock()),
            'kk': menus.MenuValue('2', Mock()),
            'kkk': menus.MenuValue('3', Mock()),
        })
        best = op.match_best_or_none('k')
        self.assertEqual(best.name, '1')
        best = op.match_best_or_none('kk')
        self.assertEqual(best.name, '2')
        best = op.match_best_or_none('kkk')
        self.assertEqual(best.name, '3')

    def test_matches_by_correct_padded_key(self):
        op = menus.Options({
            '    a': menus.MenuValue('1', Mock()),
            'b    ': menus.MenuValue('2', Mock()),
            '    c    ': menus.MenuValue('3', Mock()),
            ' s i ': menus.MenuValue('4', Mock()),
        })
        best = op.match_best_or_none('a')
        self.assertEqual(best.name, '1')
        best = op.match_best_or_none('b')
        self.assertEqual(best.name, '2')
        best = op.match_best_or_none('c')
        self.assertEqual(best.name, '3')
        best = op.match_best_or_none('si')
        self.assertEqual(best.name, '4')

    def test_check_unique_keys(self):
        with self.assertRaises(TypeError):
            menus.Options({
                'a': menus.MenuValue('þ', Mock()),
                ' a': menus.MenuValue('k', Mock())
            })
        with self.assertRaises(TypeError):
            self.op['   1'] = menus.MenuValue('1', Mock())
