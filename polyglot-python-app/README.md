# RabbitMQ timestamp router

The app consumes timestamp bytes from `timeDest` and routes them to `evenDest`
or `oddDest` according to the last digit. Output payloads retain the original
format: `Even timestamp: <timestamp>` and `Odd timestamp:<timestamp>`.

Destinations are durable **topic exchanges**, matching the default Spring Cloud
Stream RabbitMQ binder. The input queue is `<input destination>.<input group>`
(default `timeDest.python-router`) and binds with routing key `#`. Replicas with
the same group share that queue. Custom binder prefixes, partitioning, exchange
types, and multiple destinations per binding are not supported.

Inputs are acknowledged after a persistent output publish is confirmed by
RabbitMQ. Delivery is at least once: a crash between publishing and acknowledging
can duplicate an output. Malformed timestamps are rejected without requeueing
(and discarded unless the input queue has a dead-letter policy). Publish errors,
including missing output bindings, stop the app and leave the input for redelivery;
configure the deployment to restart it after broker failures. Start downstream
consumers before publishing so their queues are bound to the output exchanges.

## Run locally

Use Python 3.9 or newer and a running RabbitMQ broker:

```bash
docker run -d --name router-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4-management
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python python_router_app.py \
  --spring.cloud.stream.bindings.input.destination=timeDest \
  --spring.cloud.stream.bindings.input.group=python-router \
  --spring.cloud.stream.bindings.even.destination=evenDest \
  --spring.cloud.stream.bindings.odd.destination=oddDest
```

Use the RabbitMQ management UI at `http://localhost:15672` (local credentials
`guest` / `guest`) to create and bind output queues to `evenDest` and `oddDest`
with routing key `#`, then publish a timestamp to `timeDest`.
Health and configuration endpoints are available at `/actuator/health` and
`/actuator/info` on port 8080. Health is a process liveness check.

Connection properties can be passed as `--property=value` or environment
variables; command-line values take precedence:

| Property | Environment variable | Default |
| --- | --- | --- |
| `spring.rabbitmq.host` | `SPRING_RABBITMQ_HOST` | `localhost` |
| `spring.rabbitmq.port` | `SPRING_RABBITMQ_PORT` | `5672` |
| `spring.rabbitmq.username` | `SPRING_RABBITMQ_USERNAME` | `guest` |
| `spring.rabbitmq.password` | `SPRING_RABBITMQ_PASSWORD` | `guest` |
| `spring.rabbitmq.virtual-host` | `SPRING_RABBITMQ_VIRTUAL_HOST` | `/` |

Bindings also accept environment variables, for example
`SPRING_CLOUD_STREAM_BINDINGS_INPUT_DESTINATION=timeDest` and
`SPRING_CLOUD_STREAM_BINDINGS_INPUT_GROUP=python-router`.
Set credentials through environment variables in deployed environments.
The client uses plain AMQP on a single host; AMQP URLs, TLS and address lists
are not implemented.

## Deploy with Spring Cloud Data Flow

Build and push the container (replace `YOUR_DOCKER_HUB_USER`):

```bash
docker build -t YOUR_DOCKER_HUB_USER/scdf_python_app:0.2 .
docker push YOUR_DOCKER_HUB_USER/scdf_python_app:0.2
```

Register the image in the SCDF shell:

```text
app register --type app --name python-router --uri docker://YOUR_DOCKER_HUB_USER/scdf_python_app:0.2
```

Use RabbitMQ binder variants of the `time` and logger applications. Apply
`polyglot-python-app-deployment.properties` when deploying the stream. The
producer's `requiredGroups` provisions the input queue before the router starts;
the logger groups give each output a durable queue. Provide the RabbitMQ host,
port, credentials, and virtual host to both the Python app and Spring apps. The
Python container needs a reachable broker hostname rather than `localhost`.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests cover routing, queue setup, publish failure acknowledgements, and settings
without requiring a running broker.
