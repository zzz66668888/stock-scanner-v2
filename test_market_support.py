import os
import unittest
from unittest.mock import patch

os.environ['TUSHARE_SKIP_INIT'] = '1'

import stock_scanner as scanner


class MarketSupportTests(unittest.TestCase):
    def test_market_code_mapping(self):
        cases = [
            ('600000', 'A', 'SH', '600000.SH', '1.600000'),
            ('300750', 'A', 'SZ', '300750.SZ', '0.300750'),
            ('920083', 'BJ', 'BJ', '920083.BJ', '0.920083'),
            ('873757', 'NEEQ', 'BJ', '873757.BJ', '0.873757'),
        ]
        for code, market, exchange, ts_code, secid in cases:
            with self.subTest(code=code, market=market):
                self.assertEqual(scanner.exchange_for_code(code, market), exchange)
                self.assertEqual(scanner.tushare_code(code, market), ts_code)
                self.assertEqual(scanner.eastmoney_secid(code, market), secid)

    def test_limit_thresholds(self):
        self.assertEqual(scanner.limit_up_threshold('A', '000001'), 9.5)
        self.assertEqual(scanner.limit_up_threshold('A', '300750'), 19.5)
        self.assertEqual(scanner.limit_up_threshold('A', '688981'), 19.5)
        self.assertEqual(scanner.limit_up_threshold('BJ', '920083'), 29.5)
        self.assertEqual(scanner.limit_up_threshold('NEEQ', '873757'), 49.5)

    @patch.object(scanner, 'analyze_stock')
    @patch.object(scanner, 'fetch_bj_stock_list')
    @patch.object(scanner, 'fetch_a_stock_list')
    def test_scan_uses_one_round_robin_page(self, fetch_a, fetch_bj, analyze):
        fetch_a.return_value = [
            {'code': '000001', 'name': 'A1', 'market': 'A'},
            {'code': '000002', 'name': 'A2', 'market': 'A'},
            {'code': '000003', 'name': 'A3', 'market': 'A'},
        ]
        fetch_bj.return_value = [
            {'code': '920001', 'name': 'B1', 'market': 'BJ'},
            {'code': '920002', 'name': 'B2', 'market': 'BJ'},
        ]
        analyze.side_effect = lambda stock, market, patterns: {
            'code': stock['code'], 'market': market,
            'patterns': [{'strength': 1}],
        }

        response = scanner.app.test_client().post('/api/scan', json={
            'markets': ['A', 'BJ'], 'batch_size': 3, 'offset': 0,
        })
        payload = response.get_json()

        self.assertTrue(payload['success'])
        self.assertEqual(payload['total_available'], 5)
        self.assertEqual(payload['total_scanned'], 3)
        self.assertTrue(payload['has_more'])
        calls = [(call.args[0]['code'], call.args[1]) for call in analyze.call_args_list]
        self.assertEqual(calls, [('000001', 'A'), ('920001', 'BJ'), ('000002', 'A')])


if __name__ == '__main__':
    unittest.main()
