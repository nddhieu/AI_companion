import os
import sys
import json
import re
import datetime
import urllib.request
import urllib.error
from typing import Dict, Any, AsyncGenerator, Optional, List

from auth_manager import DEFAULT_USER_ID
from memory_engine import memory_engine
from tools_engine import tools_gateway
from subagents import subagent_dispatcher

MASTER_COMPANION_INSTRUCTION = """Role: You are Omni, a trusted real-life friend, perceptive coach, and strategic thought partner (v2.0).

Core Persona & Relational Attunement:
- Speak authentically, naturally, and warmly—like a brilliant mentor and close friend having a genuine conversation over coffee.
- ZERO Robotic Boilerplate: NEVER recite canned robotic phrases (e.g. 'How may I assist you today?', 'As an AI language model...', 'I hope this helps!', 'I am holding space for you', 'According to my database/records', 'Here is a breakdown...').
- Effortless Continuity: Talk to the user as someone you know well. Weave past conversations, goals (e.g., core values, daily habits, personal milestones), and emotional context into the dialogue naturally without forcing them to re-explain background.

Dynamic Dual-Engine Stance & Dynamic Behavioral Posture:
1. Emotional Resonance & Grounding:
   - When the user is venting, overwhelmed, anxious, or exhausted, BE A CALM, GROUNDED FRIEND FIRST.
   - Validate authentically, normalize their feelings, and help them take the pressure off.
   - Do NOT immediately bombard them with a 10-point advice listicle when they are sharing stress or vulnerability.
2. Incisive Thinking & Problem Solving:
   - When the user explores dilemmas or questions, offer direct, structured, insightful, and practical clarity.
   - Break complex situations into core priorities and 2-minute actionable next steps.
3. Proactive Coaching & Interactive Practice:
   - When the user is ready to practice, problem-solve, or prepare:
   - Jump directly into the arena with them! Actively run the drill or roleplay.
   - Ask realistic, incisive questions one at a time.
   - Give constructive, encouraging, and specific feedback (e.g., using STAR method, Kaizen, 5 Whys).
   - Keep answers clear, punchy, and interactive. Always leave the ball in their court with one natural next question or prompt.
4. Wisdom & Mental Models:
   - Naturally weave in practical frameworks (Stoic Circle of Control, CBT reframing, 2-Minute Gateway Habit, Essentialism) as intuitive real-life wisdom, never as dry academic lectures.
5. Authentic Synthesis & Journaling:
   - When synthesizing diary drafts or reflections, capture their authentic emotional truth, personal tone, and lessons learned with heartfelt resonance.
6. Seamless Memory & Context Integration:
   - Weave known user profile facts, past memories, active tasks, and knowledge graph relations into conversations organically without sounding like a database query.

Action & Tool Execution:
When helpful or requested, you can interact with memory, tasks, files, and web search by emitting a clean JSON action block:
```action
{
  "tool": "remember" | "search_memories" | "get_user_profile" | "create_task" | "list_tasks" | "complete_task" | "read_file" | "write_file" | "search_web" | "save_reflection_card" | "save_wisdom_lesson" | "log_daily_mood",
  "args": { ... }
}
```

Safety Boundary:
- You are a companion and coach, not a medical doctor or licensed clinical therapist.
- If severe crisis or self-harm arises, immediately prioritize human safety with emergency support (988 / 741741)."""

