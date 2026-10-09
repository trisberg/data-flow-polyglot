import sys
import unittest
from unittest.mock import patch

from sqlalchemy import text

from util.task_args import get_db_url
from util.task_status import TaskStatus


class DatabaseUrlTests(unittest.TestCase):
    def test_postgresql_url_preserves_credentials_and_options(self):
        args = [
            'python_task.py',
            '--spring.datasource.url=jdbc:postgresql://localhost:5432/dataflow?sslmode=require',
            '--spring.datasource.username=task@user',
            '--spring.datasource.password=p@ss:/?#%',
        ]
        with patch.object(sys, 'argv', args):
            url = get_db_url()
        self.assertEqual(url.drivername, 'postgresql+psycopg2')
        self.assertEqual(url.username, 'task@user')
        self.assertEqual(url.password, 'p@ss:/?#%')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, 5432)
        self.assertEqual(url.database, 'dataflow')
        self.assertEqual(url.query['sslmode'], 'require')

    def test_missing_or_non_postgresql_url_is_rejected(self):
        for args in ([], ['--spring.datasource.url=jdbc:mysql://localhost/dataflow']):
            with self.subTest(args=args), patch.object(sys, 'argv', ['task'] + args):
                with self.assertRaises(ValueError):
                    get_db_url()


class TaskStatusTests(unittest.TestCase):
    def setUp(self):
        self.status = TaskStatus('42', 'sqlite://')
        with self.status.engine.begin() as connection:
            connection.execute(text(
                'CREATE TABLE TASK_EXECUTION ('
                'TASK_EXECUTION_ID INTEGER PRIMARY KEY, START_TIME TIMESTAMP, '
                'END_TIME TIMESTAMP, EXIT_CODE INTEGER, EXIT_MESSAGE TEXT, '
                'ERROR_MESSAGE TEXT, LAST_UPDATED TIMESTAMP)'))
            connection.execute(text(
                'INSERT INTO TASK_EXECUTION (TASK_EXECUTION_ID, EXIT_CODE) VALUES (42, 1)'))

    def tearDown(self):
        self.status.engine.dispose()

    def row(self):
        with self.status.engine.connect() as connection:
            return connection.execute(text('SELECT * FROM TASK_EXECUTION')).mappings().one()

    def test_status_transitions_are_committed(self):
        self.status.running()
        row = self.row()
        self.assertIsNotNone(row['START_TIME'])
        self.assertIsNone(row['EXIT_CODE'])

        self.status.failed(1, 'Task failed', 'Error details')
        row = self.row()
        self.assertEqual(row['EXIT_CODE'], 1)
        self.assertEqual(row['EXIT_MESSAGE'], 'Task failed')
        self.assertEqual(row['ERROR_MESSAGE'], 'Error details')
        self.assertIsNotNone(row['END_TIME'])
        self.assertIsNotNone(row['LAST_UPDATED'])

        self.status.completed()
        row = self.row()
        self.assertEqual(row['EXIT_CODE'], 0)
        self.assertIsNone(row['EXIT_MESSAGE'])
        self.assertIsNone(row['ERROR_MESSAGE'])


if __name__ == '__main__':
    unittest.main()
