# Integration testing for the entire project
# Needs a Postgres database running on localhost:5432
# Needs a Redis server running on localhost:6379
import requests
import pytest


@pytest.mark.dependency()
def test_create_bit_array():
    path = '/bit-array'
    # Create a bit array
    response = requests.put(pytest.api_url + path)
    assert response.status_code == 200
    assert 'id' in response.json()
    pytest.created_bit_array_id = response.json()['id']


@pytest.mark.dependency(depends=['test_create_bit_array'])
def test_free_space():
    path = f'/bit-array/{pytest.created_bit_array_id}/free'
    response = requests.get(pytest.api_url + path)
    assert response.status_code == 200
    assert response.json()['free'] == 2**17


@pytest.mark.dependency(depends=['test_create_bit_array'])
def test_get_compressed():
    path = f'/bit-array/{pytest.created_bit_array_id}'
    response = requests.get(pytest.api_url + path)
    assert response.status_code == 200
    assert 'bit-array' in response.json()
    assert len(response.json()['bit-array']) == len('H4sIAGrhp2UC/+3BMQEAAADCoPVPbQwfoAAAAAAAAAAAAAAAAAAAAIC3AYbSVKsAQAAA')
