# -*- coding:utf-8 -*-

import logging
import sys
from functools import update_wrapper

# Syntax sugar.
_ver = sys.version_info

#: Python 2.x?
is_py2 = (_ver[0] == 2)

#: Python 3.x?
is_py3 = (_ver[0] == 3)

logger = logging.getLogger(__name__)


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
