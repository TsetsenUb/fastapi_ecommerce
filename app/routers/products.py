from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.models.reviews import Review as ReviewModel
from app.schemas import Product as ProductSchema, ProductCreate, Review as ReviewSchema
from app.auth import get_current_seller
from app.db_depends import get_async_db


router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=list[ProductSchema], status_code=status.HTTP_200_OK)
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    result = await db.scalars(
        select(ProductModel)
        .where(ProductModel.is_active.is_(True))
    )

    return result.all()


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
    """
    category = await db.scalar(
        select(CategoryModel)
        .where(product.category_id == CategoryModel.id, CategoryModel.is_active.is_(True))
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Category not found'
        )

    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.get("/category/{category_id}", response_model=list[ProductSchema], status_code=status.HTTP_200_OK)
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    category = await db.scalar(
        select(CategoryModel)
        .where(category_id == CategoryModel.id, CategoryModel.is_active.is_(True))
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Category not found'
        )

    results = await db.scalars(
        select(ProductModel)
        .where(ProductModel.category_id == category_id, ProductModel.is_active.is_(True))
    )

    return results.all()


@router.get("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    product = await db.scalar(
        select(ProductModel)
        .where(ProductModel.id == product_id, ProductModel.is_active.is_(True))
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found'
        )

    return product


@router.put("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def update_product(
    product_id: int,
    product: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Обновляет товар, если он принадлежит текущему продавцу (только для 'seller').
    """
    db_product = await db.scalar(select(ProductModel).where(ProductModel.id == product_id))

    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found'
        )

    if db_product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own products"
        )

    db_category = await db.scalar(
        select(CategoryModel)
        .where(CategoryModel.id == product.category_id, CategoryModel.is_active.is_(True))
    )

    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Category not found'
        )

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product.model_dump())
    )
    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """
    product = await db.scalar(
        select(ProductModel)
        .where(ProductModel.id == product_id, ProductModel.is_active.is_(True))
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found'
        )

    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own products"
        )

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(is_active=False)
    )
    await db.commit()
    await db.refresh(product)
    return product


@router.get('/{product_id}/reviews', response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_product_reviews(product_id: int, db: AsyncSession = Depends(get_async_db)):
    product = await db.scalar(
        select(ProductModel)
        .where(ProductModel.id == product_id, ProductModel.is_active.is_(True))
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found'
        )

    reviews = await db.scalars(
        select(ReviewModel)
        .where(ReviewModel.product_id == product_id, ReviewModel.is_active.is_(True))
    )
    return reviews.all()
