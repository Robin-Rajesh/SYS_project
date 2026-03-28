import sys
sys.path.insert(0, r'c:\SEM5\SYS_project')
import config
from sqlalchemy import create_engine, inspect

engine = create_engine(config.DB_URI)
insp = inspect(engine)
tables = insp.get_table_names()
print('ALL TABLES:', tables)
print()
for t in tables:
    cols = insp.get_columns(t)
    fks = insp.get_foreign_keys(t)
    print(f'--- {t} ---')
    for c in cols:
        pk = ' [PK]' if c.get('primary_key') else ''
        print(f'  {c["name"]}  {c["type"]}{pk}')
    if fks:
        for fk in fks:
            print(f'  FK: {fk["constrained_columns"]} -> {fk["referred_table"]}.{fk["referred_columns"]}')
    print()
