import asyncio
import unittest
from gemini_api_engine import gemini_api_engine
from companion_bridge import companion_bridge

class TestGeminiApiEngine(unittest.IsolatedAsyncioTestCase):
    async def test_engine_resolution_and_validation(self):
        # Empty key validation
        res = await gemini_api_engine.validate_api_key("")
        self.assertFalse(res["valid"])

        # Invalid key validation against Google API
        res_invalid = await gemini_api_engine.validate_api_key("INVALID_KEY_12345")
        self.assertFalse(res_invalid["valid"])
        self.assertIn("Invalid API key", res_invalid["message"])

    async def test_missing_key_stream_error(self):
        chunks = []
        async for chunk in gemini_api_engine.send_prompt_stream("Hello", api_key="", user_id="test_user"):
            chunks.append(chunk)
        
        self.assertTrue(any(c.get("status") == "error" for c in chunks))

    async def test_companion_bridge_routing_to_api(self):
        chunks = []
        async for chunk in companion_bridge.send_prompt_stream("Hello", engine="gemini_api", api_key="", user_id="test_user"):
            chunks.append(chunk)
        
        self.assertTrue(any(c.get("status") == "error" for c in chunks))

if __name__ == "__main__":
    unittest.main()
