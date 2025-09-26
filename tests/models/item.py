from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from src.crudle import CRUDMixin
from tests.conftest import Base


# Define the models
class Item(Base, CRUDMixin):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    color = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
