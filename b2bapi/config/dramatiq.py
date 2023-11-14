import dramatiq

def set_broker(broker):
    if broker=='redis':
        from dramatiq.brokers.redis import RedisBroker
        dramatiq.set_broker(RedisBroker(host='localhost'))
    if broker=='rabbitmq':
        from dramatiq.brokers.rabbitmq import RabbitmqBroker
        dramatiq.set_broker(RabbitmqBroker(host='localhost'))
