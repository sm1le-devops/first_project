from sqlalchemy import Column, Integer, String, DateTime,Float
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False, default=0.0)  # сумма донатов
    last_donation_time = Column(DateTime, default=None)  # время последнего доната
    avatar = Column(String(255), nullable=True) #поле аватара
