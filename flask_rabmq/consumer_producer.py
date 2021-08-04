# -*- coding:utf-8 -*-

import logging

from kombu.mixins import ConsumerProducerMixin

logger = logging.getLogger(__name__)


class CP(ConsumerProducerMixin):

    def __init__(self, connection, rpc_class_list):
        self.connection = connection
        self.rpc_class_list = rpc_class_list

    def get_consumers(self, consumer, channel):
        consumer_set = []
        for consumer_info in self.rpc_class_list:
            logger.info("consumer queue name: %s" % consumer_info['queue'])
            consumer_set.append(
                consumer(
                    queues=consumer_info['queue'], callbacks=[consumer_info['callback']],
                    prefetch_count=1  # 一个连接中只能有一个消息存在
                )
            )

        return consumer_set
