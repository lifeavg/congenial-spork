import pytest
from util import handler_factory, middleware_factory

from src.router import Router


def test_http_insertion_and_lookup():
    router = Router()
    h = handler_factory()
    router.add("/home", "GET", h, None, None)
    assert router.lookup("/home", "http", "GET") == (h, None, {})


def test_http_empty_lookup():
    router = Router()
    assert router.lookup("/home/one", "http", "GET") == (None, None, {})


def test_ws_insertion_and_lookup():
    router = Router()
    h = handler_factory()
    router.add("/home", None, None, None, h)
    assert router.lookup("/home", "ws") == (None, h, {})


@pytest.mark.asyncio()
async def test_http_middleware_insertion_and_lookup():
    router = Router()
    h = handler_factory()
    router.add("/home", None, h, middleware_factory(1), None)
    handler, _, _ = router.lookup("/home", "http")
    assert handler is not None
    assert await handler("r") == "1 r 1"


@pytest.mark.asyncio()
async def test_http_multi_middleware_insertion_and_lookup():
    router = Router()
    h = handler_factory()
    p = "/home"
    router.add(p, None, None, middleware_factory(0), None)
    router.add(p, None, h, middleware_factory(1), None)
    router.add(p, None, None, middleware_factory(2), None)
    handler, _, _ = router.lookup(p, "http")
    assert handler is not None
    assert await handler("r") == "2 1 0 r 0 1 2"


@pytest.mark.asyncio()
async def test_http_multilevel_middleware_insertion_and_lookup():
    router = Router()
    h = handler_factory()
    router.add("/", None, None, middleware_factory(2), None)
    router.add("/home/one", None, h, middleware_factory(0), None)
    router.add("/home", None, None, middleware_factory(1), None)
    router.add("/home/two", None, h, middleware_factory(3), None)
    handler, _, _ = router.lookup("/home/one", "http")
    assert handler is not None
    assert await handler("r") == "2 1 0 r 0 1 2"


def test_http_middleware_without_handler_insertion_and_lookup():
    router = Router()
    router.add("/home", None, None, middleware_factory(0), None)
    assert router.lookup("/home", "http") == (None, None, {})


def test_multimethod_insertion_and_lookup_http():
    http_handler = handler_factory()
    ws_handler = handler_factory()
    router = Router()
    router.add("/home", "GET", http_handler, None, None)
    router.add("/home", None, None, None, ws_handler)
    assert router.lookup("/home", "http", "GET") == (http_handler, None, {})


def test_multimethod_insertion_and_lookup_ws():
    http_handler = handler_factory()
    ws_handler = handler_factory()
    router = Router()
    router.add("/home", "GET", http_handler, None, None)
    router.add("/home", None, None, None, ws_handler)
    assert router.lookup("/home", "ws") == (None, ws_handler, {})


def test_not_match_non_identical_paths():
    router = Router()
    h = handler_factory()
    router.add("/home", "GET", h, None, None)
    assert router.lookup("/home/other", "http") == (None, None, {})


def test_duplicate_raises():
    router = Router()
    h = handler_factory()
    router.add("/home", "GET", h, None, None)
    with pytest.raises(Exception):
        router.add("/home", "GET", handler_factory(), None, None)


def test_different_method():
    get_handler = handler_factory()
    post_handler = handler_factory()
    router = Router()
    router.add("/home", "GET", get_handler, None, None)
    router.add("/home", "POST", post_handler, None, None)
    assert router.lookup("/home", "http", "GET") == (get_handler, None, {})
    assert router.lookup("/home", "http", "POST") == (post_handler, None, {})


@pytest.mark.asyncio()
async def test_complex_multilevel():
    router = Router()
    router.add("/home/two/sub", None, None, middleware_factory("hts"), None)
    router.add("/home/one", "GET", handler_factory(), middleware_factory("ho"), None)
    router.add("/", "GET", handler_factory(), middleware_factory("rt"), None)
    router.add("/home", "GET", handler_factory(), middleware_factory("h"), None)
    router.add("/home/two", "GET", handler_factory(), middleware_factory("ht"), None)
    router.add("/home/two/sub/sub", "GET", handler_factory(), middleware_factory("htss"), None)
    router.add("/other/one", "GET", handler_factory(), middleware_factory("oo"), None)
    router.add("/", None, None, middleware_factory("rt_"), None)

    h, _, _ = router.lookup("/other/one", "http", "GET")
    assert h is not None
    assert await h("r") == "rt_ rt oo r oo rt rt_"
    h, _, _ = router.lookup("/", "http", "GET")
    assert h is not None
    assert await h("r") == "rt_ rt r rt rt_"
    h, _, _ = router.lookup("/home/two", "http", "GET")
    assert h is not None
    assert await h("r") == "rt_ rt h ht r ht h rt rt_"
    h, _, _ = router.lookup("/home", "http", "GET")
    assert h is not None
    assert await h("r") == "rt_ rt h r h rt rt_"
    h, _, _ = router.lookup("/home/one", "http", "GET")
    assert h is not None
    assert await h("r") == "rt_ rt h ho r ho h rt rt_"
    h, _, _ = router.lookup("/home/two/sub/sub", "http", "GET")
    assert h is not None
    assert await h("r") == "rt_ rt h ht hts htss r htss hts ht h rt rt_"
