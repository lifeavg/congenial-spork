import pytest

from util import handler_factory, new_router


def test_mount_not_allowed_after():
    main_router = new_router()
    sub_router = new_router()
    users_handler = handler_factory()
    products_handler = handler_factory()
    sub_router.add("/users", "GET", users_handler, None, None)
    sub_router.add("/products", "POST", products_handler, None, None)
    with pytest.raises(ValueError):
        main_router.mount("/*path", sub_router)


def test_mount_websocket_not_allowed_after():
    main_router = new_router()
    sub_router = new_router()
    ws_handler = handler_factory()
    sub_router.add("/:id", None, None, None, ws_handler)
    with pytest.raises(ValueError):
        main_router.mount("/*path", sub_router)


def test_mount_path_not_allowed_after():
    main_router = new_router()
    sub_router = new_router()
    products_handler = handler_factory()
    sub_router.add("/*path_two", "POST", products_handler, None, None)
    with pytest.raises(ValueError):
        main_router.mount("/*path", sub_router)
