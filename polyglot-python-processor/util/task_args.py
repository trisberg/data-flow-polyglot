import os
import sys
from collections import defaultdict

import pika

def get_cmd_arg(name):
    d = defaultdict(list)
    for cmd_args in sys.argv[1:]:
        cmd_arg = cmd_args.split('=')
        if len(cmd_arg) == 2:
            d[cmd_arg[0].lstrip('-')].append(cmd_arg[1])

    if name in d:
        return d[name][0]
    else:
        print('Unknown command line arg requested: {}'.format(name))

def get_env_var(name):
    if name in os.environ:
        return os.environ[name]
    else:
        print('Unknown environment variable requested: {}'.format(name))
            
def get_rabbitmq_connection_params():
    return pika.ConnectionParameters(
        host=get_env_var('SPRING_RABBITMQ_HOST') or 'localhost',
        port=int(get_env_var('SPRING_RABBITMQ_PORT') or 5672),
        virtual_host=get_env_var('SPRING_RABBITMQ_VIRTUAL_HOST') or '/',
        credentials=pika.PlainCredentials(
            get_env_var('SPRING_RABBITMQ_USERNAME') or 'guest',
            get_env_var('SPRING_RABBITMQ_PASSWORD') or 'guest',
        ),
    )

def get_input_channel():
    return get_cmd_arg("spring.cloud.stream.bindings.input.destination")

def get_input_group():
    return get_cmd_arg("spring.cloud.stream.bindings.input.group")

def get_output_channel():
    return get_cmd_arg("spring.cloud.stream.bindings.output.destination")

def get_reverse_string():
    return get_cmd_arg("reversestring")
