import re
import datetime
from typing import Dict, List, Any, Optional, Tuple
from storage import storage
from safety_engine import safety_engine

def resolve_salutation_name(display_name: Optional[str]) -> str:
    """Returns a friendly conversational name, avoiding 'My Space' or default system identifiers."""
    if not display_name:
        return "Friend"
    clean = display_name.strip()
    if clean.lower() in ["my space", "default", "default_user", "friend", "user", "workspace", "none"]:
        return "Friend"
    return clean

class MemoryEngine:
    """
    Stateful Autobiographical Memory Engine (Judge-Store-Recall).
    Manages 2D Affective Scoring, Entity Knowledge Graphs, and Constitutional Verification.
    """
    def __init__(self, storage_manager=storage, safety_mgr=safety_engine):
        self.storage = storage_manager
        self.safety = safety_mgr

    # ---------------- 1. JUDGE STAGE ---------------- #

    def judge_interaction(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        Judge Stage: Analyzes conversational turns for durable facts, 2D affect,
        significance importance (1-10), sensitivity, and knowledge graph relations.
        """
        if not text or len(text.strip()) < 5:
            return {
                "worth_remembering": False,
                "importance": 1,
                "valence": 0.0,
                "arousal": 0.0,
                "entities": [],
                "relations": [],
                "is_sensitive": False
            }

        extracted_entities = []
        extracted_relations = []
        importance = 3

        # 1. Detect People & Roles
        people_patterns = [
            r"\bmy\s+(manager|boss|lead|team lead|coworker|colleague|partner|spouse|wife|husband|friend|therapist|doctor|mentor)\s+([A-Z][a-z]+)\b",
            r"\b([A-Z][a-z]+)\s+is\s+my\s+(manager|boss|lead|coworker|colleague|partner|spouse|wife|husband|friend)\b",
        ]
        for pat in people_patterns:
            matches = re.finditer(pat, text)
            for m in matches:
                if len(m.groups()) == 2:
                    if m.group(1).lower() in ["manager", "boss", "lead", "team lead", "coworker", "colleague", "partner", "spouse", "wife", "husband", "friend", "therapist", "doctor", "mentor"]:
                        role, name = m.group(1).capitalize(), m.group(2)
                    else:
                        name, role = m.group(1), m.group(2).capitalize()
                    
                    extracted_entities.append({"category": "person", "name": name, "value": f"{role} in user's life"})
                    extracted_relations.append({"source": name, "target": "User", "relation": f"IS_{role.upper()}_OF"})
                    importance += 3

        # 2. Detect Goals & Commitments
        goal_matches = re.finditer(r"\b(?:my goal is|i want to|i am trying to|i'm working on|aiming to)\s+([^.,;\n]{5,60})", text, re.IGNORECASE)
        for gm in goal_matches:
            goal_text = gm.group(1).strip().capitalize()
            key = f"Goal: {goal_text[:30]}"
            extracted_entities.append({"category": "goal", "name": key, "value": goal_text})
            extracted_relations.append({"source": "User", "target": key, "relation": "STRIVES_FOR"})
            importance += 2

        # 3. Detect Stressors & Anxieties
        stress_matches = re.finditer(r"\b(?:stressed about|worried about|anxious about|struggling with|frustrated by|overwhelmed by)\s+([^.,;\n]{5,60})", text, re.IGNORECASE)
        for sm in stress_matches:
            stress_text = sm.group(1).strip().capitalize()
            key = f"Stressor: {stress_text[:30]}"
            extracted_entities.append({"category": "stressor", "name": key, "value": stress_text})
            extracted_relations.append({"source": key, "target": "User", "relation": "STRESSES"})
            importance += 2

        # 4. Detect Values & Core Needs
        val_matches = re.finditer(r"\b(?:i value|important to me to|i deeply care about|my boundary is)\s+([^.,;\n]{5,60})", text, re.IGNORECASE)
        for vm in val_matches:
            val_text = vm.group(1).strip().capitalize()
            key = f"Value: {val_text[:30]}"
            extracted_entities.append({"category": "value", "name": key, "value": val_text})
            extracted_relations.append({"source": "User", "target": key, "relation": "VALUES"})
            importance += 3

        # 5. Calculate 2D Affect (Valence & Arousal)
        valence, arousal = self._estimate_affect(text)

        # 6. Check Sensitivity
        is_sensitive = self.safety.is_text_sensitive(text)
        if is_sensitive:
            importance = max(importance, 7)

        importance = min(10, max(1, importance))
        worth_remembering = (importance >= 4 or len(extracted_entities) > 0 or is_sensitive)

        return {
            "worth_remembering": worth_remembering,
            "importance": importance,
            "valence": valence,
            "arousal": arousal,
            "entities": extracted_entities,
            "relations": extracted_relations,
            "is_sensitive": is_sensitive
        }

    def _estimate_affect(self, text: str) -> Tuple[float, float]:
        """Estimates 2D Affect coordinates (Valence in [-1,1], Arousal in [-1,1])."""
        t = text.lower()
        
        # Valence cues
        pos_words = ["happy", "grateful", "joyful", "relieved", "proud", "excited", "peaceful", "calm", "confident", "good", "great"]
        neg_words = ["anxious", "sad", "hopeless", "frustrated", "overwhelmed", "angry", "terrible", "drowning", "stressed", "bad"]
        
        # Arousal cues
        high_arousal = ["panicked", "furious", "hyper", "racing", "alarmed", "urgent", "ecstatic", "restless", "screaming"]
        low_arousal = ["exhausted", "tired", "burned out", "numb", "lethargic", "calm", "relaxed", "peaceful", "sleepy"]

        pos_count = sum(1 for w in pos_words if w in t)
        neg_count = sum(1 for w in neg_words if w in t)
        high_count = sum(1 for w in high_arousal if w in t)
        low_count = sum(1 for w in low_arousal if w in t)

        valence = 0.0
        if pos_count > 0 or neg_count > 0:
            valence = (pos_count - neg_count) / max(1, pos_count + neg_count)

        arousal = 0.0
        if high_count > 0 or low_count > 0:
            arousal = (high_count - low_count) / max(1, high_count + low_count)

        return round(max(-1.0, min(1.0, valence)), 2), round(max(-1.0, min(1.0, arousal)), 2)

    # ---------------- 2. STORE STAGE ---------------- #

    def synthesize_clean_summary(self, text: str, judge_res: Dict[str, Any]) -> str:
        """Cleans conversational meta-prompts into concise, durable memory summaries."""
        t = text.strip()
        
        # Check extracted entities first
        for ent in judge_res.get("entities", []):
            if ent.get("category") == "goal":
                val = ent.get("value", "").strip()
                return f"Goal: {val}" if not val.lower().startswith("goal") else val
            elif ent.get("category") == "person":
                return f"Relationship: {ent.get('name')} ({ent.get('value', '')})"
            elif ent.get("category") == "stressor":
                return f"Stressor: {ent.get('value', '').strip()}"
            elif ent.get("category") == "value":
                return f"Core Value: {ent.get('value', '').strip()}"
        
        # Clean conversational meta-prompts
        cleaned = re.sub(r"^(?:can you|could you|please|i want to|let'?s|i am trying to|help me|tell me|let)\s+(?:recall|remember|check|see|review|practice|continue practice)\s+(?:what|how|if|about|the)?\s*", "", t, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"(?:,\s*)?(?:can you recall|what we need to do|what we have practice|what i hav practice|and what we are pending|what should we do).*$", "", cleaned, flags=re.IGNORECASE).strip()
        
        if len(cleaned) >= 8:
            return cleaned[0].upper() + cleaned[1:]
        
        return t[:150]

    def store_interaction_memory(self, user_id: str, text: str, date_str: Optional[str] = None) -> Optional[int]:
        """
        Store Stage: Persists verbatim memory with embeddings and links into Knowledge Graph.
        """
        if not date_str:
            date_str = datetime.date.today().isoformat()

        judge_res = self.judge_interaction(user_id, text)
        if not judge_res["worth_remembering"]:
            return None

        # 1. Save Profile Facts & KG Entities
        for ent in judge_res["entities"]:
            self.storage.save_profile_fact(user_id, category=ent["category"], key=ent["name"], value=ent["value"])
            self.storage.add_or_update_entity(user_id, name=ent["name"], category=ent["category"], emotional_weight=judge_res["valence"])

        # 2. Save Knowledge Graph Relations
        for rel in judge_res["relations"]:
            self.storage.add_relation(user_id, source_name=rel["source"], target_name=rel["target"], relation_type=rel["relation"])

        # 3. Save Atomic Episodic Memory with Dense Embedding and Clean Summary
        summary = self.synthesize_clean_summary(text, judge_res)
        keywords = ", ".join([e["name"] for e in judge_res["entities"]])
        valence_str = "Positive" if judge_res["valence"] > 0.2 else ("Negative" if judge_res["valence"] < -0.2 else "Neutral")

        mem_id = self.storage.add_episodic_memory(
            user_id=user_id,
            date=date_str,
            memory_type="conversation_turn",
            summary=summary,
            raw_snippet=text.strip(),
            emotional_valence=valence_str,
            valence_score=judge_res["valence"],
            arousal_score=judge_res["arousal"],
            importance_score=judge_res["importance"],
            keywords=keywords,
            is_sensitive=judge_res["is_sensitive"]
        )

        return mem_id

    # ---------------- 3. RECALL STAGE (CONSTITUTIONAL) ---------------- #

    def recall_memories(self, user_id: str, query: str = "", limit: int = 4) -> List[Dict[str, Any]]:
        """
        Recall Stage: Hybrid dense+lexical search filtered by the Constitutional Verifier with deduplication.
        """
        if not query:
            raw_memories = self.storage.get_episodic_memories(user_id, limit=limit * 2)
        else:
            raw_memories = self.storage.hybrid_search_memories(user_id, query=query, limit=limit * 2, min_importance=1, include_sensitive=True)

        verified_memories = []
        seen_summaries = set()

        for mem in raw_memories:
            norm = " ".join(re.findall(r"\w+", mem.get("summary", "").lower()))
            if not norm or norm in seen_summaries:
                continue

            approved, reason = self.safety.verify_recalled_memory(query, mem)
            if approved:
                seen_summaries.add(norm)
                mem["recall_reason"] = f"Relevance score {mem.get('composite_score', 0.8):.2f} ({reason})"
                verified_memories.append(mem)
                self.storage.log_memory_action(
                    user_id=user_id,
                    action="recalled",
                    memory_id=mem["id"],
                    details=f"Recalled for query: '{query[:50]}'",
                    reason=reason,
                    verification_status="APPROVED"
                )
            else:
                self.storage.log_memory_action(
                    user_id=user_id,
                    action="recalled",
                    memory_id=mem["id"],
                    details=f"Suppressed sensitive memory for query: '{query[:50]}'",
                    reason=reason,
                    verification_status="SUPPRESSED_CONSTITUTIONAL"
                )

            if len(verified_memories) >= limit:
                break

        return verified_memories

    # ---------------- 4. CONTEXT ENVELOPE ASSEMBLY ---------------- #

    def retrieve_context(self, user_id: str, query: str = "", current_date: Optional[str] = None, limit: int = 4) -> Dict[str, Any]:
        """Gathers multi-source context from profile, knowledge graph, tasks, and memories."""
        if not current_date:
            current_date = datetime.date.today().isoformat()

        user = self.storage.get_user_by_id(user_id) or {"display_name": "Friend", "username": "user"}
        profile_facts = self.storage.get_profile_facts(user_id)
        knowledge_graph = self.storage.get_knowledge_graph(user_id)
        active_tasks = self.storage.get_tasks(user_id, status="pending")
        memories = self.recall_memories(user_id, query=query, limit=limit)
        recent_cards = self.storage.get_reflection_cards(user_id)

        workspaces = self.storage.get_all_workspaces(user_id, limit=5)
        mood_history = [{"date": w["date"], "mood": w["mood"], "energy": w["energy"]} for w in workspaces if w.get("mood")]

        return {
            "user": user,
            "profile_facts": profile_facts,
            "knowledge_graph": knowledge_graph,
            "active_tasks": active_tasks,
            "relevant_memories": memories,
            "recent_reflection_cards": recent_cards[:2],
            "mood_history": mood_history
        }

    def format_context_envelope(self, user_id: str, context: Dict[str, Any], is_new_session: bool = True, active_mode: Optional[str] = None) -> str:
        """Assembles the unforgeable multi-user context envelope with adaptive directives."""
        user = context.get("user", {})
        display_name = resolve_salutation_name(user.get("display_name"))
        username = user.get("username", "user")
        today_formatted = datetime.date.today().strftime("%A, %B %d, %Y")

        facts = context.get("profile_facts", [])
        kg = context.get("knowledge_graph", {})
        memories = context.get("relevant_memories", [])
        tasks = context.get("active_tasks", [])
        cards = context.get("recent_reflection_cards", [])
        moods = context.get("mood_history", [])

        lines = [
            f"[SYSTEM CONTEXT & AUTOBIOGRAPHICAL MEMORY ENVELOPE (V2.0)]",
            f"Active User: {display_name} (@{username} | ID: {user_id}) | Date: {today_formatted}",
            f"Companion Stance: Thoughtful Friend, Perceptive Coach & Mentor Meeting Again",
            ""
        ]

        if facts:
            lines.append("KNOWN USER PROFILE, GOALS & VALUES:")
            for f in facts[:8]:
                lines.append(f"- [{f['category'].upper()}] {f['key']}: {f['value']}")
            lines.append("")

        if kg.get("relations"):
            lines.append("LIFE KNOWLEDGE GRAPH & RELATIONSHIPS:")
            for r in kg["relations"][:5]:
                lines.append(f"- ({r['source_name']}) --[{r['relation_type']}]--> ({r['target_name']})")
            lines.append("")

        if tasks:
            lines.append("ACTIVE TASKS & COMMITMENTS:")
            seen_tasks = set()
            for t in tasks:
                t_title = t['title'].strip()
                if t_title.lower() not in seen_tasks:
                    seen_tasks.add(t_title.lower())
                    due_str = f" (Due: {t['due_date']})" if t.get("due_date") else ""
                    lines.append(f"- [ ] {t_title}{due_str}")
                if len(seen_tasks) >= 4:
                    break
            lines.append("")

        if memories:
            lines.append("PAST SESSIONS, REFLECTIONS & RECALLED CONTEXT:")
            seen_mems = set()
            for m in memories:
                m_sum = m['summary'].strip()
                if m_sum.lower() not in seen_mems:
                    seen_mems.add(m_sum.lower())
                    lines.append(f"- [{m['date']}] {m_sum} (Valence: {m.get('emotional_valence')})")
                if len(seen_mems) >= 4:
                    break
            lines.append("")

        if cards:
            lines.append("RECENT REFLECTION TAKEAWAYS:")
            for c in cards[:2]:
                lines.append(f"- [{c['date']}] Trigger: {c['what_happened'][:70]} | Takeaway: {c['what_i_want_to_remember'][:70]}")
            lines.append("")

        if moods:
            recent_mood_str = ", ".join([f"{m['date'][-5:]}: {m['mood']}/{m['energy']}" for m in moods[:3]])
            lines.append(f"RECENT MOOD TREND: {recent_mood_str}")
            lines.append("")

        lines.append("CONVERSATIONAL DIRECTIVES:")
        lines.append(f"1. Address {display_name} naturally with genuine warmth, incisive intelligence, and zero robotic boilerplate.")
        lines.append(f"2. Seamlessly remember and build upon past conversations, interview prep, and goals without asking {display_name} to repeat background context.")
        if is_new_session:
            lines.append(f"3. MEETING AGAIN (FIRST TURN TODAY): Greet {display_name} like a friend and coach meeting again. Acknowledge what was practiced or discussed previously, check in on how they are arriving today, and directly engage with their message.")
        lines.append(f"4. Dynamically calibrate between empathetic listening, practical coaching, and constructive interview drills based on what {display_name} needs.")
        lines.append("================================================================================")

        return "\n".join(lines)

    def generate_local_response(self, user_id: str, text: str, mode: Optional[str] = None) -> str:
        """
        Generates a warm, structured, grounded local companion response
        when browser stream is idle or offline, using autonomous intent sensing.
        """
        user = self.storage.get_user_by_id(user_id) or {"display_name": "Friend"}
        display_name = resolve_salutation_name(user.get("display_name", "Friend"))
        
        # 1. Recall matching memories, pending tasks, and profile facts
        memories = self.recall_memories(user_id, query=text, limit=3)
        tasks = self.storage.get_tasks(user_id, status="pending")
        facts = self.storage.get_profile_facts(user_id)
        
        judge_res = self.judge_interaction(user_id, text)
        valence = judge_res.get("valence", 0.0)
        text_lower = text.lower()
        
        # Intent Heuristics
        is_greeting = any(k in text_lower for k in ["greeting", "greet me", "hello", "hi omni", "hey omni", "how are you", "what do you know about me", "briefing", "daily briefing", "welcome", "good morning", "good evening", "who am i", "recap what we are working on"])
        is_diary = any(k in text_lower for k in ["write my diary", "write diary", "journal entry", "journal this", "diary draft"])
        is_recall_query = any(k in text_lower for k in ["recall", "remember", "practice", "prepare", "interview", "review", "what did we", "what have we"])
        is_coaching = any(k in text_lower for k in ["coach me", "action plan", "how should i", "next step", "breakdown", "strategy"])
        is_framework = any(k in text_lower for k in ["framework", "mental model", "stoic", "cbt", "habit", "learn"])
        is_question = "?" in text or any(text_lower.startswith(w) for w in ["what", "how", "can you", "could you", "why", "where", "when", "tell me"])

        # Intent: Personalized Greeting / Daily Arrival Briefing
        if is_greeting:
            salutation = f", {display_name}" if display_name != "Friend" else ""
            greeting_lines = [f"Welcome back{salutation}! It's great to connect with you today.\n"]
            
            goals = [f['value'] for f in facts if f.get('category') == 'goal']
            if goals:
                greeting_lines.append("I'm keeping your core goals and focus areas in mind:")
                seen_goals = set()
                for g in goals:
                    if g.lower() not in seen_goals:
                        seen_goals.add(g.lower())
                        greeting_lines.append(f"- 🎯 **{g}**")
                greeting_lines.append("")
            elif memories:
                greeting_lines.append("I remember we've been working on your recent reflections and growth journey.\n")

            if tasks:
                greeting_lines.append("Here are your active commitments:")
                for t in tasks[:3]:
                    greeting_lines.append(f"- [ ] **{t['title']}**")
                greeting_lines.append("")

            greeting_lines.append("How are you feeling right now? We can continue interview preparation, reflect on today, or explore whatever is on your mind.")
            return "\n".join(greeting_lines)

        # Intent: Emotional Grounding / High Stress / Venting (Friend Engine Priority)
        is_stress_or_venting = valence < -0.2 or any(w in text_lower for w in ["overwhelmed", "stressed", "exhausted", "tired", "anxious", "burned out", "nervous", "scared", "worried", "panic", "drowning"])
        if is_stress_or_venting and not any(k in text_lower for k in ["drill", "start practice", "quiz me", "ask me a question"]):
            salutation = f", {display_name}" if display_name != "Friend" else ""
            topic_hint = ""
            if "toyota" in text_lower or "interview" in text_lower:
                topic_hint = " The Toyota interview is a major milestone, and it's completely natural to feel the nervousness and adrenaline."
            return (
                f"I hear you and I'm right here with you{salutation}.{topic_hint}\n\n"
                f"Let's take the pressure off for a minute. Take a slow, grounding breath.\n\n"
                f"You've already built solid groundwork on TPS and your STAR stories. What part feels most urgent or loud in your mind right now? We can just talk through it without rushing into drills until you feel centered."
            )

        # Intent: Diary / Journal Entry
        if is_diary:
            today_str = datetime.date.today().strftime("%B %d, %Y")
            return (
                f"**{today_str} — Daily Journal Entry**\n\n"
                f"Today I took time to check in honestly: *\"{text.strip()}\"*\n\n"
                f"Reflecting on my priorities and experiences keeps me centered, resilient, and clear on my next steps."
            )

        # Intent: Interview Prep / Practice / Recall
        if is_recall_query:
            salutation = f", {display_name}" if display_name != "Friend" else ""
            parts = [f"I remember our previous discussions{salutation}! Here is what we have in your memory and action plan:\n"]
            if memories:
                parts.append("### 🧠 Recalled Context:")
                seen_recalled = set()
                for m in memories:
                    s = m['summary'].strip()
                    if s.lower() not in seen_recalled:
                        seen_recalled.add(s.lower())
                        parts.append(f"- **{m['date']}**: {s}")
            else:
                parts.append(f"- We've been preparing for your key goals, focusing on calm confidence and practical execution.")
            
            matching_tasks = [t for t in tasks if any(w in t['title'].lower() for w in text_lower.split())] or tasks[:3]
            if matching_tasks:
                parts.append("\n### 📋 Action Steps:")
                seen_action_tasks = set()
                for t in matching_tasks:
                    if t['title'].lower() not in seen_action_tasks:
                        seen_action_tasks.add(t['title'].lower())
                        parts.append(f"- [ ] **{t['title']}** ({t.get('category', 'practice')})")
            
            if "toyota" in text_lower:
                parts.append(
                    f"\n**Toyota Game Plan Highlights**:\n"
                    f"1. **TPS & Kaizen**: Continuous improvement, 5 Whys, root cause elimination.\n"
                    f"2. **STAR Method**: Clear Situation, Task, Action, and measurable Results.\n\n"
                    f"Let's practice right now: **Tell me about a time you identified an operational or engineering bottleneck and how you led the team to resolve it.**"
                )
            else:
                parts.append(f"\nLet's jump into practicing right now! To begin: **Tell me about a challenging problem or project you tackled recently and what you learned.**")
            return "\n".join(parts)

        # Intent: Coaching / Strategy
        if is_coaching:
            salutation = f", {display_name}" if display_name != "Friend" else ""
            return (
                f"I'm with you{salutation}. Let's break this down into clear, high-leverage steps:\n\n"
                f"1. **Core Priority**: Focus on the single highest-impact outcome right now.\n"
                f"2. **Small Next Step**: What is one tiny 2-minute action that will create immediate momentum?\n\n"
                f"What part would you like to tackle first?"
            )

        # Intent: Wisdom & Mental Models
        if is_framework:
            return (
                f"A powerful mental model for this is the **Circle of Control** (Stoic / CBT framework): separating what you directly influence (your prep, mindset, breathing, effort) from what you don't (other people's reactions, past events).\n\n"
                f"Channeling 100% of your energy into your circle of control brings immediate clarity and calm."
            )

        # Intent: Direct Inquiry / Specific Question
        if is_question:
            salutation = f", {display_name}" if display_name != "Friend" else ""
            return (
                f"Regarding what you asked{salutation}: Let's look at this clearly.\n\n"
                f"Based on what you shared (*\"{text.strip()}\"*), the most effective move is to focus on what you can directly influence today.\n\n"
                f"What specific angle would you like to explore together?"
            )

        # Intent: Emotional Grounding / High Stress / Venting (Friend Engine)
        if valence < -0.2 or any(w in text_lower for w in ["overwhelmed", "stressed", "exhausted", "tired", "anxious", "burned out", "nervous", "scared", "worried"]):
            salutation = f", {display_name}" if display_name != "Friend" else ""
            return (
                f"I hear you and I'm right here with you{salutation}. It makes complete sense that you're feeling that way—you've got real stakes and high expectations on yourself.\n\n"
                f"Let's take the pressure off for a minute. Take a slow breath.\n\n"
                f"What part of this feels loudest or heaviest in your mind right now? We can just talk through it without rushing to fix anything."
            )
        elif valence > 0.2 or any(w in text_lower for w in ["happy", "proud", "excited", "great news", "won", "accomplished", "did it", "nailed it"]):
            salutation = f", {display_name}" if display_name != "Friend" else ""
            return (
                f"That is fantastic news{salutation}! I'm genuinely proud of you.\n\n"
                f"Take a moment to let that sink in. What felt like the most satisfying part of making that happen?"
            )
        else:
            salutation = f", {display_name}" if display_name != "Friend" else ""
            return (
                f"I'm with you{salutation}. Tell me what's on your mind today—whether you want to run through practice, think through a decision, or just decompress."
            )

    def generate_personalized_greeting(self, user_id: str) -> Dict[str, Any]:
        """Generates a warm, authentic daily greeting and recap as a real-life friend and coach."""
        user = self.storage.get_user_by_id(user_id) or {"display_name": "Friend"}
        display_name = resolve_salutation_name(user.get("display_name", "Friend"))
        salutation = f", {display_name}" if display_name != "Friend" else ""

        facts = self.storage.get_profile_facts(user_id)
        goals = [f['value'] for f in facts if f.get('category') == 'goal']
        tasks = self.storage.get_tasks(user_id, status="pending")
        memories = self.storage.get_episodic_memories(user_id, limit=4)

        lines = [f"**Good to see you back{salutation}!**\n"]

        has_toyota = any("toyota" in g.lower() for g in goals) or any("toyota" in m.get("summary", "").lower() for m in memories)

        if has_toyota:
            lines.append(
                "With your **Toyota interview** on the horizon, our main focus is keeping your narrative sharp, grounded, and confident. "
                "We've been zeroing in on high-impact engineering scenarios—connecting your technical depth with the practical root-cause problem solving and TPS leadership they look for.\n"
            )
            lines.append("How are you feeling heading into today's session? We can run through a behavioral mock, refine a specific system design scenario, or just talk through mindset and strategy.")
            starters = [
                {"label": "🚗 Run Toyota Mock Drill", "text": "Let's run a tough behavioral mock interview question for Toyota."},
                {"label": "⚡ Polish a STAR Scenario", "text": "Help me refine one of my key STAR leadership and engineering stories."},
                {"label": "🌿 Mindset & Calm Check-in", "text": "I want to do a quick mindset check-in to get centered before practicing."},
                {"label": "💬 Talk through strategy", "text": "Let's talk through high-level interview strategy and questions to ask the interviewer."}
            ]
        elif goals:
            clean_goals = []
            seen = set()
            for g in goals:
                if g.lower() not in seen:
                    seen.add(g.lower())
                    clean_goals.append(g)
            goals_text = ", ".join([f"**{g}**" for g in clean_goals[:2]])
            lines.append(f"I'm keeping your core priorities in sight, especially {goals_text}.\n")
            if tasks:
                task_titles = [t['title'] for t in tasks[:2]]
                lines.append(f"We also have pending commitments: *{', '.join(task_titles)}*.\n")
            lines.append("How are you feeling right now? Where would you like to direct our energy today?")
            starters = [
                {"label": "🎯 Focus on core goal", "text": f"Let's work on my main goal: {clean_goals[0]}."},
                {"label": "📋 Review pending tasks", "text": "Let's review my active action steps and knock out a quick win."},
                {"label": "🌿 Daily reflection", "text": "I'd like to do a quick check-in on my energy and mindset today."}
            ]
        else:
            lines.append(
                "I'm here as your dedicated friend and coach. Whether you want to reflect on how your day went, brainstorm through a dilemma, or build momentum on a new goal, I'm ready.\n"
            )
            lines.append("What's on your mind today?")
            starters = [
                {"label": "🌱 Set a new goal or milestone", "text": "I want to share a key goal I'm working towards so we can track it."},
                {"label": "🌿 Share how I'm feeling today", "text": "Here is what's currently on my mind and how I'm feeling today..."},
                {"label": "💡 Explore a mental model", "text": "Teach me a practical mental model to help with focus and clarity."}
            ]

        return {
            "greeting_markdown": "\n".join(lines),
            "starters": starters
        }

memory_engine = MemoryEngine()
