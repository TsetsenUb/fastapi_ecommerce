from uuid import uuid4
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from app.routers import categories, products, users, reviews


# Создаём приложение FastAPI
app = FastAPI(
    title="FastAPI Интернет-магазин",
    version="0.1.0",
)


logger.add(
    "info.log",
    format="Log: [{extra[log_id]}:{time} - {level} - {message}]",
    level="INFO",
    enqueue=True
)


# Подключаем маршруты категорий и товаров
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(reviews.router)


@app.middleware("http")
async def log_middleware(request: Request, call_next):
    log_id = str(uuid4())
    with logger.contextualize(log_id=log_id):
        try:
            response = await call_next(request)
            if response.status_code in [401, 402, 403, 404]:
                logger.warning(f"Request to {request.url.path} failed")
            else:
                logger.info('Successfully accessed ' + request.url.path)
        except Exception as ex:
            logger.error(f"Request to {request.url.path} failed: {ex}")
            response = JSONResponse(content={"success": False}, status_code=500)
        return response


# Корневой эндпоинт для проверки
@app.get("/")
async def root(background_tasks: BackgroundTasks):
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    return {"message": "Добро пожаловать в API интернет-магазина!"}
