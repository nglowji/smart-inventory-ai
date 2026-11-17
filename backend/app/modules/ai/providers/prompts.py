from datetime import datetime

from app.core.dates import LOCAL_ZONE
from app.modules.ai.routing import routing_context


def planner_instructions() -> str:
    return routing_context(datetime.now(LOCAL_ZONE))
