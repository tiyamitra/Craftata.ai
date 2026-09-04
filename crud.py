from sqlalchemy.orm import Session

import models
import schemas
from auth import get_password_hash


# -----------------------------
# User CRUD
# -----------------------------
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# -----------------------------
# Product CRUD
# -----------------------------
def create_product(db: Session, product: schemas.ProductCreate, owner_id: int):
    db_product = models.Product(
        **product.model_dump(exclude_unset=True),
        owner_id=owner_id,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    owner_id: int | None = None,
):
    query = db.query(models.Product)

    if owner_id is not None:
        query = query.filter(models.Product.owner_id == owner_id)

    return (
        query
        .order_by(models.Product.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_product(
    db: Session,
    product_id: int,
    updates: schemas.ProductUpdate,
):
    db_product = get_product(db, product_id)

    if not db_product:
        return None

    update_data = updates.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_product, field, value)

    db.commit()
    db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int):
    db_product = get_product(db, product_id)

    if not db_product:
        return False

    db.delete(db_product)
    db.commit()
    return True
