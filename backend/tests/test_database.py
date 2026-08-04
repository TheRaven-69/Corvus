import pytest
from app.db.session import async_engine
from sqlalchemy import text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection() -> None:
    try:
        async with async_engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))

            assert result.scalar_one() == 1
    finally:
        await async_engine.dispose()
