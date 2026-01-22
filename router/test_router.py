import pytest

# Assuming the RadixRouter is defined in radix_router module
from router import RadixRouter


# Test 1: Static route insertion and lookup
# Static route should match exactly and return associated data [oai_citation:0‡packagist.org](https://packagist.org/packages/wilaak/radix-router#:~:text=You%20can%20provide%20any%20value,wildcard)
def test_static_route_insertion_and_lookup():
    router = RadixRouter()
    router.add("/home", "home_handler")
    assert router.lookup("/home") == ("home_handler", {})


def test_static_route_not_match_non_identical_paths():
    router = RadixRouter()
    router.add("/home", "home_handler")
    assert router.lookup("/home/other") == (None, {})


# Test 2: Parameterized route insertion and lookup
# Parameterized segments (e.g., :id) capture corresponding path parts into params [oai_citation:1‡hexshift.medium.com](https://hexshift.medium.com/building-dynamic-routing-with-parameters-in-a-minimal-python-web-framework-cb847ec0ec7c#:~:text=pattern%20starts%20with%20a%20colon%2C,view%20function%20can%20access%20it)
def test_param_route_insertion_and_lookup():
    router = RadixRouter()
    router.add("/users/:id", "user_handler")
    assert router.lookup("/users/123") == ("user_handler", {"id": "123"})


def test_param_route_insertion_and_lookup_multiple_params():
    router = RadixRouter()
    router.add("/users/:id", "user_handler")
    router.add("/posts/:category/:post_id", "post_handler")
    assert router.lookup("/posts/news/456") == ("post_handler", {"category": "news", "post_id": "456"})


def test_param_route_duplicate_different_names_raises():
    router = RadixRouter()
    router.add("/items/:id", "handler1")
    with pytest.raises(Exception):
        # Adding equivalent param route with different name should raise error
        router.add("/items/:name", "handler2")


# Test 3: Wildcard route insertion and lookup
# Wildcard segments (e.g., *path) capture all remaining path segments into a named parameter [oai_citation:2‡docs.rs](https://docs.rs/route-recognizer/latest/route_recognizer/#:~:text=because%20,in%20the%20router)
def test_wildcard_route_insertion_and_lookup():
    router = RadixRouter()
    router.add("/files/*path", "file_handler")
    assert router.lookup("/files/a/b/c") == ("file_handler", {"path": "a/b/c"})


def test_wildcard_route_insertion_and_lookup_empty_tail():
    router = RadixRouter()
    router.add("/files/*path", "file_handler")
    assert router.lookup("/files") == ("file_handler", {"path": ""})


# Test 4: Static route takes precedence over wildcard route
def test_static_over_wildcard_precedence():
    router = RadixRouter()
    router.add("/files/images", "img_handler")
    router.add("/files/*path", "file_handler")
    # Static route should take precedence over wildcard [oai_citation:3‡packagist.org](https://packagist.org/packages/wilaak/radix-router#:~:text=You%20can%20provide%20any%20value,wildcard)
    assert router.lookup("/files/images") == ("img_handler", {})


def test_static_over_wildcard_precedence_match_deeper_paths_beyond_static_route():
    router = RadixRouter()
    router.add("/files/images", "img_handler")
    router.add("/files/*path", "file_handler")
    # Static route should take precedence over wildcard [oai_citation:3‡packagist.org](https://packagist.org/packages/wilaak/radix-router#:~:text=You%20can%20provide%20any%20value,wildcard)
    assert router.lookup("/files/docs/readme.txt") == ("file_handler", {"path": "docs/readme.txt"})


# Test 5: Route precedence static > param > wildcard
def test_route_precedence_static_param_wildcard_matches_exact_path():
    router = RadixRouter()
    router.add("/a/static", "static_handler")
    router.add("/a/:id", "param_handler")
    router.add("/a/*path", "wild_handler")
    assert router.lookup("/a/static") == ("static_handler", {})


def test_route_precedence_static_param_wildcard_match_when_static_does_not():
    router = RadixRouter()
    router.add("/a/static", "static_handler")
    router.add("/a/:id", "param_handler")
    router.add("/a/*path", "wild_handler")
    # Param route should match when static doesn't, static > param > wildcard [oai_citation:4‡packagist.org](https://packagist.org/packages/wilaak/radix-router#:~:text=You%20can%20provide%20any%20value,wildcard)
    assert router.lookup("/a/xyz") == ("param_handler", {"id": "xyz"})


