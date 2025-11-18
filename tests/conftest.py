import pytest
pytest_plugins = ["pytest_asyncio"]

# This conftest.py enables pytest_asyncio for async test functions.
# pytest_asyncio.mode can be set here if needed, e.g.,
# @pytest.fixture(scope="session")
# def event_loop():
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()
