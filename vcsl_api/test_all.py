# Integration testing for the entire project
# Needs a Postgres database running on localhost:5432
# Needs a Redis server running on localhost:6379
import requests
import pytest


def test_create_bit_array():
    path = '/bit-array'
    # Create a bit array
    response = requests.put(pytest.api_url + path)
    assert response.status_code == 200
    assert 'id' in response.json()
    print(response.json())


def __test_flip_bit():
    pass
