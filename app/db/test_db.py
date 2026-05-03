from app.db.session import engine

def test_db():
    try:
        with engine.connect() as conn:
            print("Database connected successfully")
    except Exception as e:
        print("Database connection failed")
        print(e)

if __name__ == "__main__":
    test_db()