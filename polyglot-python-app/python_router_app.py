import logging

import pika

from util.actuator import Actuator
from util.arguments import (
    get_channel_destination,
    get_channel_group,
    get_env_info,
    get_rabbitmq_settings,
)


class Router:
    """Route timestamp bytes from a RabbitMQ input exchange to even/odd exchanges.

    Destinations use Spring Cloud Stream's default RabbitMQ topology: durable
    topic exchanges and a durable input queue named <destination>.<group>.
    """

    def __init__(self, info, rabbitmq_settings, input_exchange, even_exchange,
                 odd_exchange, input_group='python-router'):
        if not all((input_exchange, even_exchange, odd_exchange, input_group)):
            raise ValueError('Input, even, odd destinations and input group are required')
        if any(',' in name for name in (input_exchange, even_exchange, odd_exchange)):
            raise ValueError('Each binding must specify a single destination')

        self.input_exchange = input_exchange
        self.even_exchange = even_exchange
        self.odd_exchange = odd_exchange
        self.input_queue = '{}.{}'.format(input_exchange, input_group)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rabbitmq_settings['host'],
            port=rabbitmq_settings['port'],
            virtual_host=rabbitmq_settings['virtual_host'],
            credentials=pika.PlainCredentials(
                rabbitmq_settings['username'], rabbitmq_settings['password']),
            heartbeat=60,
            blocked_connection_timeout=30,
        ))
        try:
            self.channel = self.connection.channel()
            for exchange in dict.fromkeys((input_exchange, even_exchange, odd_exchange)):
                self.channel.exchange_declare(
                    exchange=exchange, exchange_type='topic', durable=True)
            self.channel.queue_declare(queue=self.input_queue, durable=True)
            self.channel.queue_bind(
                queue=self.input_queue, exchange=input_exchange, routing_key='#')
            self.channel.basic_qos(prefetch_count=1)
            self.channel.confirm_delivery()
            self.channel.basic_consume(
                queue=self.input_queue, on_message_callback=self.route_timestamp,
                auto_ack=False)
        except Exception:
            self.close()
            raise

        Actuator.start(port=8080, info=info)

    def route_timestamp(self, channel, method, properties, body):
        try:
            even = self.is_even_timestamp(body)
        except (ValueError, TypeError):
            logging.warning('Rejecting invalid timestamp: %r', body)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        exchange = self.even_exchange if even else self.odd_exchange
        prefix = b'Even timestamp: ' if even else b'Odd timestamp:'
        # Confirms + mandatory detect failed or unroutable publishes. An exception
        # stops consumption; closing the connection requeues the unacked input.
        channel.basic_publish(
            exchange=exchange,
            routing_key=exchange,
            body=prefix + body,
            properties=pika.BasicProperties(content_type='text/plain', delivery_mode=2),
            mandatory=True,
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def process_timestamps(self):
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        finally:
            self.close()

    def close(self):
        if self.connection.is_open:
            self.connection.close()

    @staticmethod
    def is_even_timestamp(value):
        return int(value[-1:]) % 2 == 0


def main():
    Router(
        get_env_info(),
        get_rabbitmq_settings(),
        get_channel_destination('input'),
        get_channel_destination('even'),
        get_channel_destination('odd'),
        get_channel_group('input', 'python-router'),
    ).process_timestamps()


if __name__ == '__main__':
    main()
