"""
main.py
The full Artisan Digital Business Assistant API — Phases 1 to 8 in one app.

Pipeline this API supports:
    Product photo -> name & category -> description + tags ->
    multi-language catalog -> suggested price -> suitable market/buyer

Run it:
    pip install -r requirements.txt
    uvicorn main:app --reload
Then open http://127.0.0.1:8000/docs
"""

import os
import shutil
import uuid
from typing import List

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import models
import schemas
import crud
import ai_services
from database import engine, get_db
from auth import (
    verify_password,
    create_access_token,
    get_current_user,
)

# ---- Phase 2: create tables if they don't exist ----
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Artisan Digital Business Assistant API")

# ---- Phase 9 prep: allow the mobile/frontend app to call this API ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your app's real domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Phase 5: static folder to serve uploaded images ----
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Artisan Assistant API running"}


# =====================================================================
# PHASE 3 — Authentication
# =====================================================================

@app.post("/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user)


@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm sends "username" — we treat that field as email
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return schemas.Token(access_token=token)


@app.get("/auth/me", response_model=schemas.UserResponse)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# =====================================================================
# PHASE 4 — Product CRUD (protected: must be logged in)
# =====================================================================

@app.post("/products", response_model=schemas.ProductResponse)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_product(db, product, owner_id=current_user.id)


@app.get("/products", response_model=List[schemas.ProductResponse])
def list_products(skip: int = 0, limit: int = 50, mine_only: bool = False,
                   db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    owner_id = current_user.id if mine_only else None
    return crud.get_products(db, skip=skip, limit=limit, owner_id=owner_id)


@app.get("/products/{product_id}", response_model=schemas.ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@app.put("/products/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    updates: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    if db_product.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Not your product")
    return crud.update_product(db, product_id, updates)


@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    if db_product.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Not your product")
    crud.delete_product(db, product_id)
    return {"status": "deleted", "id": product_id}


# =====================================================================
# PHASE 5 — Image upload/store/retrieve
# =====================================================================

@app.post("/products/{product_id}/image", response_model=schemas.ProductResponse)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    if db_product.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Not your product")

    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_url = f"/uploads/{filename}"
    return crud.update_product(db, product_id, schemas.ProductUpdate(image_url=image_url))


@app.post("/products/{product_id}/image-base64", response_model=schemas.ProductResponse)
def upload_product_image_base64(
    product_id: int,
    payload: schemas.Base64ImageUpload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Matches the frontend camera/gallery flow: the browser captures a photo
    (camera snapshot or gallery file) as a base64 data URL — e.g.
    "data:image/png;base64,iVBORw0KG..." — and sends that string directly,
    instead of a multipart file. This decodes it and saves it the same way
    /products/{id}/image does for normal file uploads.
    """
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    if db_product.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Not your product")

    header, _, encoded = payload.image_data.partition(",")
    if not encoded:
        raise HTTPException(status_code=400, detail="Invalid image data — expected a base64 data URL")

    # header looks like "data:image/png;base64" -> pull out "png"
    ext = "png"
    if "/" in header and ";" in header:
        ext = header.split("/")[1].split(";")[0]

    import base64
    try:
        image_bytes = base64.b64decode(encoded)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode base64 image data")

    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    image_url = f"/uploads/{filename}"
    return crud.update_product(db, product_id, schemas.ProductUpdate(image_url=image_url))


# =====================================================================
# PHASE 6 — AI integration: image/voice -> structured product data, translation
# =====================================================================

@app.post("/ai/extract-product-info", response_model=schemas.AIExtractResponse)
async def extract_product_info(
    voice_text: str = Form(None),
    hint_category: str = Form(None),
    file: UploadFile = File(None),
    current_user: models.User = Depends(get_current_user),
):
    image_bytes = await file.read() if file else None
    result = ai_services.extract_product_info(
        image_bytes=image_bytes, voice_text=voice_text, hint_category=hint_category
    )
    return schemas.AIExtractResponse(**result)


@app.post("/ai/translate", response_model=schemas.TranslateResponse)
def translate(request: schemas.TranslateRequest, current_user: models.User = Depends(get_current_user)):
    translations = ai_services.translate_text(request.text, request.target_languages)
    return schemas.TranslateResponse(translations=translations)


@app.post("/products/{product_id}/translate", response_model=schemas.ProductResponse)
def translate_product(
    product_id: int,
    request: schemas.TranslateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    translations = ai_services.translate_text(db_product.description or db_product.name,
                                                request.target_languages)
    return crud.update_product(db, product_id, schemas.ProductUpdate(translations=translations))


# =====================================================================
# PHASE 7 — Pricing recommendation
# =====================================================================

@app.post("/ai/recommend-price", response_model=schemas.PriceResponse)
def recommend_price(request: schemas.PriceRequest, current_user: models.User = Depends(get_current_user)):
    result = ai_services.recommend_price(request.cost_price, request.category, request.material_quality)
    return schemas.PriceResponse(**result)


@app.post("/products/{product_id}/recommend-price", response_model=schemas.ProductResponse)
def recommend_price_for_product(
    product_id: int,
    material_quality: str = "standard",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not db_product.cost_price:
        raise HTTPException(status_code=400, detail="Set cost_price on the product first")

    result = ai_services.recommend_price(db_product.cost_price, db_product.category, material_quality)
    return crud.update_product(db, product_id, schemas.ProductUpdate(suggested_price=result["suggested_price"]))


# =====================================================================
# PHASE 8 — Market linkage
# =====================================================================

@app.get("/products/{product_id}/match-markets", response_model=schemas.MarketMatchResponse)
def match_markets(product_id: int, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    result = ai_services.match_markets(db_product.category, db_product.suggested_price)
    crud.update_product(db, product_id, schemas.ProductUpdate(suitable_markets=result["suitable_markets"]))

    return schemas.MarketMatchResponse(
        product_id=product_id,
        suitable_markets=result["suitable_markets"],
        reasoning=result["reasoning"],
    )


# =====================================================================
# PHASE 9 — Connect frontend
# CORS is already enabled above. The mobile app calls these same routes,
# e.g.: POST /auth/login -> store token -> attach "Authorization: Bearer <token>"
# to every subsequent request.
# =====================================================================