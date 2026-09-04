"""
models.py
All database tables live here: User (Phase 3) and Product (Phase 4).
"""

from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class UserRole(str, enum.Enum):
    artisan = "artisan"
    buyer = "buyer"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.artisan, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="owner")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    # Core info — filled manually OR by AI (Phase 6)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True, index=True)
    description = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # comma-separated

    # Phase 5 — image
    image_url = Column(String, nullable=True)

    # Phase 6 — multi-language catalog, e.g. {"hi": "...", "ta": "..."}
    translations = Column(JSON, nullable=True)

    # Phase 7 — pricing
    cost_price = Column(Float, nullable=True)
    suggested_price = Column(Float, nullable=True)

    # Phase 8 — market linkage, e.g. ["local_market", "export", "online_craft_store"]
    suitable_markets = Column(JSON, nullable=True)

    # Phase 3 — ownership
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    owner = relationship("User", back_populates="products")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())