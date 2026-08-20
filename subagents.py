import asyncio
import datetime
from typing import Dict, List, Any, Optional
from storage import storage
from tools_engine import tools_gateway

class SubAgentDispatcher:
    """
    Sub-Agent Orchestrator for executing asynchronous background routines
    without blocking the primary conversational interface.
    """
    def __init__(self, storage_manager=storage, tool_gateway=tools_gateway):
        self.storage = storage_manager
        self.gateway = tool_gateway
        self._active_tasks: List[asyncio.Task] = []

    def dispatch_background_consolidation(self, user_id: str):
        """Spawns background task to consolidate daily episodic memories into graph milestones."""
        task = asyncio.create_task(self._run_memory_consolidation(user_id))
        self._active_tasks.append(task)
        task.add_done_callback(lambda t: self._active_tasks.remove(t) if t in self._active_tasks else None)

    async def _run_memory_consolidation(self, user_id: str):
        """Consolidates episodic memories and strengthens knowledge graph edges."""
        try:
            memories = self.storage.get_episodic_memories(user_id, limit=20)
            if not memories:
                return

            # Cluster related entities
            for m in memories:
                summary = m.get("summary", "")
                keywords = [k.strip() for k in (m.get("keywords") or "").split(",") if k.strip()]
                for k in keywords:
                    self.storage.add_or_update_entity(user_id, name=k, category="topic")

            self.storage.log_memory_action(
                user_id=user_id,
                action="consolidated",
                memory_id=None,
                details=f"Sub-agent consolidated {len(memories)} memories into knowledge graph.",
                reason="Periodic Background Consolidation"
            )
        except Exception as e:
            print(f"[SubAgentDispatcher] Error in consolidation: {e}")

    async def run_parallel_research(self, user_id: str, topics: List[str]) -> List[Dict[str, Any]]:
        """Spawns parallel search workers to research topics simultaneously."""
        async def _fetch_topic(topic: str):
            res = await self.gateway.execute_tool(user_id=user_id, name="search_web", arguments={"query": topic, "max_results": 2})
            return {"topic": topic, "results": res.get("results", [])}

        tasks = [_fetch_topic(t) for t in topics]
        return await asyncio.gather(*tasks)

subagent_dispatcher = SubAgentDispatcher()
