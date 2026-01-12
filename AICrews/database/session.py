from .db_manager import DBManager

def SessionLocal():
    """
    提供与 backend/app/main.py 兼容的 SessionLocal 获取方式
    """
    return DBManager().get_session()

def get_db():
    """
    FastAPI dependency for database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
