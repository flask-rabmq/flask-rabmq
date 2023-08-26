import logging
import random

from flask import Flask

from flask_rabmq import RabbitMQ

logging.basicConfig(format='%(asctime)s %(process)d,%(threadName)s %(filename)s:%(lineno)d [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

app = Flask(__name__)

app.config.setdefault('RABMQ_RABBITMQ_URL', 'amqp://username:password@ip:port/dev_vhost')
app.config.setdefault('RABMQ_SEND_EXCHANGE_NAME', 'flask_rabmq')
app.config.setdefault('RABMQ_SEND_EXCHANGE_TYPE', 'topic')

ramq = RabbitMQ()
ramq.init_app(app=app)


@app.route('/')
def hello_world():
    # send message
    ramq.send({'message_id': 222222, 'a': 7}, routing_key='flask_rabmq.test', exchange_name='flask_rabmq')
    # delay send message, expiration second(support float).
    ramq.delay_send({'message_id': 333333, 'a': 7}, routing_key='flask_rabmq.test', exchange_name='flask_rabmq',
                    delay=random.randint(1, 20))
    return 'Hello World!'


# received message
@ramq.queue(exchange_name='flask_rabmq', routing_key='flask_rabmq.test')
def flask_rabmq_test(body):
    """

    :param body: json string.
    :return: True/False
        return True, the message will be acknowledged.
        return False, the message is resended(default 3 count) to the queue.
        :exception, the message will not be acknowledged.
    """
    logger.info(body)
    return True


@ramq.middleware("handle_before")
def mq_handler_before(body, message):
    logger.info('rabmq before handler....')
    logger.info('body: %s, message: %s', body, message)


@ramq.middleware(attach_to="handle_after")
def mq_handle_after(body, message):
    logger.info('rabmq after handler....')
    logger.info('body: %s, message: %s', body, message)


ramq.run_consumer()


if __name__ == '__main__':
    app.run()
else:
    application = app
