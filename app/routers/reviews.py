from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import Review as ReviewSchema, ReviewCreate
from app.models.reviews import Review as ReviewModel
from app.models.users import User as UserModel
from app.models.products import Product as ProductModel
from app.auth import get_current_buyer, get_current_admin
from app.db_depends import get_async_db


router = APIRouter(prefix='/reviews', tags=['reviews'])


@router.get('/', response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    reviews = await db.scalars(select(ReviewModel).where(ReviewModel.is_active.is_(True)))
    return reviews.all()


async def update_product_rating(db: AsyncSession, product_id: int):
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active.is_(True)
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    product.rating = avg_rating
    await db.commit()


@router.post('/', response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_buyer)
):
    db_product = await db.scalar(
        select(ProductModel)
        .where(ProductModel.id == review.product_id, ProductModel.is_active.is_(True))
    )
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found'
        )
    if review.grade < 1 or review.grade > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='The grade should be in the range from 1 to 5'
        )

    review_dct = review.model_dump()
    review_dct['user_id'] = current_user.id
    new_review = ReviewModel(**review_dct)

    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)

    await update_product_rating(db, db_product.id)

    return new_review


@router.delete('/{review_id}', status_code=status.HTTP_200_OK)
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_admin)
):
    review = await db.scalar(
        select(ReviewModel)
        .where(
            ReviewModel.id == review_id,
            ReviewModel.is_active.is_(True))
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Review not found'
        )

    await db.execute(
        update(ReviewModel)
        .where(ReviewModel.id == review_id)
        .values(is_active=False)
    )
    await db.commit()

    await update_product_rating(db, review.product_id)

    return {"message": "Review deleted"}
