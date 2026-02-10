import pytest
from util import handler_factory, middleware_factory, Connection

from src.router import Router


def test_mount():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    products_handler = handler_factory()
    sub_router.add("/users", "GET", users_handler, None, None)
    sub_router.add("/products", "POST", products_handler, None, None)
    main_router.mount("/", sub_router)
    assert main_router.lookup("/users", "http", "GET") == (users_handler, None, {})
    assert main_router.lookup("/products", "http", "POST") == (products_handler, None, {})


def test_mount_websocket():
    main_router = Router()
    sub_router = Router()
    ws_handler = handler_factory()
    sub_router.add("/users", None, None, None, ws_handler)
    main_router.mount("/", sub_router)
    assert main_router.lookup("/users", "ws", "GET") == (None, ws_handler, {})


def test_mount_parameter():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    sub_router.add("/:id", "GET", users_handler, None, None)
    main_router.mount("/", sub_router)
    assert main_router.lookup("/123", "http", "GET") == (users_handler, None, {"id": "123"})


def test_mount_path():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    sub_router.add("/*path", "GET", users_handler, None, None)
    main_router.mount("/", sub_router)
    assert main_router.lookup("/sme/rt/to/hl", "http", "GET") == (users_handler, None, {"path": "sme/rt/to/hl"})


def test_non_empty_mount_parameter():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    another_handler = handler_factory()
    main_router.add("/another", "GET", another_handler, None, None)
    sub_router.add("/:id", "GET", users_handler, None, None)
    main_router.mount("/", sub_router)
    assert main_router.lookup("/123", "http", "GET") == (users_handler, None, {"id": "123"})
    assert main_router.lookup("/another", "http", "GET") == (another_handler, None, {})


def test_non_empty_mount_path():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    another_handler = handler_factory()
    main_router.add("/another", "GET", another_handler, None, None)
    sub_router.add("/*path", "GET", users_handler, None, None)
    main_router.mount("/", sub_router)
    assert main_router.lookup("/sme/rt/to/hl", "http", "GET") == (users_handler, None, {"path": "sme/rt/to/hl"})
    assert main_router.lookup("/another", "http", "GET") == (another_handler, None, {})


@pytest.mark.asyncio()
async def test_mount_with_middleware():
    main_router = Router()
    sub_router = Router()
    sub_handler = handler_factory()
    sub_router.add("/test", "GET", sub_handler, middleware_factory("sub"), None)
    main_router.mount("/", sub_router)
    handler, _, _ = main_router.lookup("/test", "http", "GET")
    assert handler is not None
    c = Connection()
    await handler({}, c.receive, c.send)
    assert c.data == "sub r sub"


@pytest.mark.asyncio()
async def test_mount_middleware_composition():
    main_router = Router()
    sub_router = Router()
    main_router.add("/", None, None, middleware_factory("mn"), None)
    sub_handler = handler_factory()
    sub_router.add("/test", "GET", sub_handler, middleware_factory("sub"), None)
    main_router.mount("/", sub_router)
    handler, _, _ = main_router.lookup("/test", "http", "GET")
    assert handler is not None
    c = Connection()
    await handler({}, c.receive, c.send)
    assert c.data == "mn sub r sub mn"
