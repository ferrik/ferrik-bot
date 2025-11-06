web: gunicorn -w 4 -b 0.0.0.0:$PORT main:app
release: python -c "from app.models import Base; from sqlalchemy import create_engine; import os; engine = create_engine(os.getenv('DATABASE_URL')); Base.metadata.create_all(engine)"
