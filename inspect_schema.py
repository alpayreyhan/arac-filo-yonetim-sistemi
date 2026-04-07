from sqlalchemy import create_engine, inspect
import pymysql
import sys

# Connection string
# Make sure this matches app.py
DATABASE_URI = 'mysql+pymysql://root:@localhost/fleet_pro'

def inspect_db():
    try:
        engine = create_engine(DATABASE_URI)
        inspector = inspect(engine)
        
        with open('schema_result.txt', 'w', encoding='utf-8') as f:
            f.write("Connected to database.\n")
            
            tables = inspector.get_table_names()
            f.write(f"Existing tables: {tables}\n")
            
            check_tables = ['vehicles', 'customers', 'rentals', 'expenses']
            
            for table_name in check_tables:
                if table_name in tables:
                    f.write(f"\n--- '{table_name}' Table Columns ---\n")
                    columns = inspector.get_columns(table_name)
                    for col in columns:
                        # Type might show as INTEGER(11) or INTEGER unsigned
                        f.write(f"Column: {col['name']} - Type: {col['type']}\n")
                else:
                    f.write(f"\nTable '{table_name}' does not exist.\n")

    except Exception as e:
        with open('schema_result.txt', 'w', encoding='utf-8') as f:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    inspect_db()
