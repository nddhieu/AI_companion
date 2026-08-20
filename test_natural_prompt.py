import asyncio
from companion_bridge import companion_bridge

async def main():
    page = await companion_bridge.ensure_connected()
    
    prompt = """[Context from memory: The user is preparing for a Toyota Engineering Leadership interview on Friday. Key areas discussed and practiced: Toyota Production System (TPS / Kaizen / 5 Whys), STAR method for behavioral questions, and handling production line trade-offs.]

i want to practice for the interview with toyota on Friday, can you recall what we need to do, and what we have practice"""

    editor_loc = page.locator('.ql-editor[contenteditable="true"]').first
    await editor_loc.click()
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    
    await page.evaluate("""(text) => {
        const target = document.querySelector('.ql-editor[contenteditable="true"]');
        target.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);
        document.execCommand('insertText', false, text);
        target.dispatchEvent(new Event('input', { bubbles: true }));
        target.dispatchEvent(new Event('change', { bubbles: true }));
    }""", prompt)
    
    await asyncio.sleep(0.5)
    await page.keyboard.press("Enter")
    
    print("Prompt sent! Waiting for Gemini response...")
    await asyncio.sleep(6.0)
    
    text = await page.evaluate("""() => {
        const responses = document.querySelectorAll('model-response');
        if (responses.length === 0) return 'None';
        return responses[responses.length - 1].innerText;
    }""")
    print("\n=== GEMINI RESPONSE ===\n")
    print(text)

if __name__ == "__main__":
    asyncio.run(main())
