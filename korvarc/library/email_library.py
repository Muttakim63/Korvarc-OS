"""Searchable email draft repository with revision tracking, version comparison, and exports."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from korvarc.database.connection import get_db_session
from korvarc.database.schema import EmailDraft


class EmailLibrary:
    """Manages generated email drafts, revision history, and structured exports."""

    @classmethod
    def list_drafts(
        cls,
        outreach_type: Optional[str] = None,
        approval_status: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EmailDraft]:
        with get_db_session() as session:
            q = session.query(EmailDraft)
            if outreach_type and outreach_type != "All":
                q = q.filter(EmailDraft.outreach_type == outreach_type.lower())
            if approval_status and approval_status != "All":
                q = q.filter(EmailDraft.approval_status == approval_status.lower())
            if search_query and search_query.strip():
                term = f"%{search_query.strip()}%"
                q = q.filter(
                    (EmailDraft.recipient_entity.ilike(term))
                    | (EmailDraft.recipient_name.ilike(term))
                    | (EmailDraft.selected_subject.ilike(term))
                    | (EmailDraft.email_body.ilike(term))
                )
            return q.order_by(EmailDraft.updated_at.desc()).slice(offset, offset + limit).all()

    @classmethod
    def get_draft(cls, draft_id: int) -> Optional[EmailDraft]:
        with get_db_session() as session:
            return session.query(EmailDraft).filter_by(id=draft_id).first()

    @classmethod
    def save_generation_result(
        cls,
        outreach_type: str,
        entity_name: str,
        contact_name: Optional[str],
        recipient_email: Optional[str],
        selected_subject: str,
        subject_options: List[str],
        email_body: str,
        alternative_drafts: List[str],
        research_summary: str,
        personalization_reasoning: str,
        offer_reasoning: str,
        unsupported_claims_warnings: List[str],
        word_count: int,
        quality_score: float,
        quality_notes: str,
        ai_provider: str,
        ai_model: str,
        applied_memory_rules: List[str],
        prospect_id: Optional[int] = None,
    ) -> EmailDraft:
        """Persists newly generated or manually created email draft."""
        with get_db_session() as session:
            draft = EmailDraft(
                prospect_id=prospect_id,
                outreach_type=outreach_type,
                recipient_name=contact_name,
                recipient_entity=entity_name,
                recipient_email=recipient_email,
                subject_options=json.dumps(subject_options),
                selected_subject=selected_subject,
                email_body=email_body,
                alternative_drafts=json.dumps(alternative_drafts),
                research_summary=research_summary,
                personalization_reasoning=personalization_reasoning,
                offer_reasoning=offer_reasoning,
                unsupported_claims_warnings=json.dumps(unsupported_claims_warnings),
                word_count=word_count,
                quality_score=quality_score,
                quality_notes=quality_notes,
                ai_provider=ai_provider,
                ai_model=ai_model,
                approval_status="draft",
                applied_memory_rules=json.dumps(applied_memory_rules),
                version=1,
                is_sent=False,
            )
            session.add(draft)
            session.flush()
            session.refresh(draft)
            return draft

    @classmethod
    def duplicate_draft(cls, draft_id: int) -> Optional[EmailDraft]:
        with get_db_session() as session:
            orig = session.query(EmailDraft).filter_by(id=draft_id).first()
            if not orig:
                return None
            clone = EmailDraft(
                prospect_id=orig.prospect_id,
                outreach_type=orig.outreach_type,
                recipient_name=orig.recipient_name,
                recipient_entity=f"{orig.recipient_entity} (Copy)",
                recipient_email=orig.recipient_email,
                subject_options=orig.subject_options,
                selected_subject=orig.selected_subject,
                email_body=orig.email_body,
                alternative_drafts=orig.alternative_drafts,
                research_summary=orig.research_summary,
                personalization_reasoning=orig.personalization_reasoning,
                offer_reasoning=orig.offer_reasoning,
                unsupported_claims_warnings=orig.unsupported_claims_warnings,
                word_count=orig.word_count,
                quality_score=orig.quality_score,
                quality_notes=orig.quality_notes,
                ai_provider=orig.ai_provider,
                ai_model=orig.ai_model,
                approval_status="draft",
                applied_memory_rules=orig.applied_memory_rules,
                version=1,
                parent_id=orig.id,
                is_sent=False,
            )
            session.add(clone)
            session.flush()
            session.refresh(clone)
            return clone

    @classmethod
    def delete_draft(cls, draft_id: int) -> bool:
        with get_db_session() as session:
            draft = session.query(EmailDraft).filter_by(id=draft_id).first()
            if draft:
                session.delete(draft)
                return True
        return False

    @classmethod
    def export_drafts_csv(cls, drafts: List[EmailDraft]) -> str:
        """Exports drafts as a clean CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID",
            "Outreach Type",
            "Recipient Entity",
            "Recipient Name",
            "Recipient Email",
            "Subject",
            "Body",
            "Word Count",
            "Status",
            "AI Provider",
            "AI Model",
            "Created At",
        ])
        for d in drafts:
            writer.writerow([
                d.id,
                d.outreach_type,
                d.recipient_entity,
                d.recipient_name,
                d.recipient_email,
                d.selected_subject,
                d.email_body,
                d.word_count,
                d.approval_status,
                d.ai_provider,
                d.ai_model,
                d.created_at.isoformat() if d.created_at else "",
            ])
        return output.getvalue()

