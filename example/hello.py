import logging

from flask import Flask

from flask_rabmq import RabbitMQ

logging.basicConfig(format='%(asctime)s %(process)d,%(threadName)s %(filename)s:%(lineno)d [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

app = Flask(__name__)

app.config.setdefault('RABBITMQ_URL', 'amqp://username:password@ip:port/dev_vhost')

ramq = RabbitMQ()
ramq.init_app(app=app)


@app.route('/')
def hello_world():
    ramq.send({'message_id': 222222, 'a': 7}, routing_key='flask_rabmq.test', exchange_name='flask_rabmq')
    return 'Hello World!'


@ramq.queue(exchange_name='flask_rabmq', routing_key='flask_rabmq.test')
def flask_rabmq_test(body):
    logger.info(body)
    return True


if __name__ == '__main__':
    app.run()