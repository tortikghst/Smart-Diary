from scr.database import init_db
from scr.api.auth import auth
from scr.api.users import users_router
from scr.api.teacher import teacher_router
from scr.api.journal import journal_router
from scr.api.student import student_router
from scr.api.tests import tests_router
from scr.api.seating import seating_router
from scr.api.bot import bot_router

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

# A2: экстра-сид (не путать с seed_student_demo из пакета student_panel)
try:
    from scr.seed_big_demo import seed_big_demo
except ImportError:
    from scr.database import seed_demo_extra_data  # если положил в database.py


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth)
api_router.include_router(users_router)
api_router.include_router(teacher_router)
api_router.include_router(journal_router)
api_router.include_router(student_router)
api_router.include_router(tests_router)
api_router.include_router(seating_router)
#api_router.include_router(bot_router) 

async def lifespan(app: FastAPI):
    await init_db()
    await seed_big_demo()
    yield


app = FastAPI(title="Smart Diary API", lifespan=lifespan)

# A1: CORS — иначе браузер блокирует запросы фронта с другим origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Vite dev
        "http://localhost:3000",      # если фронт на CRA
        "https://sovolud.ru",
        "https://www.sovolud.ru",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(bot_router)
