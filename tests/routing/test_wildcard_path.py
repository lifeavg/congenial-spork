import pytest
from util import handler_factory

from src.router import Router


def test_http_insertion_and_lookup():
    h = handler_factory()
    router = Router()
    router.add("/*path", "GET", h, None, None)
    assert router.lookup("/user", "http", "GET") == (h, None, {"path": "user"})


def test_http_lookup_any_path():
    h = handler_factory()
    router = Router()
    router.add("/*path", "GET", h, None, None)
    assert router.lookup("/user/bla/n", "http", "GET") == (h, None, {"path": "user/bla/n"})


def test_http_empty_lookup():
    h = handler_factory()
    router = Router()
    router.add("/*path", "GET", h, None, None)
    assert router.lookup("/", "http", "GET") == (None, None, {})


def test_http_empty_subpath():
    h = handler_factory()
    router = Router()
    router.add("/root/*path", "GET", h, None, None)
    assert router.lookup("/root", "http", "GET") == (h, None, {"path": ""})


def test_http_static_if_no_subpath():
    h = handler_factory()
    router = Router()
    router.add("/root/*path", "GET", handler_factory(), None, None)
    router.add("/root", "GET", h, None, None)
    assert router.lookup("/root", "http", "GET") == (h, None, {})


def test_http_subpath_not_empty():
    h = handler_factory()
    router = Router()
    router.add("/root/*path", "GET", h, None, None)
    router.add("/root", "GET", handler_factory(), None, None)
    assert router.lookup("/root/a/b/c", "http", "GET") == (h, None, {"path": "a/b/c"})


def test_static_over_wildcard_precedence():
    h = handler_factory()
    router = Router()
    router.add("/root/static", "GET", h, None, None)
    router.add("/root/*path", "GET", handler_factory(), None, None)
    assert router.lookup("/root/static", "http", "GET") == (h, None, {})


def test_wildcard_over_static_precedence_for_deeper_paths_beyond_static_route():
    h = handler_factory()
    router = Router()
    router.add("/root/static", "GET", handler_factory(), None, None)
    router.add("/root/*path", "GET", h, None, None)
    assert router.lookup("/root/static/more", "http", "GET") == (h, None, {"path": "static/more"})


def test_route_precedence_static_param_wildcard_matches_exact_path():
    h = handler_factory()
    router = Router()
    router.add("/a/static", "GET", h, None, None)
    router.add("/a/:id", "GET", handler_factory(), None, None)
    router.add("/a/*path", "GET", handler_factory(), None, None)
    assert router.lookup("/a/static", "http", "GET") == (h, None, {})


def test_route_precedence_static_param_wildcard_match_when_static_does_not():
    h = handler_factory()
    router = Router()
    router.add("/a/static", "GET", handler_factory(), None, None)
    router.add("/a/:id", "GET", h, None, None)
    router.add("/a/*path", "GET", handler_factory(), None, None)
    assert router.lookup("/a/123", "http", "GET") == (h, None, {"id": "123"})


def test_route_precedence_static_param_wildcard_match_additional_segments():
    h = handler_factory()
    router = Router()
    router.add("/a/static", "GET", handler_factory(), None, None)
    router.add("/a/:id", "GET", handler_factory(), None, None)
    router.add("/a/*path", "GET", h, None, None)
    assert router.lookup("/a/b/c", "http", "GET") == (h, None, {"path": "b/c"})


def test_duplicate_wildcard_route_raises():
    router = Router()
    router.add("/a/*path", "GET", handler_factory(), None, None)
    with pytest.raises(Exception):
        router.add("/a/*path", "GET", handler_factory(), None, None)


def test_wildcard_not_last_raises():
    router = Router()
    with pytest.raises(Exception):
        router.add("/a/*path/b", "GET", handler_factory(), None, None)


def test_raises_double_wildcard():
    router = Router()
    with pytest.raises(Exception):
        router.add("/x/*a/*b", "GET", handler_factory(), None, None)


def test_invalid_pattern():
    router = Router()
    with pytest.raises(Exception):
        router.add("/x/:a/:b*", "GET", handler_factory(), None, None)


