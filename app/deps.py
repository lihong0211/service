# app/deps.py
"""
FastAPI 依赖注入（与 service-home 一致）。
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

SessionDep = Annotated[Session, Depends(get_db)]
