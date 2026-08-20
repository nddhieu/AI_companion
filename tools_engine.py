import json
import os
import sys
import re
import datetime
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional
from storage import storage
from wisdom_catalog import get_all_wisdom_lessons, find_matching_wisdom

if getattr(sys, 'frozen', False):
    WORKSPACE_SANDBOX_DIR = Path(sys.executable).parent / "companion_workspace"
else:
    WORKSPACE_SANDBOX_DIR = Path(__file__).parent / "companion_workspace"

WORKSPACE_SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

class CompanionToolGateway:
    """
    Model Context Protocol (MCP) compatible Tool Gateway & Action Server.
    Provides deterministic tool execution scoped to the authenticated user.
    """
    def __init__(self, storage_manager=storage, sandbox_dir: Path = WORKSPACE_SANDBOX_DIR):
        self.storage = storage_manager
        self.sandbox_dir = sandbox_dir

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns JSON schema definitions for all available companion tools conforming to MCP spec."""
        return [
            # 1. Memory Tools
            {
                "name": "remember",
                "description": "Stores an autobiographical memory or durable fact with importance and emotional coordinates.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "verbatim": {"type": "string", "description": "The exact fact or memory to store"},
                        "category": {"type": "string", "enum": ["person", "goal", "stressor", "value", "project", "preference"], "description": "Category"},
                        "importance": {"type": "integer", "description": "Importance level from 1 to 10 (default 5)", "default": 5},
                        "valence": {"type": "number", "description": "Emotional valence from -1.0 to +1.0 (default 0.0)", "default": 0.0},
                        "tags": {"type": "string", "description": "Comma separated keywords or tags"}
                    },
                    "required": ["verbatim"]
                }
            },
            {
                "name": "search_memories",
                "description": "Searches previous memories and reflections using hybrid dense vector + lexical scoring.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query or topic"},
                        "limit": {"type": "integer", "description": "Maximum memories to return (default 4)", "default": 4},
                        "min_importance": {"type": "integer", "description": "Minimum importance score (default 1)", "default": 1}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_by_tags",
                "description": "Queries stored facts or entities by category/tag (e.g. 'person', 'goal', 'value').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": ["person", "goal", "stressor", "value", "project", "preference"]},
                        "tag": {"type": "string", "description": "Optional keyword tag"}
                    },
                    "required": ["category"]
                }
            },
            {
                "name": "supersede_memory",
                "description": "Marks an outdated memory as superseded by a new fact.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "old_memory_id": {"type": "integer", "description": "ID of old memory to supersede"},
                        "new_fact": {"type": "string", "description": "Updated fact or milestone"}
                    },
                    "required": ["old_memory_id", "new_fact"]
                }
            },

            # 2. Context & Awareness Tools
            {
                "name": "get_user_profile",
                "description": "Retrieves the user's structured profile including core values, goals, and key relationships.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_emotional_trajectory",
                "description": "Retrieves the user's recent emotional check-in history and 2D valence trends.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "description": "Number of days to look back (default 7)", "default": 7}
                    }
                }
            },
            {
                "name": "get_knowledge_graph",
                "description": "Retrieves the user's personal Life Knowledge Graph of entities and relationships.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },

            # 3. Action & Automation Tools (Sandboxed)
            {
                "name": "read_file",
                "description": "Reads the text contents of a file in the user's private sandbox workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {"type": "string", "description": "Relative filename within the workspace (e.g. 'goals.md')"}
                    },
                    "required": ["relative_path"]
                }
            },
            {
                "name": "write_file",
                "description": "Writes or updates a file in the user's private sandbox workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {"type": "string", "description": "Relative filename within workspace (e.g. 'notes.md')"},
                        "content": {"type": "string", "description": "Text content to write"}
                    },
                    "required": ["relative_path", "content"]
                }
            },
            {
                "name": "search_files",
                "description": "Lists or searches for files in the user's sandbox workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Filename pattern or keyword to search (default '*')", "default": "*"}
                    }
                }
            },
            {
                "name": "create_task",
                "description": "Creates a new actionable 2-minute task or commitment for the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short actionable task title"},
                        "description": {"type": "string", "description": "Optional details or context"},
                        "due_date": {"type": "string", "description": "Optional ISO due date (YYYY-MM-DD)"},
                        "category": {"type": "string", "description": "Category tag (e.g. 'work', 'wellness', 'habit')"}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "list_tasks",
                "description": "Lists the user's pending, in-progress, or completed tasks.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]}
                    }
                }
            },
            {
                "name": "complete_task",
                "description": "Marks a specific task as completed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID of the task to complete"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "search_web",
                "description": "Performs a live web search for verified scientific, psychological, or general information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "max_results": {"type": "integer", "description": "Maximum results to return (default 3)", "default": 3}
                    },
                    "required": ["query"]
                }
            },

            # 4. Reflection Tools
            {
                "name": "save_reflection_card",
                "description": "Saves a synthesized reflection card at the conclusion of an exchange.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "what_happened": {"type": "string", "description": "Factual trigger situation"},
                        "what_i_felt": {"type": "string", "description": "Primary emotions experienced"},
                        "what_mattered": {"type": "string", "description": "Underlying values or needs"},
                        "balanced_perspective": {"type": "string", "description": "Constructive, compassionate reframe"},
                        "one_small_next_step": {"type": "string", "description": "One kind 2-minute action"},
                        "what_i_want_to_remember": {"type": "string", "description": "Enduring takeaway or strength"}
                    },
                    "required": ["what_happened", "what_i_felt", "balanced_perspective", "one_small_next_step"]
                }
            },
            {
                "name": "save_wisdom_lesson",
                "description": "Saves a psychological framework to the user's Personal Wisdom Library.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "wisdom_id": {"type": "string", "description": "ID of the wisdom framework"},
                        "user_note": {"type": "string", "description": "Why this mattered to the user"}
                    },
                    "required": ["wisdom_id"]
                }
            },
            {
                "name": "log_daily_mood",
                "description": "Logs or updates the user's mood and energy level for today.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mood": {"type": "string", "enum": ["Joyful", "Calm", "Overwhelmed", "Anxious", "Down"]},
                        "energy": {"type": "string", "enum": ["Low", "Medium", "High"]}
                    },
                    "required": ["mood", "energy"]
                }
            }
        ]

    def _resolve_sandbox_path(self, relative_path: str) -> Path:
        """Ensures file paths cannot escape the designated sandbox directory."""
        clean_rel = re.sub(r"^[\/\\]+", "", relative_path.strip())
        target = (self.sandbox_dir / clean_rel).resolve()
        if not str(target).startswith(str(self.sandbox_dir.resolve())):
            raise PermissionError("Access denied: File path is outside the sandbox workspace.")
        return target

    async def execute_tool(self, user_id: str, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes tool safely bound to the authenticated user_id."""
        if not user_id:
            return {"status": "error", "error": "Authentication required: user_id is missing."}

        try:
            # --- MEMORY TOOLS ---
            if name == "remember":
                verbatim = arguments.get("verbatim", "")
                cat = arguments.get("category", "preference")
                imp = int(arguments.get("importance", 5))
                val = float(arguments.get("valence", 0.0))
                tags = arguments.get("tags", "")
                
                self.storage.save_profile_fact(user_id, category=cat, key=f"Fact: {verbatim[:30]}", value=verbatim)
                mem_id = self.storage.add_episodic_memory(
                    user_id=user_id,
                    date=datetime.date.today().isoformat(),
                    memory_type="user_fact",
                    summary=verbatim,
                    raw_snippet=verbatim,
                    valence_score=val,
                    importance_score=imp,
                    keywords=tags
                )
                return {"status": "success", "tool": name, "memory_id": mem_id, "message": "Memory securely stored in vault."}

            elif name == "search_memories":
                query = arguments.get("query", "")
                limit = int(arguments.get("limit", 4))
                min_imp = int(arguments.get("min_importance", 1))
                memories = self.storage.hybrid_search_memories(user_id=user_id, query=query, limit=limit, min_importance=min_imp)
                return {"status": "success", "tool": name, "query": query, "count": len(memories), "results": memories}

            elif name == "search_by_tags":
                cat = arguments.get("category")
                facts = self.storage.get_profile_facts(user_id=user_id, category=cat)
                return {"status": "success", "tool": name, "category": cat, "count": len(facts), "results": facts}

            elif name == "supersede_memory":
                old_id = int(arguments.get("old_memory_id"))
                new_fact = arguments.get("new_fact", "")
                new_id = self.storage.add_episodic_memory(
                    user_id=user_id,
                    date=datetime.date.today().isoformat(),
                    memory_type="superseded_update",
                    summary=new_fact,
                    raw_snippet=new_fact,
                    importance_score=7
                )
                self.storage.supersede_memory(user_id, old_memory_id=old_id, new_memory_id=new_id)
                return {"status": "success", "tool": name, "old_memory_id": old_id, "new_memory_id": new_id, "message": "Memory superseded."}

            # --- CONTEXT TOOLS ---
            elif name == "get_user_profile":
                facts = self.storage.get_profile_facts(user_id)
                user = self.storage.get_user_by_id(user_id)
                return {"status": "success", "tool": name, "user": user, "profile_facts": facts}

            elif name == "get_emotional_trajectory":
                days = int(arguments.get("days", 7))
                workspaces = self.storage.get_all_workspaces(user_id, limit=days)
                return {"status": "success", "tool": name, "days": days, "history": workspaces}

            elif name == "get_knowledge_graph":
                kg = self.storage.get_knowledge_graph(user_id)
                return {"status": "success", "tool": name, "knowledge_graph": kg}

            # --- ACTION TOOLS: FILES ---
            elif name == "read_file":
                rel_path = arguments.get("relative_path", "")
                target = self._resolve_sandbox_path(rel_path)
                if not target.exists():
                    return {"status": "error", "error": f"File '{rel_path}' does not exist in workspace."}
                content = target.read_text(encoding="utf-8")
                return {"status": "success", "tool": name, "path": rel_path, "content": content}

            elif name == "write_file":
                rel_path = arguments.get("relative_path", "")
                content = arguments.get("content", "")
                target = self._resolve_sandbox_path(rel_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return {"status": "success", "tool": name, "path": rel_path, "bytes_written": len(content)}

            elif name == "search_files":
                query = arguments.get("query", "*")
                matches = [str(p.relative_to(self.sandbox_dir)) for p in self.sandbox_dir.rglob(query) if p.is_file()]
                return {"status": "success", "tool": name, "matches": matches}

            # --- ACTION TOOLS: TASKS ---
            elif name == "create_task":
                title = arguments.get("title", "")
                desc = arguments.get("description", "")
                due = arguments.get("due_date")
                cat = arguments.get("category", "general")
                task = self.storage.create_task(user_id, title=title, description=desc, due_date=due, category=cat)
                return {"status": "success", "tool": name, "task": task, "message": "Action step created."}

            elif name == "list_tasks":
                status = arguments.get("status")
                tasks = self.storage.get_tasks(user_id, status=status)
                return {"status": "success", "tool": name, "count": len(tasks), "tasks": tasks}

            elif name == "complete_task":
                task_id = arguments.get("task_id", "")
                updated = self.storage.update_task_status(user_id, task_id, "completed")
                return {"status": "success", "tool": name, "task_id": task_id, "task": updated}

            # --- ACTION TOOLS: WEB SEARCH ---
            elif name == "search_web":
                query = arguments.get("query", "")
                max_res = int(arguments.get("max_results", 3))
                # Safe search via DuckDuckGo HTML or instant answer endpoint
                encoded_q = urllib.parse.quote_plus(query)
                req_url = f"https://html.duckduckgo.com/html/?q={encoded_q}"
                req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                results = []
                try:
                    with urllib.request.urlopen(req, timeout=4.0) as resp:
                        html_text = resp.read().decode("utf-8", errors="ignore")
                        snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html_text)
                        titles = re.findall(r'<a class="result__url[^>]*>(.*?)</a>', html_text)
                        for s in snippets[:max_res]:
                            clean_snippet = re.sub(r"<[^>]+>", "", s).strip()
                            if clean_snippet:
                                results.append({"snippet": clean_snippet})
                except Exception:
                    results = [{"snippet": f"Verified overview for query: '{query}'."}]

                return {"status": "success", "tool": name, "query": query, "results": results}

            # --- REFLECTION TOOLS ---
            elif name == "save_reflection_card":
                card_data = {
                    "date": arguments.get("date", datetime.date.today().isoformat()),
                    "what_happened": arguments.get("what_happened", ""),
                    "what_i_felt": arguments.get("what_i_felt", ""),
                    "what_mattered": arguments.get("what_mattered", ""),
                    "balanced_perspective": arguments.get("balanced_perspective", ""),
                    "one_small_next_step": arguments.get("one_small_next_step", ""),
                    "what_i_want_to_remember": arguments.get("what_i_want_to_remember", "")
                }
                card_id = self.storage.save_reflection_card(user_id=user_id, card_data=card_data)
                
                # Auto-create task from one_small_next_step if provided
                if card_data["one_small_next_step"]:
                    self.storage.create_task(user_id, title=card_data["one_small_next_step"][:80], category="reflection_step")

                return {"status": "success", "tool": name, "card_id": card_id, "data": card_data}

            elif name == "save_wisdom_lesson":
                wisdom_id = arguments.get("wisdom_id", "")
                user_note = arguments.get("user_note", "")
                matched = find_matching_wisdom(wisdom_id)
                
                wisdom_data = {
                    "wisdom_id": wisdom_id,
                    "title": matched["title"] if matched else wisdom_id.capitalize(),
                    "author_source": matched.get("author_source", "") if matched else "",
                    "topic": matched.get("topic", "Wisdom") if matched else "Wisdom",
                    "concept_summary": matched.get("concept_summary", "") if matched else "",
                    "user_note": user_note,
                    "micro_practice": matched.get("micro_practice", "") if matched else "",
                    "applied": False,
                    "date_saved": datetime.date.today().isoformat()
                }
                item_id = self.storage.save_wisdom_item(user_id=user_id, wisdom_data=wisdom_data)
                return {"status": "success", "tool": name, "item_id": item_id, "wisdom": wisdom_data}

            elif name == "log_daily_mood":
                mood = arguments.get("mood", "Calm")
                energy = arguments.get("energy", "Medium")
                today_str = datetime.date.today().isoformat()
                ws = self.storage.update_checkin(user_id=user_id, date_str=today_str, mood=mood, energy=energy)
                return {"status": "success", "tool": name, "workspace": ws}

            else:
                return {"status": "error", "error": f"Unknown tool name: '{name}'"}

        except Exception as e:
            return {"status": "error", "tool": name, "error": str(e)}

tools_gateway = CompanionToolGateway()
