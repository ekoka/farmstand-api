import dramatiq


def set_broker(broker, host):
    if broker=='redis':
        from dramatiq.brokers.redis import RedisBroker
        dramatiq.set_broker(RedisBroker(host=host))
    if broker=='rabbitmq':
        from dramatiq.brokers.rabbitmq import RabbitmqBroker
        dramatiq.set_broker(RabbitmqBroker(host=host))
