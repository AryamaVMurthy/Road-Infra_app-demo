import sys
from pathlib import Path

import pytest
import redis


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def redis_url():
    return "redis://localhost:6379/15"


@pytest.fixture(autouse=True)
def clear_gateway_redis(redis_url):
    client = redis.from_url(redis_url, decode_responses=True)
    client.flushdb()
    yield
    client.flushdb()
