from util import handler_factory, middleware_factory, new_router


def test_mount_multiple_routers():
    main_router = new_router()
    users_router = new_router()
    posts_router = new_router()

    # Create handlers
    users_handler = handler_factory()
    posts_handler = handler_factory()
    users_ws_handler = handler_factory()
    posts_ws_handler = handler_factory()

    # Add routes to sub-routers
    users_router.add("/list", "GET", users_handler, None, users_ws_handler)
    posts_router.add("/recent", "GET", posts_handler, None, posts_ws_handler)

    # Mount both routers
    main_router.mount("/users", users_router)
    main_router.mount("/posts", posts_router)

    # Test both mounted routes
    handler, _, _ = main_router.lookup("/users/list", "http", "GET")
    assert handler == users_handler

    handler, _, _ = main_router.lookup("/posts/recent", "http", "GET")
    assert handler == posts_handler

    _, handler, _ = main_router.lookup("/users/list", "ws")
    assert handler == users_ws_handler

    _, handler, _ = main_router.lookup("/posts/recent", "ws")
    assert handler == posts_ws_handler


def test_mount_preserves_precedence():
    """Test that route precedence is maintained after mounting."""
    main_router = new_router()

    # Create sub-routes
    static_router = new_router()
    static_handler = handler_factory()
    static_router.add("/specific", "GET", static_handler, None, None)

    param_router = new_router()
    param_handler = handler_factory()
    param_router.add("/:id", "POST", param_handler, None, None)

    wildcard_router = new_router()
    wildcard_handler = handler_factory()
    wildcard_router.add("/*path", "PUT", wildcard_handler, None, None)

    # Mount sub-routers
    main_router.mount("/api", static_router)
    main_router.mount("/api", param_router)
    main_router.mount("/api", wildcard_router)

    # Test precedence is maintained
    handler, _, params = main_router.lookup("/api/specific", "http", "GET")
    assert handler == static_handler
    assert params == {}

    handler, _, params = main_router.lookup("/api/123", "http", "POST")
    assert handler == param_handler
    assert params == {"id": "123"}

    handler, _, params = main_router.lookup("/api/path/to/resource", "http", "PUT")
    assert handler == wildcard_handler
    assert params == {"path": "path/to/resource"}


def test_mount_merge_handlers():
    main_router = new_router()
    get_handler = handler_factory()
    main_router.add("/api/data", "GET", get_handler, None, None)

    post_router = new_router()
    post_handler = handler_factory()
    post_router.add("/data", "POST", post_handler, None, None)

    put_router = new_router()
    put_handler = handler_factory()
    put_router.add("/api/data", "PUT", put_handler, None, None)

    ws_router = new_router()
    ws_handler = handler_factory()
    ws_router.add("/data", None, None, None, ws_handler)

    # Mount sub-router
    main_router.mount("/api", post_router)
    main_router.mount("/", put_router)
    main_router.mount("/api", ws_router)

    # Both routes should be accessible
    handler, _, _ = main_router.lookup("/api/data", "http", "GET")
    assert handler == get_handler

    handler, _, _ = main_router.lookup("/api/data", "http", "POST")
    assert handler == post_handler

    handler, _, _ = main_router.lookup("/api/data", "http", "PUT")
    assert handler == put_handler

    _, handler, _ = main_router.lookup("/api/data", "ws")
    assert handler == ws_handler


def test_mount_with_middleware_hierarchy():
    """Test mounting maintains middleware hierarchy properly."""
    main_router = new_router()

    # Add middleware to main router at mount point
    main_router.add("/", None, None, middleware_factory("rt"), None)

    # Add route with middleware to sub-router
    sub_router = new_router()
    sub_router.add("/test", None, None, middleware_factory("ts"), None)

    handler_router = new_router()
    handler_router.add("/test/user", "GET", handler_factory(), middleware_factory("hh"), None)

    # Mount sub-router
    main_router.mount("/api", sub_router)
    main_router.mount("/api", handler_router)

    # Get handler and check middleware application
    handler, _, _ = main_router.lookup("/api/test/user", "http", "GET")
    assert handler is not None
    assert handler("r") == "rt ts hh r hh ts rt"
