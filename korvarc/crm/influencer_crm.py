"""Influencer CRM with duplicate detection, CSV/XLSX import wizard, and status management."""

from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from korvarc.database.connection import get_db_session
from korvarc.database.schema import Influencer

VALID_STATUSES = [
    "Prospect",
    "Contacted",
    "Interested",
    "Negotiating",
    "Onboarded Non-exclusive",
    "Inactive",
    "Declined",
    "Do Not Contact",
]


def normalize_email(email: Optional[str]) -> Optional[str]:
    if not email or not isinstance(email, str):
        return None
    cleaned = email.strip().lower()
    if "@" in cleaned and "." in cleaned:
        return cleaned
    return None


def normalize_url(url: Optional[str]) -> Optional[str]:
    if not url or not isinstance(url, str):
        return None
    cleaned = url.strip()
    # Strip trailing slashes and common tracking parameters
    cleaned = re.sub(r"/+$", "", cleaned)
    cleaned = re.sub(r"\?.*$", "", cleaned)
    return cleaned.lower()


class InfluencerCRM:
    """Manages technical creator CRM records and batch import workflows."""

    @classmethod
    def list_influencers(
        cls,
        status: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Influencer]:
        with get_db_session() as session:
            q = session.query(Influencer)
            if status and status != "All":
                q = q.filter(Influencer.representation_status == status)
            if search_query and search_query.strip():
                term = f"%{search_query.strip()}%"
                q = q.filter(
                    (Influencer.name.ilike(term))
                    | (Influencer.channel_name.ilike(term))
                    | (Influencer.business_email.ilike(term))
                    | (Influencer.niche.ilike(term))
                )
            return q.order_by(Influencer.id.desc()).slice(offset, offset + limit).all()

    @classmethod
    def count_influencers(cls, status: Optional[str] = None) -> int:
        with get_db_session() as session:
            q = session.query(Influencer)
            if status and status != "All":
                q = q.filter(Influencer.representation_status == status)
            return q.count()

    @classmethod
    def get_influencer(cls, influencer_id: int) -> Optional[Influencer]:
        with get_db_session() as session:
            return session.query(Influencer).filter_by(id=influencer_id).first()

    @classmethod
    def create_influencer(cls, **kwargs) -> Influencer:
        status = kwargs.get("representation_status", "Prospect")
        if status not in VALID_STATUSES:
            status = "Prospect"
        kwargs["representation_status"] = status

        if "business_email" in kwargs:
            kwargs["business_email"] = normalize_email(kwargs["business_email"])
        if "profile_url" in kwargs:
            kwargs["profile_url"] = normalize_url(kwargs["profile_url"])

        with get_db_session() as session:
            influencer = Influencer(**kwargs)
            session.add(influencer)
            session.flush()
            session.refresh(influencer)
            return influencer

    @classmethod
    def update_influencer(cls, influencer_id: int, **kwargs) -> Optional[Influencer]:
        if "representation_status" in kwargs:
            if kwargs["representation_status"] not in VALID_STATUSES:
                del kwargs["representation_status"]

        if "business_email" in kwargs:
            kwargs["business_email"] = normalize_email(kwargs["business_email"])
        if "profile_url" in kwargs:
            kwargs["profile_url"] = normalize_url(kwargs["profile_url"])

        with get_db_session() as session:
            inf = session.query(Influencer).filter_by(id=influencer_id).first()
            if not inf:
                return None
            for k, v in kwargs.items():
                if hasattr(inf, k):
                    setattr(inf, k, v)
            inf.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(inf)
            return inf

    @classmethod
    def delete_influencer(cls, influencer_id: int) -> bool:
        with get_db_session() as session:
            inf = session.query(Influencer).filter_by(id=influencer_id).first()
            if inf:
                session.delete(inf)
                return True
        return False

    @classmethod
    def parse_import_file(cls, file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Parses CSV or Excel bytes into a standardized pandas DataFrame."""
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            raise ValueError("Unsupported file format. Please upload a CSV or XLSX file.")
        return df

    @classmethod
    def preview_import(
        cls, df: pd.DataFrame, column_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Analyzes the DataFrame against existing database records for duplicate detection and validation."""
        total_rows = len(df)
        existing_emails = set()
        existing_urls = set()

        with get_db_session() as session:
            for inf in session.query(Influencer).all():
                if inf.business_email:
                    existing_emails.add(normalize_email(inf.business_email))
                if inf.profile_url:
                    existing_urls.add(normalize_url(inf.profile_url))

        potential_duplicates = 0
        valid_rows = 0
        preview_records = []

        name_col = column_mapping.get("name")
        email_col = column_mapping.get("business_email")
        url_col = column_mapping.get("profile_url")

        for idx, row in df.head(10).iterrows():
            rec_name = str(row.get(name_col, "")).strip() if name_col else ""
            rec_email = normalize_email(str(row.get(email_col, ""))) if email_col else None
            rec_url = normalize_url(str(row.get(url_col, ""))) if url_col else None

            is_dup = (rec_email and rec_email in existing_emails) or (rec_url and rec_url in existing_urls)
            preview_records.append({
                "Row": idx + 1,
                "Name": rec_name,
                "Email": rec_email or "None",
                "URL": rec_url or "None",
                "Status": "Duplicate detected" if is_dup else "Ready to import",
            })

        for _, row in df.iterrows():
            rec_email = normalize_email(str(row.get(email_col, ""))) if email_col else None
            rec_url = normalize_url(str(row.get(url_col, ""))) if url_col else None
            if (rec_email and rec_email in existing_emails) or (rec_url and rec_url in existing_urls):
                potential_duplicates += 1
            else:
                valid_rows += 1

        return {
            "total_rows": total_rows,
            "valid_rows": valid_rows,
            "duplicate_rows": potential_duplicates,
            "preview_sample": preview_records,
        }

    @classmethod
    def execute_import(
        cls,
        df: pd.DataFrame,
        column_mapping: Dict[str, str],
        duplicate_strategy: str = "skip",  # "skip" | "update" | "keep_both"
    ) -> Dict[str, int]:
        """Executes the import with deduplication and compliance checks."""
        imported_count = 0
        updated_count = 0
        skipped_count = 0

        name_col = column_mapping.get("name")
        channel_col = column_mapping.get("channel_name")
        email_col = column_mapping.get("business_email")
        url_col = column_mapping.get("profile_url")
        niche_col = column_mapping.get("niche")
        country_col = column_mapping.get("country")
        rate_col = column_mapping.get("rate_reference")
        status_col = column_mapping.get("representation_status")

        with get_db_session() as session:
            for _, row in df.iterrows():
                name_val = str(row.get(name_col, "")).strip() if name_col and pd.notna(row.get(name_col)) else ""
                if not name_val or name_val.lower() == "nan":
                    skipped_count += 1
                    continue

                email_val = normalize_email(str(row.get(email_col, ""))) if email_col and pd.notna(row.get(email_col)) else None
                url_val = normalize_url(str(row.get(url_col, ""))) if url_col and pd.notna(row.get(url_col)) else None
                channel_val = str(row.get(channel_col, "")).strip() if channel_col and pd.notna(row.get(channel_col)) else None
                niche_val = str(row.get(niche_col, "AI & Software Engineering")).strip() if niche_col and pd.notna(row.get(niche_col)) else "AI & Software Engineering"
                country_val = str(row.get(country_col, "")).strip() if country_col and pd.notna(row.get(country_col)) else None

                rate_val = None
                if rate_col and pd.notna(row.get(rate_col)):
                    try:
                        clean_num = re.sub(r"[^\d.]", "", str(row.get(rate_col)))
                        if clean_num:
                            rate_val = float(clean_num)
                    except ValueError:
                        pass

                status_val = "Prospect"
                if status_col and pd.notna(row.get(status_col)):
                    raw_s = str(row.get(status_col)).strip()
                    if raw_s in VALID_STATUSES:
                        status_val = raw_s

                # Check duplicate
                existing = None
                if email_val:
                    existing = session.query(Influencer).filter_by(business_email=email_val).first()
                if not existing and url_val:
                    existing = session.query(Influencer).filter_by(profile_url=url_val).first()

                if existing:
                    if duplicate_strategy == "skip":
                        skipped_count += 1
                        continue
                    elif duplicate_strategy == "update":
                        if channel_val:
                            existing.channel_name = channel_val
                        if niche_val:
                            existing.niche = niche_val
                        if country_val:
                            existing.country = country_val
                        if rate_val is not None:
                            existing.rate_reference = rate_val
                        updated_count += 1
                        continue

                # Add new record
                new_inf = Influencer(
                    name=name_val,
                    channel_name=channel_val or name_val,
                    platform="YouTube",
                    profile_url=url_val,
                    business_email=email_val,
                    niche=niche_val,
                    country=country_val,
                    rate_reference=rate_val,
                    representation_status=status_val,
                    general_notes="Imported via Korvarc CRM CSV Wizard",
                )
                session.add(new_inf)
                session.flush()
                imported_count += 1

        return {
            "imported": imported_count,
            "updated": updated_count,
            "skipped": skipped_count,
        }
