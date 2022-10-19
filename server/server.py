"""
Configure the FastAPI server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from data.config import LIVE_YEAR

from server.routers import courses, programs, specialisations

app = FastAPI()

origins = "*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses.router)
app.include_router(programs.router)
app.include_router(specialisations.router)


@app.get("/")
async def index() -> str:
    """ sanity test that this file is loaded """
    return "At index inside server.py"

@app.get("/live_year")
def live_year() -> int:
    """ sanity check for the live year """
    return LIVE_YEAR
