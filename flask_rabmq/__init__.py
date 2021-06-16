# -*- coding:utf-8 -*-

import re
import json
import sys
import random
import traceback
from functools import update_wrapper
from threading import Thread
from threading import RLock

from kombu import Connection
from kombu import Exchange
from kombu import Queue
from kombu.mixins import ConsumerProducerMixin
from kombu.exceptions import KombuError

from flask_rabmq.custom_logging import CustomLogging
from flask_rabmq.rabmq_exception import ExchangeNameError
from flask_rabmq.rabmq_exception import RoutingKeyError


# Syntax sugar.
_ver = sys.version_info

#: Python 2.x?
is_py2 = (_ver[0] == 2)

#: Python 3.x?
is_py3 = (_ver[0] == 3)

logger = CustomLogging()


def setup_method(f):
    def wrapper_func(self, *args, **kwargs):
        return f(self, *args, **kwargs)

    return update_wrapper(wrapper_func, f)


# 定义交换机类型的枚举值
class ExchangeType(object):
    DEFAULT = 'topic'
    DIRECT = "direct"
    FANOUT = "fanout"
    TOPIC = 'topic'
    HEADER = 'header'


class CP(ConsumerProducerMixin):

    def __init__(self, connection, rpc_class_list):
        self.connection = connection
        self.rpc_class_list = rpc_class_list

    def get_consumers(self, Consumer, channel):
        consumer_set = []
        for consumer in self.rpc_class_list:
            logger.info("open channel, queue name: %s" % consumer['queue'])
            consumer_set.append(
                Consumer(
                    queues=consumer['queue'], callbacks=[consumer['callback']],
                    prefetch_count=1  # 一个连接中只能有一个消息存在
                )
            )

        return consumer_set


class RabbitMQ(object):

    def __init__(self, app=None):
        self.send_exchange_name = None
        self.send_exchange_type = None
        self.config = None
        self.consumer = None
        self.connection = None
        self.send_connection = None
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
        self.send_connection = self.connection.clone()
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
                handler_flag = ''.join(random.sample('0123456789', 10))
                logger.info(handler_flag, 'message handler start: %s', func.__name__)
                try:
                    logger.info(handler_flag,
                                'received_message-route_key:%s-exchange:%s',
                                routing_key,
                                exchange_name)
                    logger.info(handler_flag, 'received data:%s', body)
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
                        logger.error(handler_flag, 'message not id: %s', body)
                        message.ack()
                        return True
                except:
                    logger.error(handler_flag, 'parse message body failed:%s', body)
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
                        logger.info(handler_flag, 'no ack message')
                        if int(message.headers.get('retry') or 0) >= retry_count:
                            message.ack()
                            logger.info(handler_flag, 'retry %s count handler failed: %s', retry_count, body)
                            return True
                        headers = {'retry': int(message.headers.get('retry') or 0) + 1}
                        message.ack()
                        self.retry_send(body=body, queue_name=queue_name,
                                        headers=headers, log_flag=handler_flag)
                        return False
                except ConnectionError:  # 不可预测的Connect错误
                    logger.info(handler_flag, 'Connection Error pass: %s', traceback.format_exc())
                    return True
                except KombuError:  # 不可预测的kombu错误
                    logger.info(handler_flag, 'Kombu Error pass: %s', traceback.format_exc())
                    return True
                except Exception as e:
                    logger.info(handler_flag, 'handler message failed: %s', traceback.format_exc())
                    headers = {'retry': int(message.headers.get('retry') or 0) + 1}
                    message.ack()
                    self.retry_send(body=body, queue_name=queue_name,
                                    headers=headers, log_flag=handler_flag)
                    return False
                finally:
                    logger.info(handler_flag, 'message handler end: %s', func.__name__)
            except Exception as e:
                logger.info('unknown error: %s' % traceback.format_exc())
                return True

        exchange = Exchange(name=exchange_name, type=exchange_type or ExchangeType.DEFAULT)
        queue = Queue(name=queue_name, exchange=exchange, routing_key=routing_key)
        tmp_dict = {'queue': queue, 'callback': _callback}
        self.message_callback_list.append(tmp_dict)

    def send(self, body, routing_key, exchange_name=None, exchange_type=None, headers=None, log_flag=None):
        exchange = Exchange(
            name=exchange_name or self.send_exchange_name,
            type=exchange_type or self.send_exchange_type,
            auto_delete=False,
            durable=True
        )
        with self.wait_send_lock:
            channel = self.send_connection.default_channel
            exchange.declare(channel=channel)
            self.consumer.producer.publish(
                body=body,
                exchange=exchange,
                routing_key=routing_key,
                retry=True,
                headers=headers,
            )
            logger.info(log_flag, 'send data: %s', body)

    def retry_send(self, body, queue_name, headers=None, log_flag='', **kwargs):
        logger.info(log_flag, 'send data: %s', body)
        with self.wait_send_lock:
            simple_queue = self.send_connection.SimpleQueue(queue_name)
            simple_queue.put(body, headers=headers, retry=True, **kwargs)

    def delay_send(self, body, routing_key, delay=None, exchange_name=None, log_flag=None, **kwargs):
        logger.info(log_flag, 'send data: %s', body)
        dead_letter_params = {
            'x-dead-letter-routing-key': routing_key,
            'x-dead-letter-exchange': exchange_name
        }
        queue_name = '%s_%s' % (exchange_name, re.sub('[^0-9a-zA-Z]+', '', routing_key))
        with self.wait_send_lock:
            channel = self.send_connection.default_channel
            simple_queue = self.send_connection.SimpleQueue(
                queue_name,
                queue_args=dead_letter_params,
                channel=channel
            )
            simple_queue.put(body, retry=True, expiration=delay, **kwargs)
