import logging


class Model:
    TABLE_NAME = None
    FIELDS = []

    def __init__(self, **kwargs):
        for field in self.FIELDS:
            setattr(self, field, kwargs.get(field, None))

    @classmethod
    def init_fields(cls, cursor):
        cursor.execute(f'''SELECT * FROM {cls.TABLE_NAME} LIMIT 0''')
        cls.FIELDS = [desc[0] for desc in cursor.description]

    def values(self):
        return tuple(getattr(self, field) for field in self.FIELDS)

    def _prepare_for_insert(self, cursor):
        pass

    def insert(self, cursor):
        self._prepare_for_insert(cursor)
        values = self.values()
        columns = ', '.join(field for field, value in zip(self.FIELDS, values) if value is not None)
        values_format = ', '.join('%s' for value in values if value is not None)
        q = f'''INSERT INTO {self.TABLE_NAME} ({columns}) VALUES ({values_format})'''
        logging.debug(q)
        cursor.execute(q, [value for value in values if value is not None])
        if 'id' in self.FIELDS and self.id is None:
            q = '''SELECT currval(pg_get_serial_sequence(%s, 'id'))'''
            cursor.execute(q, (self.TABLE_NAME, ))
            self.id, = cursor.fetchone()

    @classmethod
    def select(cls, cursor, filters={}, limit=None):
        q = f'SELECT * FROM {cls.TABLE_NAME}'
        if filters:
            q_filter = ' AND '.join(f'{field} = {repr(value)}' for field, value in filters.items())
            q += f' WHERE {q_filter}'
        if limit is not None:
            q += f' LIMIT {limit}'
        logging.debug(q)
        cursor.execute(q)
        return (cls(**dict(zip(cls.FIELDS, t))) for t in cursor.fetchall())

    @classmethod
    def clear(cls, cursor):
        cursor.execute(f'''DELETE FROM {cls.TABLE_NAME}''')
        return cursor.rowcount

    def __repr__(self):
        content = ', '.join(f'{field}={repr(value)}' for field, value in zip(self.FIELDS, self.values()) if value is not None)
        return f'{type(self).__name__}({content})'
