# Unit tests for index allocation and status changes. No Postgres/Redis/IPFS needed.
# Run from vcsl_api/:  python -m pytest test_unit
import asyncio
import sys
import types

import pytest

# serv_bitarray imports these at module level; stub them so web3/IPFS are not needed
for name, cls in [("services.serv_web3", "Web3Service"), ("services.serv_ipfs", "IPFSService")]:
    stub = types.ModuleType(name)
    setattr(stub, cls, type(cls, (), {}))
    sys.modules.setdefault(name, stub)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from models.bitarray import BitArray  # noqa: E402
from services.serv_bitarray import (  # noqa: E402
    BitArrayService,
    BitArrayFullError,
    BitArrayNotFoundError,
    IndexNotAssignedError,
)
from routers.rout_bitarray import BitArrayRouter  # noqa: E402

SIZE = 2**17


def clone(ba: BitArray) -> BitArray:
    c = BitArray(id=ba.id)
    c.array = bytearray(ba.array)
    c.free = ba.free
    return c


class FakeDAO:
    """In-memory DAO that returns copies, like reading from the database."""

    def __init__(self):
        self.bitarrays, self.masks = {}, {}

    def get_all_bitarrays(self):
        return [clone(b) for b in self.bitarrays.values()]

    def get_bitarray(self, id):
        return clone(self.bitarrays[id]) if id in self.bitarrays else None

    def get_mask(self, id):
        return clone(self.masks[id]) if id in self.masks else None

    def set_bitarray(self, ba):
        self.bitarrays[ba.id] = clone(ba)

    def set_mask(self, ba):
        self.masks[ba.id] = clone(ba)


class FakeLock:
    def __init__(self):
        self.held = set()

    async def acquire_lock(self, name, acquire_timeout=10, blocking=True):
        if name in self.held:
            return None
        self.held.add(name)
        return True

    async def release_lock(self, name):
        self.held.discard(name)


class FakeScheduler:
    def add_job(self, *args, **kwargs):
        pass


def make_service():
    dao, lock = FakeDAO(), FakeLock()
    svc = BitArrayService(cache_service=None, lock_service=lock, bitarray_dao=dao,
                          web3_service=None, ipfs_service=None, scheduler=FakeScheduler())
    return svc, dao, lock


def new_list(dao, list_id="L1", assigned=(), fill_all_but=None):
    ba, mask = BitArray(id=list_id), BitArray(id=list_id)
    if fill_all_but is not None:
        mask.array = bytearray(b"\xff" * (SIZE // 8))
        mask.free = 0
        mask[fill_all_but] = 0
    for i in assigned:
        mask[i] = 1
    dao.set_bitarray(ba)
    dao.set_mask(mask)
    return list_id


def run(coro):
    return asyncio.run(coro)


# --- allocation ---

def test_never_returns_assigned_index_when_only_one_is_free():
    # Regression for the original bug: bitarray all 0, mask all 1 except one index
    svc, dao, lock = make_service()
    new_list(dao, fill_all_but=12345)
    assert run(svc.acquire_bit_array_index("L1")) == 12345
    assert dao.masks["L1"][12345] == 1
    assert not lock.held


def test_full_mask_raises_even_if_bitarray_has_no_revocations():
    svc, dao, lock = make_service()
    new_list(dao, fill_all_but=0)
    run(svc.acquire_bit_array_index("L1"))
    with pytest.raises(BitArrayFullError):
        run(svc.acquire_bit_array_index("L1"))
    assert not lock.held


def test_many_acquisitions_are_unique():
    svc, dao, _ = make_service()
    new_list(dao)
    indexes = [run(svc.acquire_bit_array_index("L1")) for _ in range(3000)]
    assert len(set(indexes)) == len(indexes)


def test_unique_when_list_is_almost_full():
    # Exercises the linear-scan fallback
    svc, dao, _ = make_service()
    free = {7, 50000, SIZE - 1}
    lid = new_list(dao, fill_all_but=7)
    for i in free:
        dao.masks[lid][i] = 0
    dao.masks[lid].free = len(free)
    got = {run(svc.acquire_bit_array_index(lid)) for _ in range(len(free))}
    assert got == free


def test_unknown_list_raises_and_releases_lock():
    svc, _, lock = make_service()
    with pytest.raises(BitArrayNotFoundError):
        run(svc.acquire_bit_array_index("nope"))
    assert not lock.held


# --- status bit ---

def test_set_bit_is_idempotent():
    svc, dao, _ = make_service()
    new_list(dao, assigned=[10])
    assert run(svc.set_bit("L1", 10, 1)) == 1
    assert run(svc.set_bit("L1", 10, 1)) == 1
    assert dao.bitarrays["L1"][10] == 1
    assert run(svc.set_bit("L1", 10, 0)) == 0
    assert run(svc.set_bit("L1", 10, 0)) == 0


def test_set_bit_without_value_toggles():
    svc, dao, _ = make_service()
    new_list(dao, assigned=[10])
    assert run(svc.set_bit("L1", 10)) == 1
    assert run(svc.set_bit("L1", 10)) == 0


def test_set_bit_on_unassigned_index_raises_and_releases_lock():
    svc, dao, lock = make_service()
    new_list(dao)
    with pytest.raises(IndexNotAssignedError):
        run(svc.set_bit("L1", 10, 1))
    assert not lock.held


# --- HTTP ---

@pytest.fixture
def client():
    svc, dao, _ = make_service()
    new_list(dao, assigned=[10])
    app = FastAPI()
    app.include_router(BitArrayRouter(bit_array_service=svc).router)
    return TestClient(app), dao


def test_http_acquire_route_is_not_shadowed(client):
    c, dao = client
    r = c.put("/bit-array/L1/index")
    assert r.status_code == 200
    assert dao.masks["L1"][r.json()["index"]] == 1


def test_http_post_with_value_sets_instead_of_toggling(client):
    c, dao = client
    for _ in range(2):  # retried revocation must keep the credential revoked
        r = c.post("/bit-array/L1/10", json={"value": 1})
        assert r.status_code == 200 and r.json()["bit"] == 1
    assert dao.bitarrays["L1"][10] == 1


def test_http_post_without_body_still_toggles(client):
    c, _ = client
    assert c.post("/bit-array/L1/10").json()["bit"] == 1
    assert c.post("/bit-array/L1/10").json()["bit"] == 0


def test_http_put_sets_bit(client):
    c, _ = client
    assert c.put("/bit-array/L1/10", json={"bit": 1}).json() == {"bit": 1}
    assert c.put("/bit-array/L1/10", json={"bit": 1}).json() == {"bit": 1}
    assert c.get("/bit-array/L1/10").json() == {"bit": 1}


def test_http_put_requires_value(client):
    c, _ = client
    assert c.put("/bit-array/L1/10", json={}).status_code == 422
    assert c.put("/bit-array/L1/10", json={"bit": 2}).status_code == 422


def test_http_error_codes(client):
    c, _ = client
    assert c.post("/bit-array/L1/11", json={"bit": 1}).status_code == 400  # not assigned
    assert c.post("/bit-array/L1/999999", json={"bit": 1}).status_code == 400  # out of range
    assert c.put("/bit-array/missing/index").status_code == 404


def test_http_full_list_returns_409():
    svc, dao, _ = make_service()
    new_list(dao, fill_all_but=0)
    dao.masks["L1"][0] = 1
    dao.masks["L1"].free = 0
    app = FastAPI()
    app.include_router(BitArrayRouter(bit_array_service=svc).router)
    assert TestClient(app).put("/bit-array/L1/index").status_code == 409