def test_route_precedence_static_param_wildcard_match_additional_segments():
    router = RadixRouter()
    router.add("/a/static", "static_handler")
    router.add("/a/:id", "param_handler")
    router.add("/a/*path", "wild_handler")
    assert router.lookup("/a/xyz/other") == ("wild_handler", {"path": "xyz/other"})


# Test 6: Duplicate route insertion should raise error
def test_duplicate_static_route_raises():
    router = RadixRouter()
    router.add("/duplicate", "handler")
    with pytest.raises(Exception):
        router.add("/duplicate", "handler2")


def test_duplicate_wildcard_route_raises():
    router = RadixRouter()
    router.add("/docs/*path", "handler1")
    with pytest.raises(Exception):
        # Equivalent wildcard with different param name should error
        router.add("/docs/*other", "handler2")


# Test 7: Empty and root path handling
def test_root_path_handling():
    router = RadixRouter()
    router.add("/", "root_handler")
    assert router.lookup("/") == ("root_handler", {})


def test_root_path_handling_empty_path_lookup_treated_as_root():
    router = RadixRouter()
    router.add("/", "root_handler")
    assert router.lookup("") == ("root_handler", {})


def test_empty_path_insertion_raises():
    router = RadixRouter()
    with pytest.raises(Exception):
        # Routes should start with '/'
        router.add("", "nope")


# Test 8: Overlapping routes (static vs parameter segments)
def test_overlapping_routes_static_and_param_static_match():
    router = RadixRouter()
    router.add("/shop/books", "books_handler")
    router.add("/shop/:category", "category_handler")
    # Static '/shop/books' should match over '/shop/:category' [oai_citation:5‡packagist.org](https://packagist.org/packages/wilaak/radix-router#:~:text=You%20can%20provide%20any%20value,wildcard)
    assert router.lookup("/shop/books") == ("books_handler", {})


def test_overlapping_routes_static_and_param_parameter_match():
    router = RadixRouter()
    router.add("/shop/books", "books_handler")
    router.add("/shop/:category", "category_handler")
    # Static '/shop/books' should match over '/shop/:category' [oai_citation:5‡packagist.org](https://packagist.org/packages/wilaak/radix-router#:~:text=You%20can%20provide%20any%20value,wildcard)
    assert router.lookup("/shop/electronics") == ("category_handler", {"category": "electronics"})


def test_overlapping_routes_static_and_param_static_vs_parameter_in_deeper_path_static_match():
    # Static vs parameter in deeper path
    router = RadixRouter()
    router.add("/a/x/b", "static_nested")
    router.add("/a/:id/b", "param_nested")
    assert router.lookup("/a/x/b") == ("static_nested", {})


def test_overlapping_routes_static_and_param_static_vs_parameter_in_deeper_path_parameter_match():
    # Static vs parameter in deeper path
    router = RadixRouter()
    router.add("/a/x/b", "static_nested")
    router.add("/a/:id/b", "param_nested")
    assert router.lookup("/a/y/b") == ("param_nested", {"id": "y"})


# Test 9: Parameter route vs wildcard route precedence
def test_param_vs_wildcard_precedence_param_match():
    router = RadixRouter()
    router.add("/data/:id", "param_handler")
    router.add("/data/*path", "wild_handler")
    # Parameter route should match a single segment (parameter > wildcard) [oai_citation:6‡packagist.org](https://packagist.org/packages/wilaak/radix-router#:~:text=You%20can%20provide%20any%20value,wildcard)
    assert router.lookup("/data/123") == ("param_handler", {"id": "123"})


def test_param_vs_wildcard_precedence_wildcard_match():
    router = RadixRouter()
    router.add("/data/:id", "param_handler")
    router.add("/data/*path", "wild_handler")
    # Parameter route should match a single segment (parameter > wildcard) [oai_citation:6‡packagist.org](https://packagist.org/packages/wilaak/radix-router#:~:text=You%20can%20provide%20any%20value,wildcard)
    assert router.lookup("/data/123/more") == ("wild_handler", {"path": "123/more"})


