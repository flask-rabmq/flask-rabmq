# -*- coding:utf-8 -*-

import json
import logging
import re
import traceback
from threading import RLock
from threading import Thread

from kombu import Connection
from kombu import Exchange
from kombu import Queue
from kombu.exceptions import KombuError

from .exceptions import ExchangeNameError
from .exceptions import RoutingKeyError
from .consumer_producer import CP
from .utils import ExchangeType
from .utils import is_py2
from .utils import setup_method

logger = logging.getLogger(__name__)


class RabbitMQ(object):

    def __init__(self, app=None):
        self.send_exchange_name = None
        self.send_exchange_type = None
        self.config = None
        self.consumer = None
        self.connection = None
        self.app = app
        self.message_callback_list = []
        self.wait_send_lock = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.config = app.config
        self.connection = Connection(self.config.get('RABMQ_RABBITMQ_URL'))
        self.consumer = CP(self.connection, self.message_callback_list)
        self.send_exchange_name = self.config.get('RABMQ_SEND_EXCHANGE_NAME')
        self.send_exchange_type = self.config.get('RABMQ_SEND_EXCHANGE_TYPE') or ExchangeType.TOPIC
        self.wait_send_lock = RLock()

    def run_consumer(self):
        self._run()

    def _run(self):
        thread = Thread(target=self.consumer.run)
        thread.setDaemon(True)
        thread.start()

    def queue(self, exchange_name, routing_key, queue_name=None, exchange_type=None, retry_count=3):

        def decorator(f):
            self.add_message_rule(f, queue_name=queue_name, exchange_type=exchange_type,
                                  exchange_name=exchange_name, routing_key=routing_key,
                                  retry_count=retry_count)
            return f

        return decorator

    @setup_method
    def add_message_rule(self, func, queue_name, routing_key,
                         exchange_name, exchange_type=ExchangeType.DEFAULT, retry_count=3):
        if not queue_name:
            queue_name = func.__name__
        if not routing_key:
            raise RoutingKeyError('routing_key 没有指定')

        if not exchange_name:
            raise ExchangeNameError('exchange_name 没有指定')

        def _callback(body, message):
            try:
                logger.info('message handler start: %s', func.__name__)
                try:
                    logger.info('received message routing_key:%s, exchange:%s',
                                routing_key,
                                exchange_name)
                    logger.info('received data:%s', body)
                    if is_py2:
                        if isinstance(body, (str, eval('unicode'))):
                            message_id = json.loads(body).get('message_id')
                        else:
                            message_id = body.get('message_id')
                    else:
                        if isinstance(body, str):
                            message_id = json.loads(body).get('message_id')
                        else:
                            message_id = body.get('message_id')
                    if not message_id:
                        logger.error('message not id: %s', body)
                        message.ack()
                        return True
                except Exception as E:
                    logger.error('parse message body failed:%s', body)
                    message.ack()
                    return True
                try:
                    if is_py2:
                        if not isinstance(body, (str, eval('unicode'))):
                            body = json.dumps(body)
                    else:
                        if not isinstance(body, str):
                            body = json.dumps(body)
                    with self.app.app_context():
                        result = func(body)
                    if result:
                        message.ack()
                        return True
                    else:
                        logger.info('no ack message')
                        if int(message.headers.get('retry') or 0) >= retry_count:
                            message.ack()
                            logger.info('retry %s count handler failed: %s', retry_count, body)
                            return True
                        headers = {'retry': int(message.headers.get('retry') or 0) + 1}
                        message.ack()
                        self.retry_send(body=body, queue_name=queue_name,
                                        headers=headers)
                        return False
                except KombuError:  # 不可预测的kombu错误
                    logger.info('Kombu Error pass: %s', traceback.format_exc())
                    return True
                except Exception as e:
                    logger.info('handler message failed: %s', traceback.format_exc())
                    headers = {'retry': int(message.headers.get('retry') or 0) + 1}
                    message.ack()
                    self.retry_send(body=body, queue_name=queue_name,
                                    headers=headers, )
                    return False
                finally:
                    logger.info('message handler end: %s', func.__name__)
            except Exception as e:
                logger.info('unknown error: %s' % traceback.format_exc())
                return True

        exchange = Exchange(name=exchange_name, type=exchange_type or ExchangeType.DEFAULT)
        queue = Queue(name=queue_name, exchange=exchange, routing_key=routing_key)
        tmp_dict = {'queue': queue, 'callback': _callback}
        self.message_callback_list.append(tmp_dict)

    def send(self, body, routing_key, exchange_name=None, exchange_type=None, headers=None, ):
        exchange = Exchange(
            name=exchange_name or self.send_exchange_name,
            type=exchange_type or self.send_exchange_type,
            auto_delete=False,
            durable=True
        )
        with self.wait_send_lock:
            self.consumer.producer.publish(
                body=body,
                exchange=exchange,
                routing_key=routing_key,
                retry=True,
                headers=headers,
                declare=[exchange]
            )
            logger.info('send data: %s', body)

    def retry_send(self, body, queue_name, headers=None, **kwargs):
        exchange = Exchange()
        with self.wait_send_lock:
            self.consumer.producer.publish(
                body=body,
                exchange=exchange,
                routing_key=queue_name,
                retry=True,
                headers=headers,
            )
            logger.info('retry send data: %s', body)

    def delay_send(self, body, routing_key, delay=None, exchange_name=None, **kwargs):
        dead_letter_params = {
            'x-dead-letter-routing-key': routing_key,
            'x-dead-letter-exchange': exchange_name
        }
        queue_name = '%s_%s_delay' % (exchange_name, re.sub('[^0-9a-zA-Z]+', '', routing_key))
        with self.wait_send_lock:
            exchange = Exchange()
            queue = Queue(
                name=queue_name, exchange=exchange, routing_key=queue_name, queue_arguments=dead_letter_params,
            )
            self.consumer.producer.publish(
                body=body,
                exchange=exchange,
                routing_key=queue_name,
                retry=True,
                declare=[queue],
                expiration=delay,
                **kwargs
            )
            logger.info('send data: %s', body)
