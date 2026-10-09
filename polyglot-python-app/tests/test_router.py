import unittest
from unittest.mock import Mock, patch

import pika

from python_router_app import Router


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        self.channel = self.connection.channel.return_value
        with patch('python_router_app.pika.BlockingConnection', return_value=self.connection), \
                patch('python_router_app.Actuator.start'):
            self.router = Router('info', {
                'host': 'rabbitmq', 'port': 5672, 'virtual_host': '/',
                'username': 'user', 'password': 'secret',
            }, 'timeDest', 'evenDest', 'oddDest', 'routers')
        self.method = Mock(delivery_tag=42)

    def test_spring_binder_topology(self):
        self.assertEqual(self.channel.exchange_declare.call_count, 3)
        self.channel.exchange_declare.assert_any_call(
            exchange='timeDest', exchange_type='topic', durable=True)
        self.channel.queue_declare.assert_called_once_with(
            queue='timeDest.routers', durable=True)
        self.channel.queue_bind.assert_called_once_with(
            queue='timeDest.routers', exchange='timeDest', routing_key='#')
        self.channel.basic_consume.assert_called_once_with(
            queue='timeDest.routers', on_message_callback=self.router.route_timestamp,
            auto_ack=False)
        self.channel.confirm_delivery.assert_called_once_with()
        self.channel.basic_qos.assert_called_once_with(prefetch_count=1)

    def test_even_and_odd_outputs_acknowledged_after_publish(self):
        for timestamp, exchange, output in (
                (b'2026-10-09 12:00:02', 'evenDest', b'Even timestamp: 2026-10-09 12:00:02'),
                (b'2026-10-09 12:00:03', 'oddDest', b'Odd timestamp:2026-10-09 12:00:03')):
            with self.subTest(timestamp=timestamp):
                self.channel.reset_mock()
                self.router.route_timestamp(self.channel, self.method, None, timestamp)
                publish = self.channel.basic_publish.call_args.kwargs
                self.assertEqual(publish['exchange'], exchange)
                self.assertEqual(publish['routing_key'], exchange)
                self.assertEqual(publish['body'], output)
                self.assertTrue(publish['mandatory'])
                self.assertEqual(publish['properties'].delivery_mode, 2)
                self.channel.basic_ack.assert_called_once_with(delivery_tag=42)
                calls = [call[0] for call in self.channel.mock_calls]
                self.assertLess(calls.index('basic_publish'), calls.index('basic_ack'))

    def test_invalid_inputs_rejected_without_publish(self):
        for body in (b'', b'not-a-timestamp', b'2026-10-09x'):
            with self.subTest(body=body):
                self.channel.reset_mock()
                self.router.route_timestamp(self.channel, self.method, None, body)
                self.channel.basic_nack.assert_called_once_with(delivery_tag=42, requeue=False)
                self.channel.basic_publish.assert_not_called()
                self.channel.basic_ack.assert_not_called()

    def test_publish_failures_leave_input_unacknowledged(self):
        for error in (pika.exceptions.UnroutableError([]),
                      pika.exceptions.NackError([]),
                      pika.exceptions.AMQPConnectionError()):
            with self.subTest(error=type(error).__name__):
                self.channel.reset_mock()
                self.channel.basic_publish.side_effect = error
                with self.assertRaises(type(error)):
                    self.router.route_timestamp(self.channel, self.method, None, b'02')
                self.channel.basic_ack.assert_not_called()
                self.channel.basic_nack.assert_not_called()

    def test_consumption_failure_closes_connection_for_redelivery(self):
        self.channel.start_consuming.side_effect = pika.exceptions.AMQPConnectionError()
        with self.assertRaises(pika.exceptions.AMQPConnectionError):
            self.router.process_timestamps()
        self.connection.close.assert_called_once_with()

    def test_missing_destination_fails_before_connecting(self):
        with patch('python_router_app.pika.BlockingConnection') as connect:
            with self.assertRaises(ValueError):
                Router('info', {}, '', 'evenDest', 'oddDest')
            connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
