import pytest
from util import handler_factory, middleware_factory

from src.router import Router


def test_mount():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    products_handler = handler_factory()
    sub_router.add("/users", "GET", users_handler, None, None)
    sub_router.add("/products", "POST", products_handler, None, None)
    main_router.mount("/:id", sub_router)
    assert main_router.lookup("/sub/users", "http", "GET") == (users_handler, None, {"id": "sub"})
    assert main_router.lookup("/sub/products", "http", "POST") == (products_handler, None, {"id": "sub"})


def test_mount_existing():
    main_router = Router()
    main_handler = handler_factory()
    main_router.add("/:id", "GET", main_handler, None, None)
    sub_router = Router()
    users_handler = handler_factory()
    products_handler = handler_factory()
    sub_router.add("/users", "GET", users_handler, None, None)
    sub_router.add("/products", "POST", products_handler, None, None)
    main_router.mount("/:id", sub_router)
    assert main_router.lookup("/sub/users", "http", "GET") == (users_handler, None, {"id": "sub"})
    assert main_router.lookup("/sub/products", "http", "POST") == (products_handler, None, {"id": "sub"})
    assert main_router.lookup("/sub", "http", "GET") == (main_handler, None, {"id": "sub"})


def test_mount_websocket():
    main_router = Router()
    sub_router = Router()
    ws_handler = handler_factory()
    sub_router.add("/:id", None, None, None, ws_handler)
    main_router.mount("/sub", sub_router)
    assert main_router.lookup("/sub/users", "ws", "GET") == (None, ws_handler, {"id": "users"})


def test_mount_parameter():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    sub_router.add("/:id", "GET", users_handler, None, None)
    main_router.mount("/:val", sub_router)
    assert main_router.lookup("/sub/123", "http", "GET") == (users_handler, None, {"id": "123", "val": "sub"})


def test_mount_parameter_existing():
    main_router = Router()
    main_handler = handler_factory()
    main_router.add("/:val", "GET", main_handler, None, None)
    sub_router = Router()
    users_handler = handler_factory()
    sub_router.add("/:id", "GET", users_handler, None, None)
    main_router.mount("/:val", sub_router)
    assert main_router.lookup("/sub/123", "http", "GET") == (users_handler, None, {"id": "123", "val": "sub"})
    assert main_router.lookup("/sub", "http", "GET") == (main_handler, None, {"val": "sub"})


def test_mount_path():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    sub_router.add("/*path", "GET", users_handler, None, None)
    main_router.mount("/:val", sub_router)
    assert main_router.lookup("/sub/sme/rt/to/hl", "http", "GET") == (
        users_handler,
        None,
        {"path": "sme/rt/to/hl", "val": "sub"},
    )


def test_mount_path_existing():
    main_router = Router()
    main_handler = handler_factory()
    main_router.add("/:val", "GET", main_handler, None, None)
    sub_router = Router()
    users_handler = handler_factory()
    sub_router.add("/*path", "GET", users_handler, None, None)
    main_router.mount("/:val", sub_router)
    assert main_router.lookup("/sub/sme/rt/to/hl", "http", "GET") == (
        users_handler,
        None,
        {"path": "sme/rt/to/hl", "val": "sub"},
    )
    assert main_router.lookup("/sub", "http", "GET") == (main_handler, None, {"val": "sub"})


def test_non_empty_mount_path():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    another_handler = handler_factory()
    main_router.add("/sub/:val", "GET", another_handler, None, None)
    sub_router.add("/*path", "GET", users_handler, None, None)
    main_router.mount("/sub", sub_router)
    assert main_router.lookup("/sub/sme/rt/to/hl", "http", "GET") == (users_handler, None, {"path": "sme/rt/to/hl"})
    assert main_router.lookup("/sub/another", "http", "GET") == (another_handler, None, {"val": "another"})


@pytest.mark.asyncio()
async def test_mount_with_middleware():
    main_router = Router()
    sub_router = Router()
    sub_handler = handler_factory()
    sub_router.add("/test", "GET", sub_handler, middleware_factory("s"), None)
    main_router.mount("/:val", sub_router)
    handler, _, params = main_router.lookup("/sub/test", "http", "GET")
    assert handler is not None
    assert params == {"val": "sub"}
    assert await handler("r") == "s r s"


@pytest.mark.asyncio()
async def test_mount_middleware_composition():
    main_router = Router()
    sub_router = Router()
    main_router.add("/:val", None, None, middleware_factory("mn"), None)
    sub_handler = handler_factory()
    sub_router.add("/test", "GET", sub_handler, middleware_factory("sub"), None)
    main_router.mount("/:val", sub_router)
    handler, _, params = main_router.lookup("/sub/test", "http", "GET")
    assert handler is not None
    assert params == {"val": "sub"}
    assert await handler("r") == "mn sub r sub mn"


def test_mount_conflict_detection():
    main_router = Router()
    sub_router = Router()
    main_router.add("/:val/users", "GET", handler_factory(), None, None)
    sub_router.add("/users", "GET", handler_factory(), None, None)
    with pytest.raises(ValueError):
        main_router.mount("/:val", sub_router)


def test_mount_parameter_conflict_tail():
    main_router = Router()
    sub_router = Router()
    users_handler = handler_factory()
    another_handler = handler_factory()
    main_router.add("/sub/:val", "GET", another_handler, None, None)
    sub_router.add("/:id", "GET", users_handler, None, None)
    with pytest.raises(ValueError):
        main_router.mount("/sub", sub_router)
