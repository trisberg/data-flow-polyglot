import sys
from collections import defaultdict
from sqlalchemy.engine import make_url

def get_cmd_arg(name):
    d = defaultdict(list)
    for k, v in ((k.lstrip('-'), v) for k, v in (a.split('=', 1) for a in sys.argv[1:])):
        d[k].append(v)

    if bool(d[name]):
        return d[name][0]
    else:
        return None

def get_db_url():
    username = get_cmd_arg('spring.datasource.username')
    password = get_cmd_arg('spring.datasource.password')
    jdbc_url = get_cmd_arg('spring.datasource.url')

    if jdbc_url is None or not jdbc_url.startswith('jdbc:postgresql:'):
        raise ValueError('spring.datasource.url must be a jdbc:postgresql:// URL')

    return make_url(jdbc_url[len('jdbc:'):]).set(
        drivername='postgresql+psycopg2', username=username, password=password)

def get_task_id():
    return get_cmd_arg('spring.cloud.task.executionid')

def get_task_name():
    return get_cmd_arg('spring.cloud.task.name')
