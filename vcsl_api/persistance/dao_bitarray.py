from kink import inject
from persistance.datastore_postgres import PostgresDataStore
from models.bitarray import BitArray


@inject
class BitArrayDAO:
    def __init__(self, psqlDataStore: PostgresDataStore):
        self.psql = psqlDataStore
        self.create_bitarray_table()
        self.create_mask_table()

    def create_bitarray_table(self) -> bool:
        conn = self.psql.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('CREATE TABLE IF NOT EXISTS bitarray (id VARCHAR PRIMARY KEY, bitarray BYTEA);')
                conn.commit()
        finally:
            self.psql.put_connection(conn)
        return True

    def create_mask_table(self) -> bool:
        conn = self.psql.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('CREATE TABLE IF NOT EXISTS mask (id VARCHAR PRIMARY KEY, mask BYTEA, FOREIGN KEY (id) REFERENCES bitarray(id))')
                conn.commit()
        finally:
            self.psql.put_connection(conn)
        return True

    def get_bitarray(self, bitarray_id: str) -> BitArray:
        conn = self.psql.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM bitarray WHERE id = %s', (bitarray_id,))
                row = cur.fetchone()
            if row is None:
                return None
            return BitArray.decompress(row[1], id=row[0])
        finally:
            self.psql.put_connection(conn)

    def get_mask(self, mask_id: str) -> BitArray:
        conn = self.psql.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM mask WHERE id = %s', (mask_id,))
                row = cur.fetchone()
            if row is None:
                return None
            return BitArray.decompress(row[1], id=row[0])
        finally:
            self.psql.put_connection(conn)

    def set_bitarray(self, bitarray: BitArray) -> None:
        conn = self.psql.get_connection()
        try:
            with conn.cursor() as cur:
                compressed = bitarray.compress()
                cur.execute('INSERT INTO bitarray VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET bitarray = %s', (bitarray.id, compressed, compressed))
                conn.commit()
        finally:
            self.psql.put_connection(conn)

    def get_all_bitarrays(self) -> [BitArray]:
        conn = self.psql.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM bitarray')
                rows = cur.fetchall()
            return [BitArray.decompress(row[1], id=row[0]) for row in rows]
        finally:
            self.psql.put_connection(conn)

    def set_mask(self, mask: BitArray) -> None:
        conn = self.psql.get_connection()
        try:
            with conn.cursor() as cur:
                compressed = mask.compress()
                cur.execute('INSERT INTO mask VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET mask = %s', (mask.id, compressed, compressed))
                conn.commit()
        finally:
            self.psql.put_connection(conn)

