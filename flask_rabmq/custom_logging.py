# -*- coding:utf-8 -*-

import logging


class CustomLogging(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def info(self, message_id='', msg='', *args, **kwargs):
        self.logger.info('%s %s' % (message_id, msg), *args, **kwargs)

    def error(self, message_id='', msg='', *args, **kwargs):
        self.logger.error('%s %s' % (message_id, msg), *args, **kwargs)

    def warning(self, message_id='', msg='', *args, **kwargs):
        self.logger.warning('%s %s' % (message_id, msg), *args, **kwargs)

    def critical(self, message_id='', msg='', *args, **kwargs):
        self.logger.critical('%s %s' % (message_id, msg), *args, **kwargs)

    def debug(self, message_id='', msg='', *args, **kwargs):
        self.logger.debug('%s %s' % (message_id, msg), *args, **kwargs)