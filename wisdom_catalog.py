from typing import List, Dict, Optional

WISDOM_CATALOG: List[Dict[str, str]] = [
    {
        "id": "wisdom-01",
        "topic": "Fear of Criticism & Imposter Feelings",
        "title": "Feedback is Information, Not Identity",
        "author_source": "Douglas Stone & Sheila Heen (Thanks for the Feedback) / Carol Dweck",
        "concept_summary": "Criticism often triggers our threat response because we confuse who we are with what we produced. Separating your core worth from a piece of work allows you to evaluate feedback as neutral data.",
        "reflection_question": "What is 5% of this feedback that could actually help me grow, even if the tone or timing was imperfect?",
        "micro_practice": "Write down one observable fact from the feedback without attaching emotional self-judgment."
    },
    {
        "id": "wisdom-02",
        "topic": "Procrastination & Overwhelm",
        "title": "The 2-Minute Gateway Habit",
        "author_source": "James Clear (Atomic Habits) / Behavioral Activation",
        "concept_summary": "When a task feels heavy, our brain resists the anticipated emotional friction. Scaling a task down until it takes under two minutes eliminates resistance and activates momentum.",
        "reflection_question": "What is the smallest, almost ridiculously easy version of this task I could start right now?",
        "micro_practice": "Set a timer for 120 seconds and open the file, write 1 sentence, or clear 1 item."
    },
    {
        "id": "wisdom-03",
        "topic": "Perfectionism & Fear of Failure",
        "title": "Safe-to-Fail Experiments",
        "author_source": "Cognitive Behavioral Coaching / Amy Edmondson",
        "concept_summary": "Perfectionism treats every outcome as high-stakes judgment. Reframing a project as an 'experiment' creates psychological safety: an experiment cannot fail, it only generates results.",
        "reflection_question": "If failure in this situation carried zero threat to my worth, what would I test?",
        "micro_practice": "Define a 'Version 0.1' draft that is intentionally rough and shareable."
    },
    {
        "id": "wisdom-04",
        "topic": "Burnout & Overextension",
        "title": "Energy Management Over Time Management",
        "author_source": "Jim Loehr & Tony Schwartz (The Power of Full Engagement)",
        "concept_summary": "Time is finite, but energy is renewable. Burnout happens when we continuously output physical, emotional, and mental energy without deliberate oscillation between stress and recovery.",
        "reflection_question": "What activity today replenished my energy, and what drained it fastest?",
        "micro_practice": "Take a 10-minute non-screen sensory break (walk, breath, silence) before your next task."
    },
    {
        "id": "wisdom-05",
        "topic": "Interpersonal Conflict & Resentment",
        "title": "Boundaries are Distance to Love Both People",
        "author_source": "Prentis Hemphill / Harriet Lerner (The Dance of Anger)",
        "concept_summary": "Resentment is the emotional signal that a boundary has been crossed or unexpressed. Setting a clear boundary is an act of care that prevents the erosion of trust.",
        "reflection_question": "What am I saying 'yes' to on the outside while saying 'no' on the inside?",
        "micro_practice": "Draft one honest, respectful sentence: 'I want to support this, but I cannot take on X right now.'"
    },
    {
        "id": "wisdom-06",
        "topic": "Feeling Behind & Comparison Anxiety",
        "title": "Comparing Inwards, Not Upwards",
        "author_source": "Leon Festinger (Social Comparison Theory) / Stoic Philosophy",
        "concept_summary": "Social comparison measures your messy internal reality against someone else's curated highlight reel. Real progress is only measured against who you were six months ago.",
        "reflection_question": "What is one challenge I navigated this year that would have overwhelmed me two years ago?",
        "micro_practice": "List two pieces of evidence of your own growth from the past month."
    },
    {
        "id": "wisdom-07",
        "topic": "Self-Criticism & Guilt",
        "title": "The Compassionate Observer",
        "author_source": "Kristin Neff (Self-Compassion: The Proven Power of Being Kind to Yourself)",
        "concept_summary": "Self-criticism activates the fight-or-flight system against ourselves. Self-compassion is not letting yourself off the hook; it is speaking to yourself with the supportive tone of an encouraging mentor.",
        "reflection_question": "What would I say to a close friend in this exact situation with this exact feeling?",
        "micro_practice": "Speak that exact sentence to yourself silently with hand on chest."
    },
    {
        "id": "wisdom-08",
        "topic": "Decision Paralysis & Ambiguity",
        "title": "Satisficing Over Maximizing",
        "author_source": "Herbert Simon (Administrative Behavior) / Barry Schwartz",
        "concept_summary": "Maximizers seek the absolute best choice and suffer chronic regret. Satisficers define 'good enough' criteria upfront and move forward once those criteria are met.",
        "reflection_question": "What are the top 2 must-haves for this decision, ignoring all nice-to-haves?",
        "micro_practice": "Pick the option that meets the top 2 criteria and commit for 7 days."
    }
]

def get_all_wisdom_lessons() -> List[Dict[str, str]]:
    """Returns the full catalog of curated wisdom lessons."""
    return WISDOM_CATALOG

def find_matching_wisdom(query: str) -> List[Dict[str, str]]:
    """Finds matching lessons based on keyword overlap or situation."""
    query_lower = query.lower()
    matches = []
    
    for item in WISDOM_CATALOG:
        score = 0
        if any(w in query_lower for w in item["topic"].lower().split()):
            score += 2
        if any(w in query_lower for w in item["concept_summary"].lower().split()):
            score += 1
            
        if score > 0:
            matches.append((score, item))
            
    matches.sort(key=lambda x: x[0], reverse=True)
    if matches:
        return [m[1] for m in matches[:3]]
    return WISDOM_CATALOG[:3]
