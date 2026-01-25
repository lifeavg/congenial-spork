def handler_factory():
    async def empty_handler(request):
        return request

    return empty_handler


def middleware_factory(n):
    def middleware(handler):
        async def wrapper(request):
            return f"{n} {await handler(request)} {n}"

        return wrapper

    return middleware
