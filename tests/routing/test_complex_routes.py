from util import handler_factory, new_router


def test_diamond_branching():
    h_static = handler_factory()
    h_param = handler_factory()
    h_wildcard = handler_factory()
    router = new_router()
    router.add("/x/static/end", "GET", h_static, None, None)
    router.add("/x/:id/end", "GET", h_param, None, None)
    router.add("/x/*rest", "GET", h_wildcard, None, None)
    assert router.lookup("/x/static/end", "http", "GET") == (h_static, None, {})
    assert router.lookup("/x/123/end", "http", "GET") == (h_param, None, {"id": "123"})
    assert router.lookup("/x/123/other", "http", "GET") == (h_wildcard, None, {"rest": "123/other"})


def test_nested_wildcard_forks():
    h_static_wildcard = handler_factory()
    h_param_static = handler_factory()
    h_param_wildcard = handler_factory()
    router = new_router()
    router.add("/a/b/*rest", "GET", h_static_wildcard, None, None)
    router.add("/a/:id/c/*rest", "GET", h_param_static, None, None)
    router.add("/a/:id/*rest", "GET", h_param_wildcard, None, None)
    assert router.lookup("/a/b/x/y", "http", "GET") == (h_static_wildcard, None, {"rest": "x/y"})
    assert router.lookup("/a/1/c/d/e", "http", "GET") == (h_param_static, None, {"id": "1", "rest": "d/e"})
    assert router.lookup("/a/1/x/y", "http", "GET") == (h_param_wildcard, None, {"id": "1", "rest": "x/y"})
