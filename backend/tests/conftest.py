import asyncio
import sys
from collections.abc import Callable

import pytest


def pytest_asyncio_loop_factories(
    config: pytest.Config,
    item: pytest.Item,
) -> dict[str, Callable[[], asyncio.AbstractEventLoop]]:
    if sys.platform == "win32":
        return {"selector": asyncio.SelectorEventLoop}

    return {"default": asyncio.new_event_loop}
