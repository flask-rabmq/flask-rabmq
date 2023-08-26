"""
@Description：中间件
@Author：tsir
@Time：2023/3/18 11:53
@Copyright：©2019-2030 成都俊云科技有限公司
"""
from enum import IntEnum
from enum import auto

from flask_rabmq.exceptions import MiddlewareAttachToNameError


class MiddlewareLocation(IntEnum):
    HANDEL_BEFORE = auto()
    HANDLE_AFTER = auto()


class Middleware:
    __slots__ = ("func", "location")

    def __init__(self, func, location: MiddlewareLocation) -> None:
        self.func = func
        self.location = location

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __hash__(self) -> int:
        return hash(self.func)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(" f"func=<function {self.func.__name__}>, " f"location={self.location.name})"


class MiddlewareMixin:

    FUNC_MAP = {MiddlewareLocation.HANDEL_BEFORE: [], MiddlewareLocation.HANDLE_AFTER: []}

    def middleware(self, attach_to="handle_before"):
        def register_middleware(func):
            if attach_to == 'handle_before':
                location = MiddlewareLocation.HANDEL_BEFORE
            elif attach_to == 'handle_after':
                location = MiddlewareLocation.HANDLE_AFTER
            else:
                raise MiddlewareAttachToNameError("unknown attach to name: handler_before/handler_after")
            middleware = Middleware(func, location)
            self.FUNC_MAP[location].append(middleware)
            return middleware

        return register_middleware

    def on_handle_before(self, body, message):
        for func in self.FUNC_MAP[MiddlewareLocation.HANDEL_BEFORE]:
            func(body, message)

    def on_handle_after(self, body, message):
        for func in self.FUNC_MAP[MiddlewareLocation.HANDLE_AFTER]:
            func(body, message)