# Test 10: Wildcard misuse (wildcard not last) should raise error
def test_wildcard_not_last_raises():
    router = RadixRouter()
    with pytest.raises(Exception):
        router.add("/a/*path/b", "invalid")


# Test 11: Multiple wildcards or invalid patterns should raise error
def test_multiple_wildcards_or_invalid_patterns_raises_double_wildcard():
    router = RadixRouter()
    with pytest.raises(Exception):
        router.add("/x/*a/*b", "double_wildcard")


def test_multiple_wildcards_or_invalid_patterns_raises_invalid_pattern():
    router = RadixRouter()
    with pytest.raises(Exception):
        router.add("/x/:a/:b*", "invalid_pattern")


def test_multiple_wildcards_or_invalid_patterns_raises_unnamed_wildcard():
    router = RadixRouter()
    with pytest.raises(Exception):
        router.add("/x/*", "unnamed_wildcard")


def test_wildcard_matches_single_segment():
    router = RadixRouter()
    router.add("/x/*rest", "h")
    assert router.lookup("/x/a") == ("h", {"rest": "a"})


def test_wildcard_does_not_override_static():
    router = RadixRouter()
    router.add("/x/y", "static")
    router.add("/x/*rest", "wild")
    assert router.lookup("/x/y") == ("static", {})


def test_param_does_not_override_static():
    router = RadixRouter()
    router.add("/x/y", "static")
    router.add("/x/:id", "param")
    assert router.lookup("/x/y") == ("static", {})


def test_wildcard_under_param():
    router = RadixRouter()
    router.add("/a/:id/*rest", "h")
    assert router.lookup("/a/123/x/y") == ("h", {"id": "123", "rest": "x/y"})


# ------
def test_param_then_wildcard_vs_deep_static_param_wild():
    router = RadixRouter()
    router.add("/a/:id/*rest", "param_wild")
    router.add("/a/123/b/c", "static_deep")
    assert router.lookup("/a/999/x/y") == ("param_wild", {"id": "999", "rest": "x/y"})


def test_param_then_wildcard_vs_deep_static_static_deep():
    router = RadixRouter()
    router.add("/a/:id/*rest", "param_wild")
    router.add("/a/123/b/c", "static_deep")
    assert router.lookup("/a/123/b/c") == ("static_deep", {})


def test_param_dead_end_falls_back_to_wildcard_param():
    router = RadixRouter()
    router.add("/a/:id/b", "param_b")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/123/b") == ("param_b", {"id": "123"})


def test_param_dead_end_falls_back_to_wildcard_wildcard():
    router = RadixRouter()
    router.add("/a/:id/b", "param_b")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/123/x") == ("wild", {"rest": "123/x"})


def test_two_params_vs_wildcard_two_params():
    router = RadixRouter()
    router.add("/a/:x/:y", "two_params")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/1/2") == ("two_params", {"x": "1", "y": "2"})


def test_two_params_vs_wildcard_wildcard():
    router = RadixRouter()
    router.add("/a/:x/:y", "two_params")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/1/2/3") == ("wild", {"rest": "1/2/3"})


def test_param_shadowing_deeper_wildcard_param_then_wild():
    router = RadixRouter()
    router.add("/a/:id/b/*rest", "param_then_wild")
    router.add("/a/:id/*rest", "param_wild")
    assert router.lookup("/a/1/b/c") == ("param_then_wild", {"id": "1", "rest": "c"})


def test_param_shadowing_deeper_wildcard_param_wild():
    router = RadixRouter()
    router.add("/a/:id/b/*rest", "param_then_wild")
    router.add("/a/:id/*rest", "param_wild")
    assert router.lookup("/a/1/x/y") == ("param_wild", {"id": "1", "rest": "x/y"})


def test_multiple_wildcards_different_levels_wild_deeper():
    router = RadixRouter()
    router.add("/a/*rest", "wild_root")
    router.add("/a/b/*rest", "wild_deeper")
    assert router.lookup("/a/b/c/d") == ("wild_deeper", {"rest": "c/d"})


