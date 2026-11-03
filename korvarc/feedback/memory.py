"""Three-tier persistent feedback memory engine with preference confirmation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from korvarc.database.connection import get_db_session
from korvarc.database.schema import EmailDraft, MemoryRule

FEEDBACK_REASONS = [
    "Too generic",
    "Too robotic",
    "Too long",
    "Too flattering",
    "Weak subject",
    "Poor personalization",
    "Weak offer",
    "Poor CTA",
    "Unsupported claim",
    "Incorrect information",
    "Wrong tone",
    "Other",
]


class MemoryEngine:
    """Manages 3-level persistent memory rules and retrieval-based learning."""

    @classmethod
    def get_active_rules(cls, outreach_type: str = "influencer") -> List[str]:
        """Retrieves active confirmed preferences across Level 1 (Global) and Level 2 (Outreach specific)."""
        rules = []
        with get_db_session() as session:
            query = (
                session.query(MemoryRule)
                .filter(MemoryRule.is_active == True, MemoryRule.is_approved == True)
                .filter(MemoryRule.outreach_type.in_(["all", outreach_type]))
                .order_by(MemoryRule.level.asc(), MemoryRule.id.asc())
            )
            for r in query.all():
                rules.append(r.rule_text)
        return rules

    @classmethod
    def get_approved_examples(cls, outreach_type: str = "influencer", limit: int = 2) -> List[Dict[str, str]]:
        """Retrieves verified approved drafts to serve as few-shot prompt demonstrations."""
        examples = []
        with get_db_session() as session:
            drafts = (
                session.query(EmailDraft)
                .filter(EmailDraft.outreach_type == outreach_type)
                .filter(EmailDraft.approval_status == "approved")
                .order_by(EmailDraft.updated_at.desc())
                .limit(limit)
                .all()
            )
            for d in drafts:
                examples.append({
                    "subject": d.selected_subject,
                    "body": d.email_body,
                    "recipient": d.recipient_entity or d.recipient_name or "Partner",
                })
        return examples

    @classmethod
    def get_rejected_lessons(cls, outreach_type: str = "influencer", limit: int = 3) -> List[Dict[str, str]]:
        """Retrieves recent negative feedback to actively instruct the model what to avoid."""
        lessons = []
        with get_db_session() as session:
            drafts = (
                session.query(EmailDraft)
                .filter(EmailDraft.outreach_type == outreach_type)
                .filter(EmailDraft.approval_status == "rejected")
                .order_by(EmailDraft.updated_at.desc())
                .limit(limit)
                .all()
            )
            for d in drafts:
                reasons = []
                try:
                    reasons = json.loads(d.feedback_reasons or "[]")
                except Exception:
                    pass
                reason_str = ", ".join(reasons) if reasons else "Quality standards not met"
                lessons.append({
                    "reason": reason_str,
                    "notes": d.free_text_feedback or "",
                })
        return lessons

    @classmethod
    def record_feedback(
        cls,
        draft_id: int,
        action: str,  # "approve" | "reject" | "save_edit"
        rating: Optional[int] = None,
        feedback_reasons: Optional[List[str]] = None,
        free_text: Optional[str] = None,
        edited_body: Optional[str] = None,
        selected_subject: Optional[str] = None,
    ) -> EmailDraft:
        """Records user feedback, saves edits, and creates proposed memory rules if applicable."""
        reasons_list = feedback_reasons or []
        free_text_clean = free_text.strip() if free_text else None

        with get_db_session() as session:
            draft = session.query(EmailDraft).filter_by(id=draft_id).first()
            if not draft:
                raise ValueError(f"Draft with ID {draft_id} not found.")

            # If user edited the body
            if edited_body and edited_body.strip() != draft.email_body.strip():
                # Update body and increment version
                draft.email_body = edited_body.strip()
                words = [w for w in draft.email_body.split() if w.strip()]
                draft.word_count = len(words)
                draft.version += 1

            if selected_subject and selected_subject.strip():
                draft.selected_subject = selected_subject.strip()

            if rating is not None:
                draft.user_rating = rating

            draft.feedback_reasons = json.dumps(reasons_list)
            draft.free_text_feedback = free_text_clean

            if action == "approve":
                draft.approval_status = "approved"
            elif action == "reject":
                draft.approval_status = "rejected"
            elif action == "save_edit":
                draft.approval_status = "draft"

            draft.updated_at = datetime.now(timezone.utc)

            # If meaningful free-text guidance or high-priority structured rejection reason is provided,
            # synthesize a proposed memory rule for operator confirmation
            if free_text_clean or (action == "reject" and reasons_list):
                rule_text = ""
                source_desc = f"From feedback on Draft #{draft.id} ({draft.recipient_entity or 'Direct'})"

                if free_text_clean:
                    rule_text = free_text_clean
                elif "Too long" in reasons_list:
                    rule_text = f"Keep {draft.outreach_type} outreach emails concise and well under target word count."
                elif "Too flattering" in reasons_list:
                    rule_text = "Eliminate all flattery or generic enthusiasm; maintain pure commercial peer perspective."
                elif "Too generic" in reasons_list:
                    rule_text = "Require deep technical grounding and specific feature references before sending."
                elif "Weak subject" in reasons_list:
                    rule_text = "Subject lines must be strictly curiosity-based or cite a specific verified technical topic."
                elif "Weak offer" in reasons_list:
                    rule_text = "Clearly explain the commercial matchmaking benefit and why the developer tool aligns."
                else:
                    rule_text = f"Avoid: {', '.join(reasons_list)}."

                if rule_text:
                    proposed_rule = MemoryRule(
                        level=2 if draft.outreach_type in ("influencer", "brand") else 1,
                        outreach_type=draft.outreach_type,
                        rule_text=rule_text,
                        source_feedback=source_desc,
                        is_approved=False,  # Requires operator confirmation in Memory page
                        is_active=True,
                        version=1,
                        previous_versions=json.dumps([]),
                    )
                    session.add(proposed_rule)

            return draft

    @classmethod
    def get_all_rules(cls) -> List[MemoryRule]:
        with get_db_session() as session:
            return session.query(MemoryRule).order_by(MemoryRule.created_at.desc()).all()

    @classmethod
    def approve_rule(cls, rule_id: int) -> None:
        with get_db_session() as session:
            rule = session.query(MemoryRule).filter_by(id=rule_id).first()
            if rule:
                rule.is_approved = True
                rule.updated_at = datetime.now(timezone.utc)

    @classmethod
    def toggle_rule_active(cls, rule_id: int, active: bool) -> None:
        with get_db_session() as session:
            rule = session.query(MemoryRule).filter_by(id=rule_id).first()
            if rule:
                rule.is_active = active
                rule.updated_at = datetime.now(timezone.utc)

    @classmethod
    def update_rule_text(cls, rule_id: int, new_text: str) -> None:
        with get_db_session() as session:
            rule = session.query(MemoryRule).filter_by(id=rule_id).first()
            if rule:
                prev_versions = []
                try:
                    prev_versions = json.loads(rule.previous_versions or "[]")
                except Exception:
                    pass
                prev_versions.append({
                    "version": rule.version,
                    "text": rule.rule_text,
                    "archived_at": datetime.now(timezone.utc).isoformat(),
                })
                rule.previous_versions = json.dumps(prev_versions)
                rule.rule_text = new_text.strip()
                rule.version += 1
                rule.updated_at = datetime.now(timezone.utc)

    @classmethod
    def restore_previous_version(cls, rule_id: int, target_version: int) -> None:
        with get_db_session() as session:
            rule = session.query(MemoryRule).filter_by(id=rule_id).first()
            if rule:
                prev_versions = []
                try:
                    prev_versions = json.loads(rule.previous_versions or "[]")
                except Exception:
                    pass
                for ver in prev_versions:
                    if ver.get("version") == target_version:
                        current_text = rule.rule_text
                        prev_versions.append({
                            "version": rule.version,
                            "text": current_text,
                            "archived_at": datetime.now(timezone.utc).isoformat(),
                        })
                        rule.rule_text = ver.get("text")
                        rule.previous_versions = json.dumps(prev_versions)
                        rule.version += 1
                        rule.updated_at = datetime.now(timezone.utc)
                        break

    @classmethod
    def delete_rule(cls, rule_id: int) -> None:
        with get_db_session() as session:
            rule = session.query(MemoryRule).filter_by(id=rule_id).first()
            if rule:
                session.delete(rule)

