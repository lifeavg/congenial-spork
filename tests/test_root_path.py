import pytest
from util import handler_factory, middleware_factory

from router import Router


def test_http_insertion_and_lookup():
    h = handler_factory()
    router = Router()
    router.add("/", "GET", h, None, None)
    assert router.lookup("/", "http", "GET") == (h, None, {})


def test_http_empty_lookup():
    router = Router()
    assert router.lookup("/", "http", "GET") == (None, None, {})


def test_http_empty_method_insertion_and_lookup():
    h = handler_factory()
    router = Router()
    router.add("/", None, h, None, None)
    assert router.lookup("/", "http") == (h, None, {})


def test_ws_insertion_and_lookup():
    h = handler_factory()
    router = Router()
    router.add("/", None, None, None, h)
    assert router.lookup("/", "ws") == (None, h, {})


@pytest.mark.asyncio()
async def test_http_middleware_insertion_and_lookup():
    router = Router()
    router.add("/", None, handler_factory(), middleware_factory(1), None)
    handler, _, _ = router.lookup("/", "http")
    assert handler is not None
    assert await handler("r") == "1 r 1"


@pytest.mark.asyncio()
async def test_http_multi_middleware_insertion_and_lookup():
    router = Router()
    router.add("/", None, None, middleware_factory(0), None)
    router.add("/", None, handler_factory(), middleware_factory(1), None)
    router.add("/", None, None, middleware_factory(2), None)
    handler, _, _ = router.lookup("/", "http")
    assert handler is not None
    assert await handler("r") == "2 1 0 r 0 1 2"


def test_http_middleware_without_handler_insertion_and_lookup():
    router = Router()
    router.add("/", None, None, middleware_factory(0), None)
    assert router.lookup("/", "http") == (None, None, {})


def test_multimethod_insertion_and_lookup_http():
    http_handler = handler_factory()
    ws_handler = handler_factory()
    router = Router()
    router.add("/", "GET", http_handler, None, None)
    router.add("/", None, None, None, ws_handler)
    assert router.lookup("/", "http", "GET") == (http_handler, None, {})


def test_multimethod_insertion_and_lookup_ws():
    http_handler = handler_factory()
    ws_handler = handler_factory()
    router = Router()
    router.add("/", "GET", http_handler, None, None)
    router.add("/", None, None, None, ws_handler)
    assert router.lookup("/", "ws") == (None, ws_handler, {})


def test_duplicate_raises():
    router = Router()
    router.add("/", "GET", handler_factory(), None, None)
    with pytest.raises(Exception):
        router.add("/", "GET", handler_factory(), None, None)


def test_different_method():
    get_handler = handler_factory()
    post_handler = handler_factory()
    router = Router()
    router.add("/", "GET", get_handler, None, None)
    router.add("/", "POST", post_handler, None, None)
    assert router.lookup("/", "http", "GET") == (get_handler, None, {})
    assert router.lookup("/", "http", "POST") == (post_handler, None, {})