def test_multiple_wildcards_different_levels_wild_root():
    router = RadixRouter()
    router.add("/a/*rest", "wild_root")
    router.add("/a/b/*rest", "wild_deeper")
    assert router.lookup("/a/x/y") == ("wild_root", {"rest": "x/y"})


def test_static_inside_param_beats_wildcard_param_static():
    router = RadixRouter()
    router.add("/a/:id/b", "param_static")
    router.add("/a/:id/*rest", "param_wild")
    assert router.lookup("/a/1/b") == ("param_static", {"id": "1"})


def test_static_inside_param_beats_wildcard_param_wild():
    router = RadixRouter()
    router.add("/a/:id/b", "param_static")
    router.add("/a/:id/*rest", "param_wild")
    assert router.lookup("/a/1/b/c") == ("param_wild", {"id": "1", "rest": "b/c"})


def test_wildcard_empty_vs_nonempty():
    router = RadixRouter()
    router.add("/a/b/*rest", "wild")
    assert router.lookup("/a/b") == ("wild", {"rest": ""})


def test_wildcard_empty_vs_nonempty_trailing_slash():
    router = RadixRouter()
    router.add("/a/b/*rest", "wild")
    assert router.lookup("/a/b/") == ("wild", {"rest": ""})


def test_wildcard_empty_vs_nonempty_nonempty():
    router = RadixRouter()
    router.add("/a/b/*rest", "wild")
    assert router.lookup("/a/b/c") == ("wild", {"rest": "c"})


def test_param_name_reuse_in_separate_branches_l():
    router = RadixRouter()
    router.add("/a/:id/x", "ax")
    router.add("/b/:id/y", "by")
    assert router.lookup("/a/1/x") == ("ax", {"id": "1"})


def test_param_name_reuse_in_separate_branches_r():
    router = RadixRouter()
    router.add("/a/:id/x", "ax")
    router.add("/b/:id/y", "by")
    assert router.lookup("/b/2/y") == ("by", {"id": "2"})


def test_param_and_wildcard_same_node_param():
    router = RadixRouter()
    router.add("/a/:id", "param")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/1") == ("param", {"id": "1"})


def test_param_and_wildcard_same_node_wild():
    router = RadixRouter()
    router.add("/a/:id", "param")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/1/x") == ("wild", {"rest": "1/x"})


def test_deep_fallback_chain_static():
    router = RadixRouter()
    router.add("/a/b/c", "static")
    router.add("/a/:x/c", "param")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/b/c") == ("static", {})


def test_deep_fallback_chain_param():
    router = RadixRouter()
    router.add("/a/b/c", "static")
    router.add("/a/:x/c", "param")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/x/c") == ("param", {"x": "x"})


def test_deep_fallback_chain_wild():
    router = RadixRouter()
    router.add("/a/b/c", "static")
    router.add("/a/:x/c", "param")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/x/y") == ("wild", {"rest": "x/y"})


def test_param_inside_wildcard_never_matches():
    router = RadixRouter()
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/:id/x") == ("wild", {"rest": ":id/x"})


# ---------


def test_complex_branching_root_level():
    router = RadixRouter()
    router.add("/a/:id/x", "a_param_x")
    router.add("/a/:id/*rest", "a_param_wild")
    router.add("/a/b/c", "a_static_bc")
    router.add("/a/*rest", "a_wild")
    assert router.lookup("/a/b/c") == ("a_static_bc", {})
    assert router.lookup("/a/1/x") == ("a_param_x", {"id": "1"})
    assert router.lookup("/a/1/y/z") == ("a_param_wild", {"id": "1", "rest": "y/z"})
    assert router.lookup("/a/q") == ("a_param_wild", {"id": "q", "rest": ""})


def test_diamond_branching():
    router = RadixRouter()
    router.add("/x/static/end", "static")
    router.add("/x/:id/end", "param")
    router.add("/x/*rest", "wild")
    assert router.lookup("/x/static/end") == ("static", {})
    assert router.lookup("/x/123/end") == ("param", {"id": "123"})
    assert router.lookup("/x/123/other") == ("wild", {"rest": "123/other"})


