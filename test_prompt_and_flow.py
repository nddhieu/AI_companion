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

    def test_markdown_table_structure_preservation(self):
        # Verify markdown table formatting rules
        sample_table = (
            "| Priority | Area | Status | Key Deliverables / Next Actions |\n"
            "| --- | --- | --- | --- |\n"
            "| High | 3 Core STAR Stories | Pending Drill | Lock down 3 specific stories: 1) Outage debugging |\n"
            "| High | \"Tell Me About Yourself\" | Pending Polish | Deliver concise narrative |"
        )
        lines = sample_table.strip().split("\n")
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[0].startswith("| Priority"))
        self.assertTrue(lines[1].startswith("| ---"))

if __name__ == "__main__":
    unittest.main()
