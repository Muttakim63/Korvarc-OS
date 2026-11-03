"""Pydantic data schemas for validation and structured generation."""

from __future__ import annotations

from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ResearchObservation(BaseModel):
    source: str = Field(..., description="Source of the observation (e.g. YouTube oEmbed, Website Meta, User Input)")
    url: Optional[str] = Field(None, description="Source URL where data was fetched")
    observation: str = Field(..., description="Factual observation about content, audience, or product")
    evidence: str = Field(..., description="Direct quote, snippet, or metric serving as proof")
    retrieved_at: str = Field(..., description="ISO timestamp or date string of retrieval")
    verification_status: Literal["verified", "user_provided", "ai_interpretation", "unknown"] = Field(
        ..., description="Verification classification of the observation"
    )
    confidence: Literal["high", "medium", "low"] = Field("high", description="Confidence level in the finding")


class ResearchResult(BaseModel):
    target_name: str
    target_type: Literal["influencer", "brand"]
    input_url: Optional[str] = None
    observations: List[ResearchObservation] = Field(default_factory=list)
    extracted_topics: List[str] = Field(default_factory=list)
    potential_matches: List[str] = Field(default_factory=list)
    raw_summary: str = ""
    limitation_notes: Optional[str] = None


class GenerationRequest(BaseModel):
    outreach_type: Literal["influencer", "brand"] = "influencer"
    contact_name: Optional[str] = None
    entity_name: str
    url: Optional[str] = None
    email: Optional[str] = None
    additional_context: Optional[str] = None
    user_pasted_content: Optional[str] = None
    campaign_objective: str = "Commercial sponsorship exploration"
    desired_tone: str = "Confident, concise, peer-to-peer"
    target_word_count: int = 50
    provider: Literal["openai", "claude"] = "openai"
    model_name: Optional[str] = None
    sender_first_name: Optional[str] = None
    related_entity_id: Optional[int] = None


class EmailGenerationResult(BaseModel):
    subject_lines: List[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Exactly three distinct, compelling, curiosity-based or verified-observation subject lines",
    )
    primary_draft: str = Field(
        ..., description="Recommended primary email draft adhering strictly to target length and structure"
    )
    alternative_drafts: List[str] = Field(
        default_factory=list, description="Up to two alternative angles or draft variations"
    )
    personalization_explanation: str = Field(
        ..., description="Explanation of why this personalization works and connects to verified content"
    )
    offer_relevance: str = Field(
        ..., description="Explanation of why the commercial opportunity/brand match makes sense"
    )
    unsupported_claims_warnings: List[str] = Field(
        default_factory=list, description="Factual warnings if any assertion cannot be firmly verified"
    )
    word_count: int = Field(default=0, description="Calculated word count of the primary draft")
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Quality and grounding evaluation score")
    quality_notes: str = Field("", description="Agency compliance & quality assessment")
    research_grounding: List[str] = Field(
        default_factory=list, description="Verified facts directly utilized in this generation"
    )
    applied_memory_rules: List[str] = Field(
        default_factory=list, description="List of active memory rules enforced in this draft"
    )

    @field_validator("word_count", mode="before")
    def compute_word_count(cls, v, info):
        # Automatically compute word count if not set or zero
        if (not v or v == 0) and "primary_draft" in info.data:
            words = [w for w in info.data["primary_draft"].split() if w.strip()]
            return len(words)
        return v


class FeedbackSubmission(BaseModel):
    draft_id: int
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_reasons: List[str] = Field(default_factory=list)
    free_text: Optional[str] = None
    edited_body: Optional[str] = None
    action: Literal["approve", "reject", "save_edit"] = "approve"


class ComparisonResult(BaseModel):
    openai_result: Optional[EmailGenerationResult] = None
    claude_result: Optional[EmailGenerationResult] = None
    differences_summary: Optional[str] = None

