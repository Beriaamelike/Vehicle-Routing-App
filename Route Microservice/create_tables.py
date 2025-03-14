from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "mysql+pymysql://fastapi:fastapi123@localhost/vrp_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # ✅ Hata buradan kaynaklanıyordu, artık düzeltildi!

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer = Column(Integer, index=True)
    xc = Column(Float)
    yc = Column(Float)

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    route_id = Column(Integer, nullable=False)
    customer = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    demand = Column(Integer, nullable=False)
    distance = Column(Float, nullable=False)

# ✅ Veritabanındaki tüm tabloları oluştur
Base.metadata.create_all(bind=engine)

print("✅ MySQL içindeki tablolar başarıyla oluşturuldu!")
