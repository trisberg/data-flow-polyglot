import os
import sys


def get_cmd_arg(name):
    """Read the first --name=value deployer argument, preserving '=' in values."""
    for argument in sys.argv[1:]:
        key, separator, value = argument.lstrip('-').partition('=')
        if separator and key == name:
            return value
    return ''


def get_property(name, default=''):
    """Command-line settings override Spring-style environment variables."""
    value = get_cmd_arg(name)
    if value:
        return value
    return os.getenv(name.upper().replace('.', '_').replace('-', '_'), default)


def get_stream_app_label():
    return get_property('spring.cloud.dataflow.stream.app.label')


def get_stream_name():
    return get_property('spring.cloud.dataflow.stream.name')


def get_channel_destination(channel_name):
    """Return the RabbitMQ exchange for a Spring Cloud Stream binding."""
    return get_property('spring.cloud.stream.bindings.{}.destination'.format(channel_name))


def get_channel_group(channel_name, default=''):
    return get_property('spring.cloud.stream.bindings.{}.group'.format(channel_name), default)


def get_rabbitmq_settings():
    return {
        'host': get_property('spring.rabbitmq.host', 'localhost'),
        'port': int(get_property('spring.rabbitmq.port', '5672')),
        'username': get_property('spring.rabbitmq.username', 'guest'),
        'password': get_property('spring.rabbitmq.password', 'guest'),
        'virtual_host': get_property('spring.rabbitmq.virtual-host', '/'),
    }


def get_application_guid():
    return os.getenv('SPRING_CLOUD_APPLICATION_GUID', '')


def get_application_group():
    return os.getenv('SPRING_CLOUD_APPLICATION_GROUP', '')


def get_env_info():
    rabbitmq = get_rabbitmq_settings()
    props = (
        '  stream-name={}\n  app-name={}\n  app-guid={}\n  app-group={}\n'
        '  rabbitmq-host={}\n  rabbitmq-port={}\n  rabbitmq-virtual-host={}\n'
        '  input-group={}\n'
    ).format(get_stream_name(), get_stream_app_label(), get_application_guid(),
             get_application_group(), rabbitmq['host'], rabbitmq['port'],
             rabbitmq['virtual_host'], get_channel_group('input', 'python-router'))
    channels = '  Inputs:\n    input={}\n  Outputs:\n    even={}\n    odd={}\n'.format(
        get_channel_destination('input'), get_channel_destination('even'),
        get_channel_destination('odd'))
    # Arguments may contain RabbitMQ credentials; expose only safe configuration.
    return 'Properties\n{}\nChannels\n{}'.format(props, channels)
