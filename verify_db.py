from app import app, Vehicle
with app.app_context():
    try:
        v = Vehicle.query.first()
        print("VERIFICATION_SUCCESS")
    except Exception as e:
        print(f"VERIFICATION_ERROR: {e}")