def test_param_branches_reconverge_to_wildcard_different_name():
    router = RadixRouter()
    router.add("/a/:x/b", "xb")
    with pytest.raises(ValueError):
        router.add("/a/:y/c", "yc")


def test_param_branches_reconverge_to_wildcard_lb():
    router = RadixRouter()
    router.add("/a/:x/b", "xb")
    router.add("/a/:x/c", "yc")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/1/b") == ("xb", {"x": "1"})


def test_param_branches_reconverge_to_wildcard_rb():
    router = RadixRouter()
    router.add("/a/:x/b", "xb")
    router.add("/a/:x/c", "yc")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/2/c") == ("yc", {"x": "2"})


def test_param_branches_reconverge_to_wildcard_wild():
    router = RadixRouter()
    router.add("/a/:x/b", "xb")
    router.add("/a/:x/c", "yc")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/3/d") == ("wild", {"rest": "3/d"})


def test_nested_wildcard_forks():
    router = RadixRouter()
    router.add("/a/b/*rest", "b_wild")
    router.add("/a/:id/c/*rest", "id_c_wild")
    router.add("/a/:id/*rest", "id_wild")
    assert router.lookup("/a/b/x/y") == ("b_wild", {"rest": "x/y"})
    assert router.lookup("/a/1/c/d/e") == ("id_c_wild", {"id": "1", "rest": "d/e"})
    assert router.lookup("/a/1/x/y") == ("id_wild", {"id": "1", "rest": "x/y"})


def test_static_branch_blocks_param_and_wildcard():
    router = RadixRouter()
    router.add("/a/fixed/x", "static")
    router.add("/a/:id/x", "param")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/fixed/x") == ("static", {})
    assert router.lookup("/a/123/x") == ("param", {"id": "123"})
    assert router.lookup("/a/fixed/y") == ("wild", {"rest": "fixed/y"})


def test_param_branch_with_inner_static_and_outer_wildcard():
    router = RadixRouter()
    router.add("/a/:id/static", "param_static")
    router.add("/a/:id/*rest", "param_wild")
    router.add("/a/*rest", "wild")
    assert router.lookup("/a/1/static") == ("param_static", {"id": "1"})
    assert router.lookup("/a/1/x/y") == ("param_wild", {"id": "1", "rest": "x/y"})
    assert router.lookup("/a/x") == ("param_wild", {"id": "x", "rest": ""})


def test_multiple_param_siblings_with_wildcard_fallback():
    router = RadixRouter()
    router.add("/a/:x/b", "xb")
    router.add("/a/:x/c", "xc")
    router.add("/a/:x/*rest", "xwild")
    assert router.lookup("/a/1/b") == ("xb", {"x": "1"})
    assert router.lookup("/a/1/c") == ("xc", {"x": "1"})
    assert router.lookup("/a/1/d") == ("xwild", {"x": "1", "rest": "d"})


def test_competing_wildcards_deep_tree():
    router = RadixRouter()
    router.add("/a/*rest", "root_wild")
    router.add("/a/b/*rest", "b_wild")
    router.add("/a/b/c/*rest", "c_wild")
    assert router.lookup("/a/b/c/d") == ("c_wild", {"rest": "d"})
    assert router.lookup("/a/b/x/y") == ("b_wild", {"rest": "x/y"})
    assert router.lookup("/a/x/y/z") == ("root_wild", {"rest": "x/y/z"})


def test_param_and_wildcard_shadowing_across_branches():
    router = RadixRouter()
    router.add("/a/:id/b", "param_b")
    router.add("/a/:id/*rest", "param_wild")
    router.add("/a/b/c", "static")
    assert router.lookup("/a/b/c") == ("static", {})
    assert router.lookup("/a/1/b") == ("param_b", {"id": "1"})
    assert router.lookup("/a/1/x/y") == ("param_wild", {"id": "1", "rest": "x/y"})


def test_param_partial_match_then_wildcard_fallback():
    router = RadixRouter()
    router.add("/a/:id/x/y", "deep_param")
    router.add("/a/:id/*rest", "param_wild")
    assert router.lookup("/a/1/x/y") == ("deep_param", {"id": "1"})
    assert router.lookup("/a/1/x/z") == ("param_wild", {"id": "1", "rest": "x/z"})
