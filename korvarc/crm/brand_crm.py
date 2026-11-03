"""Brand CRM and explainable creator-brand sponsorship matching."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from korvarc.database.connection import get_db_session
from korvarc.database.schema import Brand, Influencer

VALID_BRAND_STATUSES = [
    "Researching",
    "Qualified",
    "Contacted",
    "Interested",
    "Negotiating",
    "Active Partner",
    "Closed",
    "Declined",
    "Do Not Contact",
]


class BrandCRM:
    """Manages brand relationship records and transparent creator matchmaking."""

    @classmethod
    def list_brands(
        cls,
        status: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Brand]:
        with get_db_session() as session:
            q = session.query(Brand)
            if status and status != "All":
                q = q.filter(Brand.pipeline_status == status)
            if search_query and search_query.strip():
                term = f"%{search_query.strip()}%"
                q = q.filter(
                    (Brand.company_name.ilike(term))
                    | (Brand.product_category.ilike(term))
                    | (Brand.contact_name.ilike(term))
                    | (Brand.contact_email.ilike(term))
                )
            return q.order_by(Brand.id.desc()).slice(offset, offset + limit).all()

    @classmethod
    def count_brands(cls, status: Optional[str] = None) -> int:
        with get_db_session() as session:
            q = session.query(Brand)
            if status and status != "All":
                q = q.filter(Brand.pipeline_status == status)
            return q.count()

    @classmethod
    def get_brand(cls, brand_id: int) -> Optional[Brand]:
        with get_db_session() as session:
            return session.query(Brand).filter_by(id=brand_id).first()

    @classmethod
    def create_brand(cls, **kwargs) -> Brand:
        status = kwargs.get("pipeline_status", "Researching")
        if status not in VALID_BRAND_STATUSES:
            status = "Researching"
        kwargs["pipeline_status"] = status

        with get_db_session() as session:
            brand = Brand(**kwargs)
            session.add(brand)
            session.flush()
            session.refresh(brand)
            return brand

    @classmethod
    def update_brand(cls, brand_id: int, **kwargs) -> Optional[Brand]:
        if "pipeline_status" in kwargs:
            if kwargs["pipeline_status"] not in VALID_BRAND_STATUSES:
                del kwargs["pipeline_status"]

        with get_db_session() as session:
            brand = session.query(Brand).filter_by(id=brand_id).first()
            if not brand:
                return None
            for k, v in kwargs.items():
                if hasattr(brand, k):
                    setattr(brand, k, v)
            brand.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(brand)
            return brand

    @classmethod
    def delete_brand(cls, brand_id: int) -> bool:
        with get_db_session() as session:
            brand = session.query(Brand).filter_by(id=brand_id).first()
            if brand:
                session.delete(brand)
                return True
        return False

    @classmethod
    def find_creator_matches(cls, brand_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Finds explainable creator matches based on niche, audience, and commercial fit.
        
        Avoids arbitrary numerical scores; provides explicit, explainable match rationale.
        """
        matches = []
        with get_db_session() as session:
            brand = session.query(Brand).filter_by(id=brand_id).first()
            if not brand:
                return []

            category = (brand.product_category or "").lower()
            target_aud = (brand.target_audience or "").lower()

            creators = session.query(Influencer).all()
            for creator in creators:
                creator_niche = (creator.niche or "").lower()
                creator_notes = (creator.general_notes or "").lower()

                match_reasons = []

                # Domain overlap
                if any(w in creator_niche for w in ["ai", "machine learning", "data science"]) and any(
                    w in category or w in target_aud for w in ["ai", "ml", "data", "python", "model"]
                ):
                    match_reasons.append("Shared technical domain: AI, Machine Learning & Data Science")

                if any(w in creator_niche for w in ["developer", "software", "programming"]) and any(
                    w in category or w in target_aud for w in ["developer", "code", "dev tools", "software", "api"]
                ):
                    match_reasons.append("Developer audience alignment: Engineers, DevOps, and Full-Stack builders")

                if any(w in creator_niche for w in ["cloud", "devops"]) and any(
                    w in category or w in target_aud for w in ["cloud", "infra", "kubernetes", "hosting"]
                ):
                    match_reasons.append("Infrastructure alignment: Cloud architecture & DevOps practitioners")

                # If no specific keyword match, check generic technical education match
                if not match_reasons and ("saas" in category or "tool" in category):
                    match_reasons.append("General SaaS / developer utility fit for technical software audience")

                if match_reasons:
                    matches.append({
                        "creator_id": creator.id,
                        "creator_name": creator.name,
                        "channel_name": creator.channel_name,
                        "niche": creator.niche,
                        "representation_status": creator.representation_status,
                        "rate_reference": creator.rate_reference,
                        "reasons": match_reasons,
                    })

        return matches[:limit]

