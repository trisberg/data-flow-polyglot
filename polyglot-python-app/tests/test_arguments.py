import os
import unittest
from unittest.mock import patch

from util.arguments import get_cmd_arg, get_env_info, get_rabbitmq_settings


class ArgumentsTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch('sys.argv', ['router'])
    def test_rabbitmq_defaults(self):
        self.assertEqual(get_rabbitmq_settings(), {
            'host': 'localhost', 'port': 5672, 'username': 'guest',
            'password': 'guest', 'virtual_host': '/',
        })

    @patch.dict(os.environ, {'SPRING_RABBITMQ_HOST': 'env-host',
                            'SPRING_RABBITMQ_PORT': '5673',
                            'SPRING_RABBITMQ_VIRTUAL_HOST': 'stream'}, clear=True)
    @patch('sys.argv', ['router', '--spring.rabbitmq.host=cli-host',
                        '--spring.rabbitmq.password=a=b', '--unrelated'])
    def test_environment_and_command_line_precedence(self):
        settings = get_rabbitmq_settings()
        self.assertEqual(settings['host'], 'cli-host')
        self.assertEqual(settings['port'], 5673)
        self.assertEqual(settings['virtual_host'], 'stream')
        self.assertEqual(settings['password'], 'a=b')
        self.assertEqual(get_cmd_arg('missing'), '')
        self.assertNotIn('a=b', get_env_info())


if __name__ == '__main__':
    unittest.main()