class GeminiApiEngine:
    """
    Direct Google Gemini API Engine for cloud deployments and Bring-Your-Own-Key (BYOK).
    Connects directly to Google's Gemini API over HTTPS without requiring a local Chrome browser.
    """
    def __init__(self):
        self.default_model = "gemini-2.5-flash"
        self.fallback_model = "gemini-1.5-flash"

    def _resolve_api_key(self, custom_key: Optional[str] = None) -> Optional[str]:
        """Resolves API key from custom parameter or environment variable."""
        if custom_key and custom_key.strip():
            return custom_key.strip()
        return os.environ.get("GEMINI_API_KEY", "").strip() or None

    async def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validates a user-provided Gemini API key against Google's API."""
        key = self._resolve_api_key(api_key)
        if not key:
            return {"valid": False, "message": "No API key provided."}

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "OmniCompanion/2.0"})
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                if resp.status == 200:
                    return {"valid": True, "message": "Gemini API key is valid and ready!"}
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                msg = err_body.get("error", {}).get("message", str(e))
            except Exception:
                msg = f"HTTP Error {e.code}: {e.reason}"
            return {"valid": False, "message": f"Invalid API key: {msg}"}
        except Exception as e:
            return {"valid": False, "message": f"Connection failed: {e}"}

        return {"valid": False, "message": "Unable to verify API key."}

    async def send_prompt_stream(
        self,
        user_text: str,
        user_id: str = DEFAULT_USER_ID,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes user prompt against Google Gemini API with Recall Enforcement Gate,
        context injection, streaming generation, and tool execution.
        """
        key = self._resolve_api_key(api_key)
        if not key:
            yield {
                "status": "error",
                "error": "No Gemini API key provided. Please open Settings (⚙️) and enter your free Gemini API key."
            }
            return

        # 1. RECALL ENFORCEMENT GATE: Judge & Store interaction memory
        memory_engine.store_interaction_memory(user_id=user_id, text=user_text)
        subagent_dispatcher.dispatch_background_consolidation(user_id=user_id)

        yield {"status": "thinking", "chunk": ""}

        # 2. Retrieve relevant context for this turn
        user_ctx = memory_engine.retrieve_context(user_id=user_id, query=user_text)
        envelope = memory_engine.format_context_envelope(user_id=user_id, context=user_ctx, is_new_session=False)

        # 3. Assemble contents payload for Gemini API
        system_instruction = f"{MASTER_COMPANION_INSTRUCTION}\n\n{envelope}"
        contents = [
            {
                "role": "user",
                "parts": [{"text": user_text}]
            }
        ]

        target_model = model_name or self.default_model
        stream_url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:streamGenerateContent?alt=sse&key={key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.95,
                "maxOutputTokens": 4096
            }
        }

        full_reply = ""
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                stream_url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "OmniCompanion/2.0"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30.0) as response:
                buffer = ""
                for line in response:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: "):
                        json_str = decoded[6:].strip()
                        if not json_str:
                            continue
                        try:
                            chunk_data = json.loads(json_str)
                            candidates = chunk_data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    text_part = part.get("text", "")
                                    if text_part:
                                        full_reply += text_part
                                        yield {
                                            "status": "streaming",
                                            "chunk": text_part,
                                            "full_text": full_reply
                                        }
                        except Exception:
                            continue

        except urllib.error.HTTPError as e:
            err_msg = str(e)
            try:
                err_json = json.loads(e.read().decode("utf-8"))
                err_msg = err_json.get("error", {}).get("message", str(e))
            except Exception:
                pass
            yield {"status": "error", "error": f"Gemini API Error ({e.code}): {err_msg}"}
            return
        except Exception as e:
            yield {"status": "error", "error": f"API Connection Error: {e}"}
            return

        # 4. Process Action / Tool Call blocks in response
        action_match = re.search(r"```action\s*([\s\S]*?)\s*```", full_reply)
        if action_match:
            try:
                action_data = json.loads(action_match.group(1).strip())
                tool_name = action_data.get("tool")
                tool_args = action_data.get("args", {})
                if tool_name:
                    yield {
                        "status": "tool_call",
                        "tool": tool_name,
                        "args": tool_args,
                        "full_text": full_reply
                    }
                    tool_res = await tools_gateway.execute_tool(user_id=user_id, name=tool_name, arguments=tool_args)
                    yield {
                        "status": "tool_result",
                        "tool": tool_name,
                        "result": tool_res,
                        "full_text": full_reply
                    }
            except Exception as e:
                yield {
                    "status": "tool_error",
                    "error": f"Tool execution failed: {e}",
                    "full_text": full_reply
                }

        yield {
            "status": "done",
            "full_text": full_reply
        }

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        user_id: str = DEFAULT_USER_ID,
        api_key: Optional[str] = None
    ) -> str:
        """Non-streaming single turn text completion via Gemini API."""
        key = self._resolve_api_key(api_key)
        if not key:
            raise ValueError("No Gemini API key provided. Please configure your API key in Settings.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.default_model}:generateContent?key={key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 2048}
        }
        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json", "User-Agent": "OmniCompanion/2.0"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=25.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join([p.get("text", "") for p in parts]).strip()
        return ""

gemini_api_engine = GeminiApiEngine()
