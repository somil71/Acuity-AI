from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List

router = APIRouter()

# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class TriageRequest(BaseModel):
    symptoms: List[str] = Field(..., description="List of symptom keywords")
    symptom_description: str = Field(..., description="Free-text description of symptoms")
    pain_scale: int = Field(..., ge=1, le=10, description="Pain intensity 1-10")
    duration_days: int = Field(..., ge=0, description="How many days symptoms have persisted")
    age: int = Field(..., ge=0, le=150)
    gender: str


class TriageResponse(BaseModel):
    urgency: str           # "low" | "medium" | "high" | "emergency"
    urgency_color: str     # "green" | "amber" | "red" | "red-flashing"
    recommended_dept: str
    visit_type: str        # "new" | "follow_up"
    reasoning: str
    go_to_er: bool


# ─── Rule-based helpers ───────────────────────────────────────────────────────

_EMERGENCY_KEYWORDS = frozenset([
    "chest pain", "difficulty breathing", "unconscious", "stroke",
    "severe bleeding", "crushing chest", "cannot breathe",
])

_HIGH_KEYWORDS = frozenset([
    "fever", "vomiting blood", "severe headache", "vision loss",
])

_DEPT_KEYWORDS = {
    "Cardiology":  frozenset(["chest pain", "palpitations", "shortness of breath", "heart", "irregular heartbeat"]),
    "Orthopedics": frozenset(["joint pain", "bone", "fracture", "back pain", "knee", "shoulder", "hip", "ankle"]),
    "Pediatrics":  frozenset(["child", "infant", "baby", "pediatric", "vaccination"]),
}


def _normalise(symptoms: List[str]) -> List[str]:
    """Return lowercased, stripped symptom list."""
    return [s.lower().strip() for s in symptoms]


def _rule_based_urgency(symptoms: List[str], pain_scale: int, duration_days: int) -> str:
    """
    Classify urgency as one of: "emergency", "high", "medium", "low".
    Priority order: emergency > high > medium > low.
    """
    symptoms_lower = _normalise(symptoms)

    # EMERGENCY: any life-threatening keyword OR extreme pain
    if pain_scale >= 9 or any(kw in symptoms_lower for kw in _EMERGENCY_KEYWORDS):
        return "emergency"

    # HIGH: severe pain, prolonged symptoms, or serious secondary keywords
    if pain_scale >= 7 or duration_days > 14 or any(kw in symptoms_lower for kw in _HIGH_KEYWORDS):
        return "high"

    # MEDIUM: moderate pain or symptoms persisting more than a week
    if pain_scale >= 4 or duration_days > 7:
        return "medium"

    return "low"


def _rule_based_dept(symptoms: List[str]) -> str:
    """
    Map symptom list to a recommended department.
    Falls back to "General Physician" when no specialised match is found.
    """
    symptoms_lower = _normalise(symptoms)

    for dept, keywords in _DEPT_KEYWORDS.items():
        if any(kw in symptoms_lower for kw in keywords):
            return dept

    return "General Physician"


_URGENCY_COLOR_MAP = {
    "low":       "green",
    "medium":    "amber",
    "high":      "red",
    "emergency": "red-flashing",
}


def _build_reasoning(urgency: str, dept: str, pain_scale: int, duration_days: int, symptoms: List[str]) -> str:
    """Compose a human-readable explanation from the rule outputs."""
    symptom_summary = ", ".join(symptoms[:3]) if symptoms else "unspecified symptoms"
    if len(symptoms) > 3:
        symptom_summary += f" and {len(symptoms) - 3} more"

    urgency_phrases = {
        "emergency": (
            "EMERGENCY: Symptoms indicate a potentially life-threatening condition. "
            "Immediate emergency care is required — please call emergency services or go to the ER now."
        ),
        "high": (
            "HIGH PRIORITY: Symptoms are severe or have persisted for an extended period. "
            "You should seek medical attention today."
        ),
        "medium": (
            "MEDIUM PRIORITY: Symptoms are moderate. "
            "A same-day or next-day appointment is recommended."
        ),
        "low": (
            "LOW PRIORITY: Symptoms appear mild. "
            "A routine appointment within the next few days should be sufficient."
        ),
    }

    base = urgency_phrases[urgency]
    detail = (
        f" Reported symptoms: {symptom_summary}. "
        f"Pain scale: {pain_scale}/10. Duration: {duration_days} day(s). "
        f"Recommended department: {dept}."
    )
    return base + detail


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/assess", response_model=TriageResponse)
def assess_triage(request: TriageRequest):
    """
    Rule-based AI Symptom Triage.

    No authentication required — patients can triage before creating an account.
    No external API calls — fully local and instantaneous.
    """
    urgency = _rule_based_urgency(request.symptoms, request.pain_scale, request.duration_days)
    dept = _rule_based_dept(request.symptoms)
    color = _URGENCY_COLOR_MAP[urgency]
    go_to_er = urgency == "emergency"

    # Infer visit type from symptom description heuristic
    description_lower = request.symptom_description.lower()
    visit_type = "follow_up" if any(
        kw in description_lower for kw in ["follow", "follow-up", "check-up", "checkup", "review", "returning"]
    ) else "new"

    reasoning = _build_reasoning(urgency, dept, request.pain_scale, request.duration_days, request.symptoms)

    return TriageResponse(
        urgency=urgency,
        urgency_color=color,
        recommended_dept=dept,
        visit_type=visit_type,
        reasoning=reasoning,
        go_to_er=go_to_er,
    )
