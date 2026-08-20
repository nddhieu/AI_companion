import unittest
import asyncio
import os
import shutil
import tempfile
from pathlib import Path

from storage import StorageManager, compute_text_embedding, cosine_similarity
from safety_engine import SafetyEngine
from memory_engine import MemoryEngine
from tools_engine import CompanionToolGateway
from mcp_server import MCPServer

class TestV2Features(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_companion.db"
        self.sandbox_dir = Path(self.test_dir) / "sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        self.storage = StorageManager(db_path=self.db_path)
        self.safety = SafetyEngine()
        self.memory = MemoryEngine(storage_manager=self.storage, safety_mgr=self.safety)
        self.gateway = CompanionToolGateway(storage_manager=self.storage, sandbox_dir=self.sandbox_dir)
        self.mcp = MCPServer(tool_gateway=self.gateway, storage_manager=self.storage)
        self.user_id = "test_user_001"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_embeddings_and_cosine_similarity(self):
        vec1 = compute_text_embedding("Marcus is my engineering manager at work")
        vec2 = compute_text_embedding("Marcus engineering manager")
        vec3 = compute_text_embedding("Apple banana pineapple fruit")
        
        sim_high = cosine_similarity(vec1, vec2)
        sim_low = cosine_similarity(vec1, vec3)
        
        self.assertGreater(sim_high, sim_low)
        self.assertGreater(sim_high, 0.4)

    def test_knowledge_graph_entities_and_relations(self):
        ent = self.storage.add_or_update_entity(self.user_id, name="Marcus", category="person", emotional_weight=0.5)
        self.assertEqual(ent["name"], "Marcus")
        self.assertEqual(ent["category"], "person")

        rel = self.storage.add_relation(self.user_id, source_name="Marcus", target_name="User", relation_type="MANAGES")
        self.assertEqual(rel["relation_type"], "MANAGES")

        kg = self.storage.get_knowledge_graph(self.user_id)
        self.assertTrue(len(kg["entities"]) >= 2)
        self.assertTrue(len(kg["relations"]) >= 1)

    def test_tasks_crud(self):
        task = self.storage.create_task(self.user_id, title="Take 3 deep breaths", category="wellness")
        self.assertEqual(task["title"], "Take 3 deep breaths")
        self.assertEqual(task["status"], "pending")

        updated = self.storage.update_task_status(self.user_id, task["id"], "completed")
        self.assertEqual(updated["status"], "completed")

        tasks = self.storage.get_tasks(self.user_id)
        self.assertEqual(len(tasks), 1)

        deleted = self.storage.delete_task(self.user_id, task["id"])
        self.assertTrue(deleted)
        self.assertEqual(len(self.storage.get_tasks(self.user_id)), 0)

    def test_judge_store_recall_pipeline(self):
        text = "I am feeling really anxious about my review with my manager Marcus tomorrow."
        judge_res = self.memory.judge_interaction(self.user_id, text)
        
        self.assertTrue(judge_res["worth_remembering"])
        self.assertGreaterEqual(judge_res["importance"], 5)
        self.assertLess(judge_res["valence"], 0.0) # Negative valence
        self.assertTrue(any(e["name"] == "Marcus" for e in judge_res["entities"]))

        mem_id = self.memory.store_interaction_memory(self.user_id, text)
        self.assertIsNotNone(mem_id)

        recalled = self.memory.recall_memories(self.user_id, query="Marcus review")
        self.assertTrue(len(recalled) >= 1)
        self.assertIn("Marcus", recalled[0]["summary"])

    def test_constitutional_verifier_trauma_suppression(self):
        # Store a sensitive trauma memory
        sensitive_mem_id = self.storage.add_episodic_memory(
            user_id=self.user_id,
            date="2026-08-01",
            memory_type="reflection",
            summary="Grieving the loss of my father after his funeral.",
            is_sensitive=True
        )

        # Casual prompt should suppress the sensitive memory
        casual_prompt = "What tasks should I focus on for work today?"
        recalled_casual = self.memory.recall_memories(self.user_id, query=casual_prompt)
        self.assertFalse(any(m["id"] == sensitive_mem_id for m in recalled_casual))

        # Explicit invitation prompt should permit the memory
        invite_prompt = "I want to talk about my grief and healing from my loss."
        recalled_invited = self.memory.recall_memories(self.user_id, query=invite_prompt)
        self.assertTrue(any(m["id"] == sensitive_mem_id for m in recalled_invited))

    def test_cryptographic_forget_me_purge(self):
        self.storage.save_profile_fact(self.user_id, category="person", key="Dave", value="Old teammate")
        self.storage.add_episodic_memory(self.user_id, date="2026-08-10", memory_type="reflection", summary="Had coffee with Dave")
        
        purge_res = self.storage.purge_memories_forget_me(self.user_id, target_term="Dave")
        self.assertEqual(purge_res["status"], "success")
        self.assertGreaterEqual(purge_res["deleted_facts"], 1)
        self.assertGreaterEqual(purge_res["deleted_memories"], 1)
        self.assertTrue(len(purge_res["tombstone_signature"]) == 64) # SHA256 hex length

        facts = self.storage.get_profile_facts(self.user_id)
        self.assertFalse(any("Dave" in f["key"] for f in facts))

    def test_mcp_json_rpc_server(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 1. tools/list
        req_list = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        res_list = loop.run_until_complete(self.mcp.handle_json_rpc(req_list, self.user_id))
        tools = res_list["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("remember", tool_names)
        self.assertIn("create_task", tool_names)
        self.assertIn("read_file", tool_names)

        # 2. tools/call create_task
        req_call = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "create_task",
                "arguments": {"title": "Write 1 paragraph", "category": "reflection"}
            }
        }
        loop.close()

    def test_adaptive_local_generation_intents(self):
        # 1. Interview Prep Intent
        reply_interview = self.memory.generate_local_response(self.user_id, "I want to practice for my Toyota interview on Friday")
        self.assertIn("Toyota", reply_interview)
        self.assertTrue("Kaizen" in reply_interview or "practice" in reply_interview.lower())

        # 2. Emotional Venting Intent
        reply_venting = self.memory.generate_local_response(self.user_id, "I am feeling totally overwhelmed and exhausted today")
        self.assertIn("hear you", reply_venting)
        self.assertIn("breath", reply_venting)

        # 3. Diary / Journaling Intent
        reply_diary = self.memory.generate_local_response(self.user_id, "Write my diary for today")
        self.assertIn("Journal Entry", reply_diary)

        # 4. Coaching Intent
        reply_coaching = self.memory.generate_local_response(self.user_id, "Coach me on how to prioritize my workload")
        self.assertIn("Core Priority", reply_coaching)
        self.assertIn("Next Step", reply_coaching)

        # 5. Wisdom Framework Intent
        reply_wisdom = self.memory.generate_local_response(self.user_id, "What mental model or framework can help me handle stress?")
        self.assertIn("Circle of Control", reply_wisdom)

    def test_master_companion_instruction_integrity(self):
        from companion_bridge import MASTER_COMPANION_INSTRUCTION
        self.assertTrue("Omni" in MASTER_COMPANION_INSTRUCTION)
        self.assertTrue("ZERO Robotic Boilerplate" in MASTER_COMPANION_INSTRUCTION)
        self.assertTrue("Dynamic Behavioral Posture" in MASTER_COMPANION_INSTRUCTION)
        self.assertTrue("Action & Tool Execution" in MASTER_COMPANION_INSTRUCTION)

    def test_memory_deduplication_on_store_and_recall(self):
        # Store same interaction 3 times
        text = "I want to practice for the interview with Toyota on Friday"
        id1 = self.memory.store_interaction_memory(self.user_id, text)
        id2 = self.memory.store_interaction_memory(self.user_id, text)
        id3 = self.memory.store_interaction_memory(self.user_id, text)

        # IDs should be merged into the existing memory
        self.assertEqual(id1, id2)
        self.assertEqual(id1, id3)

        # Recall should return only 1 deduplicated memory
        recalled = self.memory.recall_memories(self.user_id, query="Toyota interview")
        self.assertEqual(len(recalled), 1)
        self.assertIn("toyota", recalled[0]["summary"].lower())

    def test_salutation_name_resolution(self):
        from memory_engine import resolve_salutation_name
        self.assertEqual(resolve_salutation_name("My Space"), "Friend")
        self.assertEqual(resolve_salutation_name("default"), "Friend")
        self.assertEqual(resolve_salutation_name(None), "Friend")
        self.assertEqual(resolve_salutation_name("Alex"), "Alex")

        # Verify generate_local_response doesn't address as "My Space"
        reply = self.memory.generate_local_response(self.user_id, "I want to practice Toyota interview")
        self.assertNotIn("My Space", reply)

    def test_generate_personalized_greeting(self):
        greeting = self.memory.generate_personalized_greeting(self.user_id)
        self.assertIn("greeting_markdown", greeting)
        self.assertIn("starters", greeting)
        self.assertTrue(len(greeting["starters"]) > 0)
        self.assertNotIn("My Space", greeting["greeting_markdown"])
        self.assertTrue("Good to see you back" in greeting["greeting_markdown"] or "Welcome" in greeting["greeting_markdown"])

if __name__ == "__main__":
    unittest.main()
