import unittest
import log_analyzer
import os
import gzip
import bz2


class ConfigTest(unittest.TestCase):
    def setUp(self):
        with open('con.conf', 'wb') as con:
            con.write('"REPORT_DIR": "."')
            con.write('\n')
            con.write('"REPORT_SIZE": 10')
            con.write('\n')
            con.write('"LOG_DIR": "."')

    def test_config(self):
        self.assertEqual(log_analyzer.get_config('con.conf'), {'REPORT_DIR': ".", 'REPORT_SIZE': '10', 'LOG_DIR': "."})

    def tearDown(self):
        os.remove('con.conf')


class ReportTest(unittest.TestCase):
    def setUp(self):
        with open('log-example.log') as f:
            content = f.read()

        with gzip.open('nginx-access-ui.log-20181101.gz', 'w') as f1:
            f1.write(content)

        with bz2.BZ2File('nginx-access-ui.log-20181102.bz2', 'w') as f2:
            f2.writelines(content)

    def test_get_log_file(self):
        self.assertEqual(log_analyzer.get_log('.').log_file_name, 'nginx-access-ui.log-20181101.gz')

    def test_create_report(self):
        file_log = 'nginx-access-ui.log-20181101.gz'
        self.assertEqual(log_analyzer.create_report(file_log, 1)[0]['count'], 3)
        self.assertLessEqual(abs(log_analyzer.create_report(file_log, 1)[0]['time_sum']-1.17), 0.01)
        self.assertLessEqual(abs(log_analyzer.create_report(file_log, 1)[0]['time_avg']-0.39), 0.01)
        self.assertLessEqual(abs(log_analyzer.create_report(file_log, 1)[0]['time_max']-0.49), 0.01)
        self.assertLessEqual(abs(log_analyzer.create_report(file_log, 1)[0]['time_med']-0.39), 0.01)
        self.assertLessEqual(abs(log_analyzer.create_report(file_log, 1)[0]['count_perc']-50), 1)
        self.assertLessEqual(abs(log_analyzer.create_report(file_log, 1)[0]['time_perc']-67), 1)

    def tearDown(self):
        os.remove('nginx-access-ui.log-20181101.gz')
        os.remove('nginx-access-ui.log-20181102.bz2')


if __name__ == '__main__':
    unittest.main()
