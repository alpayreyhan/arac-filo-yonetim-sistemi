from app import app, db, Vehicle
from sqlalchemy import text

with app.app_context():
    try:
        print("Testing Vehicle Query...")
        v = Vehicle.query.first()
        print(f"Vehicle: {v}")
        if v:
            print(f"Daily Rate: {v.daily_rate}")
        print("Query successful.")
    except Exception as e:
        print(f"Query Failed: {e}")
        # Try to fix
        try:
            print("Attempting to add column...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE vehicles ADD COLUMN daily_rate FLOAT DEFAULT 0.0"))
                conn.commit()
            print("Column added successfully.")
        except Exception as e2:
            print(f"Fix Failed: {e2}")
