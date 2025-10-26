class AsyncCursorMock:
    """Async-iterable mock for motor cursors, supports .sort() chaining."""

    def __init__(self, items: list) -> None:
        self._items = list(items)

    def sort(self, *args, **kwargs) -> "AsyncCursorMock":
        return self

    def __aiter__(self) -> "AsyncCursorMock":
        return self

    async def __anext__(self):
        if self._items:
            return self._items.pop(0)
        raise StopAsyncIteration
