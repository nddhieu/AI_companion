import unittest
import asyncio
from companion_bridge import MASTER_COMPANION_INSTRUCTION, companion_bridge
from memory_engine import memory_engine

class TestMasterPromptAndFlow(unittest.TestCase):
    def test_master_instruction_no_robotic_boilerplate(self):
        self.assertIn("ZERO Robotic Boilerplate", MASTER_COMPANION_INSTRUCTION)
        self.assertIn("Emotional Resonance & Grounding", MASTER_COMPANION_INSTRUCTION)
        self.assertIn("Incisive Thinking & Problem Solving", MASTER_COMPANION_INSTRUCTION)
        self.assertIn("Proactive Coaching & Interactive Practice", MASTER_COMPANION_INSTRUCTION)
        self.assertIn("Wisdom & Mental Models", MASTER_COMPANION_INSTRUCTION)
        self.assertIn("Authentic Synthesis & Journaling", MASTER_COMPANION_INSTRUCTION)
        self.assertIn("Seamless Memory & Context Integration", MASTER_COMPANION_INSTRUCTION)

    def test_dynamic_intent_scenarios(self):
        # Scenario 1: User is overwhelmed / venting
        res1 = memory_engine.generate_local_response("default_user", "I'm having a super stressful day and feel totally burned out.")
        self.assertTrue("hear you" in res1.lower() or "breath" in res1.lower())
        self.assertNotIn("HOLDING SPACE", res1.upper())

        # Scenario 2: User wants to practice interview
        res2 = memory_engine.generate_local_response("default_user", "Let's practice behavioral questions for my upcoming interview.")
        self.assertTrue("practice" in res2.lower() or "action plan" in res2.lower())

        # Scenario 3: User asks for a diary synthesis
        res3 = memory_engine.generate_local_response("default_user", "Write my diary entry for today's session.")
        self.assertIn("Journal Entry", res3)
        self.assertIn("Today I took time", res3)

        # Scenario 4: User asks for coaching / prioritization
        res4 = memory_engine.generate_local_response("default_user", "Coach me on how to organize these three tasks.")
        self.assertIn("Core Priority", res4)

    def test_yesterday_diary_synthesis(self):
        # User asks: "base on what you know , write a diary how was my day yesterday"
        res = memory_engine.generate_local_response("default_user", "base on what you know , write a diary how was my day yesterday")
        self.assertIn("Daily Journal Entry", res)
        self.assertTrue("Toyota" in res or "interview" in res)
        self.assertTrue("calm" in res.lower() or "medium" in res.lower() or "today i took time" in res.lower())
        self.assertNotIn("I'm with you. Tell me what's on your mind today—whether you want to run through practice", res)

    def test_identity_and_yesterday_recap(self):
        # Identity query
        res_id = memory_engine.generate_local_response("default_user", "what do you know about me")
        self.assertIn("Hieu Nguyen", res_id)
        self.assertIn("Technical Lead", res_id)
        self.assertIn("Toyota", res_id)

        # Yesterday recap
        res_recap = memory_engine.generate_local_response("default_user", "what did we do yesterday")
        self.assertIn("Toyota Production System", res_recap)
        self.assertIn("STAR Behavioral Stories", res_recap)

if __name__ == "__main__":
    unittest.main()

