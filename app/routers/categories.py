from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categories import Category as CategoryModel
from app.schemas import Category as CategorySchema, CategoryCreate
from app.db_depends import get_async_db


router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


@router.get("/", response_model=list[CategorySchema])
async def get_all_categories(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех активных категорий.
    """
    result = await db.scalars(
        select(CategoryModel).
        where(CategoryModel.is_active.is_(True))
    )
    return result.all()


@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Создаёт новую категорию.
    """
    # Проверка существования parent_id, если указан
    if category.parent_id is not None:
        stmt = select(CategoryModel).where(
            CategoryModel.id == category.parent_id,
            CategoryModel.is_active.is_(True)
        )
        parent = await db.scalar(stmt)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found"
            )

    # Создание новой категории
    db_category = CategoryModel(**category.model_dump())
    db.add(db_category)
    await db.commit()

    return db_category


@router.put("/{category_id}", response_model=CategorySchema)
async def update_category(category_id: int, category: CategoryCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Обновляет категорию по её ID.
    """
    # Проверка существования категории
    db_category = await db.scalar(
        select(CategoryModel)
        .where(
            CategoryModel.id == category_id,
            CategoryModel.is_active.is_(True)
        )
    )
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Проверка существования parent_id, если указан
    if category.parent_id is not None:
        parent = await db.scalar(
            select(CategoryModel)
            .where(
                CategoryModel.id == category.parent_id,
                CategoryModel.is_active.is_(True)
            )
        )
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found"
            )
        if parent.id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent"
            )

    # Обновление категории
    await db.execute(
        update(CategoryModel)
        .where(CategoryModel.id == category_id)
        .values(**category.model_dump(exclude_unset=True))
    )
    await db.commit()

    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Логически удаляет категорию по её ID, устанавливая is_active=False.
    """
    # Проверка существования активной категории
    db_category = await db.scalar(
        select(CategoryModel)
        .where(
            CategoryModel.id == category_id,
            CategoryModel.is_active.is_(True)
        )
    )
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Логическое удаление категории (установка is_active=False)
    await db.execute(
        update(CategoryModel)
        .where(CategoryModel.id == category_id)
        .values(is_active=False)
    )
    await db.commit()

    return db_category
