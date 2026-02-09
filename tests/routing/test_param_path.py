import pytest
from util import handler_factory, middleware_factory

from router import Router


def test_http_insertion_and_lookup():
    h = handler_factory()
    router = Router()
    router.add("/:id", "GET", h, None, None)
    assert router.lookup("/123", "http", "GET") == (h, None, {"id": "123"})


def test_param_route_insertion_and_lookup_multiple_params():
    h = handler_factory()
    router = Router()
    router.add("/users/:id", "GET", handler_factory(), None, None)
    router.add("/posts/:category/:post_id", "GET", h, None, None)
    assert router.lookup("/posts/news/456", "http", "GET") == (h, None, {"category": "news", "post_id": "456"})


def test_http_empty_method_insertion_and_lookup():
    h = handler_factory()
    router = Router()
    router.add("/:id", None, h, None, None)
    assert router.lookup("/123", "http") == (h, None, {"id": "123"})


def test_ws_insertion_and_lookup():
    h = handler_factory()
    router = Router()
    router.add("/:id", None, None, None, h)
    assert router.lookup("/123", "ws") == (None, h, {"id": "123"})


@pytest.mark.asyncio()
async def test_http_middleware_insertion_and_lookup():
    router = Router()
    router.add("/:id", None, handler_factory(), middleware_factory(1), None)
    handler, _, params = router.lookup("/123", "http")
    assert handler is not None
    assert params == {"id": "123"}
    assert await handler("r") == "1 r 1"


@pytest.mark.asyncio()
async def test_http_multi_middleware_insertion_and_lookup():
    router = Router()
    router.add("/:id", None, None, middleware_factory(0), None)
    router.add("/:id", None, handler_factory(), middleware_factory(1), None)
    router.add("/:id", None, None, middleware_factory(2), None)
    handler, _, params = router.lookup("/123", "http")
    assert handler is not None
    assert params == {"id": "123"}
    assert await handler("r") == "2 1 0 r 0 1 2"


def test_http_middleware_without_handler_insertion_and_lookup():
    router = Router()
    router.add("/:id", None, None, middleware_factory(0), None)
    assert router.lookup("/123", "http") == (None, None, {})


def test_multimethod_insertion_and_lookup_http():
    http_handler = handler_factory()
    ws_handler = handler_factory()
    router = Router()
    router.add("/:id", "GET", http_handler, None, None)
    router.add("/:id", None, None, None, ws_handler)
    assert router.lookup("/123", "http", "GET") == (http_handler, None, {"id": "123"})


def test_multimethod_insertion_and_lookup_ws():
    http_handler = handler_factory()
    ws_handler = handler_factory()
    router = Router()
    router.add("/:id", "GET", http_handler, None, None)
    router.add("/:id", None, None, None, ws_handler)
    assert router.lookup("/123", "ws") == (None, ws_handler, {"id": "123"})


def test_not_match_non_identical_paths():
    router = Router()
    h = handler_factory()
    router.add("/:id", "GET", h, None, None)
    assert router.lookup("/home/other", "http") == (None, None, {})


def test_duplicate_raises():
    router = Router()
    router.add("/:id", "GET", handler_factory(), None, None)
    with pytest.raises(Exception):
        router.add("/:id", "GET", handler_factory(), None, None)


def test_different_method():
    get_handler = handler_factory()
    post_handler = handler_factory()
    router = Router()
    router.add("/:id", "GET", get_handler, None, None)
    router.add("/:id", "POST", post_handler, None, None)
    assert router.lookup("/123", "http", "GET") == (get_handler, None, {"id": "123"})
    assert router.lookup("/123", "http", "POST") == (post_handler, None, {"id": "123"})


def test_param_route_duplicate_different_names_raises():
    router = Router()
    router.add("/items/:id", "GET", handler_factory(), None, None)
    with pytest.raises(Exception):
        # Adding equivalent param route with different name should raise error
        router.add("/items/:name", "GET", handler_factory(), None, None)


def test_overlapping_routes_static_and_param_static_match():
    h = handler_factory()
    router = Router()
    router.add("/shop/books", "GET", h, None, None)
    router.add("/shop/:category", "GET", handler_factory(), None, None)
    assert router.lookup("/shop/books", "http", "GET") == (h, None, {})


def test_overlapping_routes_static_and_param_parameter_match():
    h = handler_factory()
    router = Router()
    router.add("/shop/books", "GET", handler_factory(), None, None)
    router.add("/shop/:category", "GET", h, None, None)
    assert router.lookup("/shop/electronics", "http", "GET") == (h, None, {"category": "electronics"})


def test_overlapping_routes_static_and_param_static_vs_parameter_in_deeper_path_static_match():
    h = handler_factory()
    router = Router()
    router.add("/a/x/b", "GET", h, None, None)
    router.add("/a/:id/b", "GET", handler_factory(), None, None)
    assert router.lookup("/a/x/b", "http", "GET") == (h, None, {})


def test_overlapping_routes_static_and_param_static_vs_parameter_in_deeper_path_parameter_match():
    h = handler_factory()
    router = Router()
    router.add("/a/x/b", "GET", handler_factory(), None, None)
    router.add("/a/:id/b", "GET", h, None, None)
    assert router.lookup("/a/y/b", "http", "GET") == (h, None, {"id": "y"})


def test_param_name_reuse_in_separate_branches_l():
    h = handler_factory()
    router = Router()
    router.add("/a/:id/x", "GET", h, None, None)
    router.add("/b/:id/y", "GET", handler_factory(), None, None)
    assert router.lookup("/a/y/x", "http", "GET") == (h, None, {"id": "y"})


def test_param_name_reuse_in_separate_branches_r():
    h = handler_factory()
    router = Router()
    router.add("/a/:id/x", "GET", handler_factory(), None, None)
    router.add("/b/:id/y", "GET", h, None, None)
    assert router.lookup("/b/t/y", "http", "GET") == (h, None, {"id": "t"})
