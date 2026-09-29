#!/usr/bin/env python

import pika

from util.http_status_server import HttpHealthServer
from util.task_args import (
    get_rabbitmq_connection_params,
    get_input_channel,
    get_input_group,
    get_output_channel,
    get_reverse_string,
)

input_exchange = get_input_channel()
output_exchange = get_output_channel()
group = get_input_group()

connection = pika.BlockingConnection(get_rabbitmq_connection_params())
channel = connection.channel()

channel.exchange_declare(exchange=input_exchange, exchange_type='topic', durable=True)
channel.exchange_declare(exchange=output_exchange, exchange_type='topic', durable=True)

if group:
    queue_name = '{}.{}'.format(input_exchange, group)
    channel.queue_declare(queue=queue_name, durable=True)
else:
    result = channel.queue_declare(queue='', exclusive=True, auto_delete=True)
    queue_name = result.method.queue

channel.queue_bind(exchange=input_exchange, queue=queue_name, routing_key='#')

HttpHealthServer.run_thread()


def on_message(ch, method, properties, body):
    output_message = body
    reverse_string = get_reverse_string()

    if reverse_string is not None and reverse_string.lower() == "true":
        output_message = body[::-1]

    ch.basic_publish(exchange=output_exchange, routing_key='', body=output_message)
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(queue=queue_name, on_message_callback=on_message)
channel.start_consuming()