def test_raises_unnamed_wildcard():
    router = Router()
    with pytest.raises(Exception):
        router.add("/x/*", "GET", handler_factory(), None, None)


def test_wildcard_under_param():
    h = handler_factory()
    router = Router()
    router.add("/a/:id/*rest", "GET", h, None, None)
    assert router.lookup("/a/123/x/y", "http", "GET") == (h, None, {"id": "123", "rest": "x/y"})


def test_param_then_wildcard_vs_deep_static_param_matches_wildcard():
    h = handler_factory()
    router = Router()
    router.add("/a/:id/*rest", "GET", h, None, None)
    router.add("/a/123/b/c", "GET", handler_factory(), None, None)
    assert router.lookup("/a/999/x/y", "http", "GET") == (h, None, {"id": "999", "rest": "x/y"})


def test_param_then_wildcard_vs_deep_static_static_matches_static():
    h = handler_factory()
    router = Router()
    router.add("/a/:id/*rest", "GET", handler_factory(), None, None)
    router.add("/a/123/b/c", "GET", h, None, None)
    assert router.lookup("/a/123/b/c", "http", "GET") == (h, None, {})


def test_param_dead_end_falls_back_to_wildcard_param():
    h = handler_factory()
    router = Router()
    router.add("/a/:id/b", "GET", h, None, None)
    router.add("/a/*rest", "GET", handler_factory(), None, None)
    assert router.lookup("/a/123/b", "http", "GET") == (h, None, {"id": "123"})


def test_param_dead_end_falls_back_to_wildcard_wildcard():
    h = handler_factory()
    router = Router()
    router.add("/a/:id/b", "GET", handler_factory(), None, None)
    router.add("/a/*rest", "GET", h, None, None)
    assert router.lookup("/a/123/x", "http", "GET") == (h, None, {"rest": "123/x"})


def test_two_params_vs_wildcard_two_params():
    h = handler_factory()
    router = Router()
    router.add("/a/:x/:y", "GET", h, None, None)
    router.add("/a/*rest", "GET", handler_factory(), None, None)
    assert router.lookup("/a/1/2", "http", "GET") == (h, None, {"x": "1", "y": "2"})


def test_two_params_vs_wildcard_wildcard():
    h = handler_factory()
    router = Router()
    router.add("/a/:x/:y", "GET", handler_factory(), None, None)
    router.add("/a/*rest", "GET", h, None, None)
    assert router.lookup("/a/1/2/3", "http", "GET") == (h, None, {"rest": "1/2/3"})


def test_param_shadowing_deeper_wildcard_parameter_then_wildcard():
    h = handler_factory()
    router = Router()
    router.add("/a/:id/b/*rest", "GET", h, None, None)
    router.add("/a/:id/*rest", "GET", handler_factory(), None, None)
    assert router.lookup("/a/1/b/c", "http", "GET") == (h, None, {"id": "1", "rest": "c"})


def test_param_shadowing_deeper_wildcard_path_to_wildcard():
    h = handler_factory()
    router = Router()
    router.add("/a/:id/b/*rest", "GET", handler_factory(), None, None)
    router.add("/a/:id/*rest", "GET", h, None, None)
    assert router.lookup("/a/1/x/y", "http", "GET") == (h, None, {"id": "1", "rest": "x/y"})


def test_multiple_wildcards_different_levels_wildcard_deeper():
    h = handler_factory()
    router = Router()
    router.add("/a/*rest", "GET", handler_factory(), None, None)
    router.add("/a/b/*rest", "GET", h, None, None)
    assert router.lookup("/a/b/c/d", "http", "GET") == (h, None, {"rest": "c/d"})


def test_multiple_wildcards_different_levels_wildcard_first():
    h = handler_factory()
    router = Router()
    router.add("/a/*rest", "GET", h, None, None)
    router.add("/a/b/*rest", "GET", handler_factory(), None, None)
    assert router.lookup("/a/x/y/z", "http", "GET") == (h, None, {"rest": "x/y/z"})
