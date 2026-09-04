from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "artisan"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Any
    created_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    cost_price: Optional[float] = Field(default=None, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    image_url: Optional[str] = None
    translations: Optional[Dict[str, str]] = None
    cost_price: Optional[float] = Field(default=None, ge=0)
    suggested_price: Optional[float] = Field(default=None, ge=0)
    suitable_markets: Optional[List[str]] = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    image_url: Optional[str] = None
    translations: Optional[Dict[str, str]] = None
    cost_price: Optional[float] = None
    suggested_price: Optional[float] = None
    suitable_markets: Optional[List[str]] = None
    owner_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Base64ImageUpload(BaseModel):
    image_data: str


class AIExtractResponse(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class TranslateRequest(BaseModel):
    text: str
    target_languages: List[str]


class TranslateResponse(BaseModel):
    translations: Dict[str, str]


class PriceRequest(BaseModel):
    cost_price: float = Field(ge=0)
    category: Optional[str] = None
    material_quality: str = "standard"


class PriceResponse(BaseModel):
    suggested_price: float
    reasoning: Optional[str] = None


class MarketMatchResponse(BaseModel):
    product_id: int
    suitable_markets: List[str]
    reasoning: Optional[str] = None
