import logging

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
                    delay=10)
    return 'Hello World!'


@ramq.queue(exchange_name='flask_rabmq', routing_key='flask_rabmq.test')
def flask_rabmq_test(body):
    logger.info(body)
    return True


if __name__ == '__main__':
    ramq.run_consumer()
    app.run()
