import re
from typing import Dict, Any, Tuple, Optional

CRISIS_PATTERNS = [
    r"\b(suicid|kill\s*myself|end\s*my\s*life|want\s*to\s*die|hurt\s*myself|self\s*harm)\b",
    r"\b(better\s*off\s*dead|no\s*reason\s*to\s*live|can'?t\s*go\s*on\s*anymore)\b",
    r"\b(hanging\s*myself|overdos(e|ing)|cut\s*my\s*wrists)\b"
]

DISTRESS_PATTERNS = [
    r"\b(hopeless|completely\s*broken|drowning|giving\s*up|so\s*depressed|worthless)\b",
    r"\b(panic\s*attack|can'?t\s*breathe|unbearable\s*pain)\b"
]

SENSITIVE_TRAUMA_PATTERNS = [
    r"\b(trauma|grief|passed away|died|death of|funeral|assault|abuse|ptsd|divorce|bereavement)\b"
]

EXPLICIT_INVITE_PATTERNS = [
    r"\b(talk about|discuss|process|reflect on|remembering|when .* died|my grief|my trauma|healing from)\b"
]

CRISIS_RESOURCES = {
    "us_ca_phone": "988",
    "us_ca_text": "Text HOME to 741741 (Crisis Text Line)",
    "uk_phone": "111 or 116 123 (Samaritans)",
    "international_url": "https://findahelpline.com",
    "message": (
        "If you are feeling overwhelmed, hopeless, or having thoughts of hurting yourself, "
        "please know you do not have to carry this alone. Free, confidential, and 24/7 support is available right now."
    )
}

class SafetyEngine:
    """
    Multi-Tier Crisis Triage and Constitutional Memory Verifier.
    """
    def __init__(self):
        self.crisis_regexes = [re.compile(p, re.IGNORECASE) for p in CRISIS_PATTERNS]
        self.distress_regexes = [re.compile(p, re.IGNORECASE) for p in DISTRESS_PATTERNS]
        self.trauma_regexes = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_TRAUMA_PATTERNS]
        self.invite_regexes = [re.compile(p, re.IGNORECASE) for p in EXPLICIT_INVITE_PATTERNS]

    def evaluate_text(self, text: str) -> Dict[str, Any]:
        """
        Evaluates input text against 3-tier safety levels.
        Returns:
            {
                "level": 1 | 2 | 3,
                "is_crisis": bool,
                "is_distressed": bool,
                "resources": Dict (if level 3),
                "guidance": str
            }
        """
        if not text:
            return {"level": 1, "is_crisis": False, "is_distressed": False}

        # Level 3: Immediate Crisis (Hard Intercept)
        for regex in self.crisis_regexes:
            if regex.search(text):
                return {
                    "level": 3,
                    "is_crisis": True,
                    "is_distressed": True,
                    "resources": CRISIS_RESOURCES,
                    "guidance": (
                        "Immediate crisis detected. Standard reflection paused. "
                        "Display emergency helpline resources and warm grounding immediately."
                    )
                }

        # Level 2: Elevated Distress
        for regex in self.distress_regexes:
            if regex.search(text):
                return {
                    "level": 2,
                    "is_crisis": False,
                    "is_distressed": True,
                    "guidance": (
                        "Elevated distress detected. Offer gentle empathy and validate feelings. "
                        "Avoid overconfident advice and gently encourage human/professional connection."
                    )
                }

        # Level 1: Normal Reflection
        return {
            "level": 1,
            "is_crisis": False,
            "is_distressed": False,
            "guidance": "Normal reflection mode."
        }

    def is_text_sensitive(self, text: str) -> bool:
        """Determines if text contains sensitive trauma/grief markers."""
        if not text:
            return False
        return any(regex.search(text) for regex in self.trauma_regexes)

    def verify_recalled_memory(self, user_prompt: str, memory_item: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Constitutional Verifier on Memory Recall:
        Prevents accidental trauma blurt-outs in casual conversation unless explicitly invited by user.
        """
        is_sensitive = bool(memory_item.get("is_sensitive")) or self.is_text_sensitive(memory_item.get("summary", ""))

        if not is_sensitive:
            return True, "APPROVED_STANDARD"

        # If memory is sensitive, check if user explicitly invited discussing it
        for inv in self.invite_regexes:
            if inv.search(user_prompt):
                return True, "EXPLICIT_USER_INVITATION"

        return False, "SUPPRESSED_CASUAL_CONTEXT"

safety_engine = SafetyEngine()
