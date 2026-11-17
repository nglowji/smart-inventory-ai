from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.dependencies import current_user
from app.modules.reporting.insights import get_insights
from app.modules.reporting.queries import get_flow, get_summary
from app.modules.reporting.schemas import DashboardFlow, DashboardInsights, DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(current_user)])


@router.get("/insights", response_model=DashboardInsights)
def insights(
    date_from: date | None = None,
    date_to: date | None = None,
    session: Session = Depends(get_session),
):
    return get_insights(session, date_from, date_to)


@router.get("/summary", response_model=DashboardSummary)
def summary(
    date_from: date | None = None,
    date_to: date | None = None,
    session: Session = Depends(get_session),
):
    return get_summary(session, date_from, date_to)


@router.get("/flow", response_model=DashboardFlow)
def flow(
    date_from: date | None = None,
    date_to: date | None = None,
    session: Session = Depends(get_session),
):
    return get_flow(session, date_from, date_to)
