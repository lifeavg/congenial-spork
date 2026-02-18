from collections.abc import Callable, Iterable


def chain_decorators[T](decorators: Iterable[Callable[[T], T]]) -> Callable[[T], T]:

    def wrapper(func: T) -> T:
        for dec in decorators:
            func = dec(func)
        return func

    return wrapper
