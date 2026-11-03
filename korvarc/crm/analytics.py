"""Analytics engine computing agency performance strictly from stored database records."""

from __future__ import annotations

import json
from typing import Any, Dict
from sqlalchemy import func
from sqlalchemy.orm import Session

from korvarc.database.connection import get_db_session
from korvarc.database.schema import Brand, Campaign, EmailDraft, Influencer


class AgencyAnalytics:
    """Provides factual, uninflated metrics directly from stored records."""

    @classmethod
    def get_summary_metrics(cls) -> Dict[str, Any]:
        with get_db_session() as session:
            # CRM Counts
            total_influencers = session.query(Influencer).count()
            onboarded_influencers = session.query(Influencer).filter_by(representation_status="Onboarded Non-exclusive").count()
            prospect_influencers = session.query(Influencer).filter_by(representation_status="Prospect").count()

            total_brands = session.query(Brand).count()
            active_brand_partners = session.query(Brand).filter_by(pipeline_status="Active Partner").count()

            # Email Drafts
            total_drafts = session.query(EmailDraft).count()
            approved_drafts = session.query(EmailDraft).filter_by(approval_status="approved").count()
            rejected_drafts = session.query(EmailDraft).filter_by(approval_status="rejected").count()
            pending_drafts = session.query(EmailDraft).filter_by(approval_status="draft").count()

            # Average Word Count
            avg_wc_result = session.query(func.avg(EmailDraft.word_count)).filter(EmailDraft.word_count > 0).scalar()
            avg_word_count = round(float(avg_wc_result), 1) if avg_wc_result else 0.0

            # Average Rating
            avg_rating_res = session.query(func.avg(EmailDraft.user_rating)).filter(EmailDraft.user_rating != None).scalar()
            avg_rating = round(float(avg_rating_res), 2) if avg_rating_res else 0.0

            # Campaigns & Revenue
            active_campaigns = session.query(Campaign).filter(Campaign.status.in_(["Negotiating", "Contracted", "In Production", "Live"])).count()
            confirmed_deals = session.query(Campaign).filter(Campaign.status.in_(["Contracted", "In Production", "Live", "Completed"])).all()

            revenue_cad = sum(c.commission_amount or 0.0 for c in confirmed_deals if (c.currency or "CAD").upper() == "CAD")
            revenue_usd = sum(c.commission_amount or 0.0 for c in confirmed_deals if (c.currency or "").upper() == "USD")

            # Providers Breakdown
            openai_count = session.query(EmailDraft).filter_by(ai_provider="openai").count()
            claude_count = session.query(EmailDraft).filter_by(ai_provider="claude").count()
            manual_count = session.query(EmailDraft).filter_by(ai_provider="manual").count()

            # Feedback reasons breakdown
            all_drafts = session.query(EmailDraft.feedback_reasons).all()
            reasons_counter: Dict[str, int] = {}
            for row in all_drafts:
                if row[0]:
                    try:
                        reasons = json.loads(row[0])
                        for r in reasons:
                            reasons_counter[r] = reasons_counter.get(r, 0) + 1
                    except Exception:
                        pass

            return {
                "total_influencers": total_influencers,
                "onboarded_influencers": onboarded_influencers,
                "prospect_influencers": prospect_influencers,
                "total_brands": total_brands,
                "active_brand_partners": active_brand_partners,
                "total_drafts": total_drafts,
                "approved_drafts": approved_drafts,
                "rejected_drafts": rejected_drafts,
                "pending_drafts": pending_drafts,
                "avg_word_count": avg_word_count,
                "avg_rating": avg_rating,
                "active_campaigns": active_campaigns,
                "confirmed_revenue_cad": round(revenue_cad, 2),
                "confirmed_revenue_usd": round(revenue_usd, 2),
                "providers_distribution": {
                    "OpenAI": openai_count,
                    "Claude": claude_count,
                    "Manual": manual_count,
                },
                "feedback_reasons_distribution": reasons_counter,
            }

