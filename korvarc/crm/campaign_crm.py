"""Campaign management and commercial partnership tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from korvarc.database.connection import get_db_session
from korvarc.database.schema import Brand, Campaign, Influencer

VALID_CAMPAIGN_STATUSES = [
    "Pitching",
    "Negotiating",
    "Contracted",
    "In Production",
    "Live",
    "Completed",
    "Cancelled",
]


class CampaignCRM:
    """Tracks commercial campaigns, agreed deliverables, rates, and agency commissions."""

    @classmethod
    def list_campaigns(cls, status: Optional[str] = None) -> List[Campaign]:
        with get_db_session() as session:
            q = session.query(Campaign)
            if status and status != "All":
                q = q.filter(Campaign.status == status)
            return q.order_by(Campaign.id.desc()).all()

    @classmethod
    def get_campaign(cls, campaign_id: int) -> Optional[Campaign]:
        with get_db_session() as session:
            return session.query(Campaign).filter_by(id=campaign_id).first()

    @classmethod
    def create_campaign(cls, **kwargs) -> Campaign:
        status = kwargs.get("status", "Pitching")
        if status not in VALID_CAMPAIGN_STATUSES:
            status = "Pitching"
        kwargs["status"] = status

        # Compute commission amount if agreed rate is set
        agreed = kwargs.get("agreed_rate")
        comm_rate = kwargs.get("commission_rate", 0.20)
        if agreed and comm_rate:
            kwargs["commission_amount"] = round(float(agreed) * float(comm_rate), 2)

        with get_db_session() as session:
            camp = Campaign(**kwargs)
            session.add(camp)
            session.flush()
            session.refresh(camp)
            return camp

    @classmethod
    def update_campaign(cls, campaign_id: int, **kwargs) -> Optional[Campaign]:
        if "status" in kwargs and kwargs["status"] not in VALID_CAMPAIGN_STATUSES:
            del kwargs["status"]

        with get_db_session() as session:
            camp = session.query(Campaign).filter_by(id=campaign_id).first()
            if not camp:
                return None
            for k, v in kwargs.items():
                if hasattr(camp, k):
                    setattr(camp, k, v)

            if camp.agreed_rate and camp.commission_rate:
                camp.commission_amount = round(float(camp.agreed_rate) * float(camp.commission_rate), 2)

            camp.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(camp)
            return camp

    @classmethod
    def get_confirmed_revenue(cls) -> Dict[str, float]:
        """Calculates confirmed agency commission revenue from actual contracted/completed campaigns."""
        totals = {"CAD": 0.0, "USD": 0.0}
        confirmed_statuses = ["Contracted", "In Production", "Live", "Completed"]
        with get_db_session() as session:
            campaigns = session.query(Campaign).filter(Campaign.status.in_(confirmed_statuses)).all()
            for c in campaigns:
                curr = (c.currency or "CAD").upper()
                amount = c.commission_amount or 0.0
                if curr in totals:
                    totals[curr] += amount
                else:
                    totals[curr] = amount
        return totals

