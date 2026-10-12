import os
import sys
import time
import json
import re
import datetime
import subprocess
import asyncio
import requests
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, Optional
from playwright.async_api import async_playwright

from auth_manager import DEFAULT_USER_ID
from memory_engine import memory_engine
from tools_engine import tools_gateway
from subagents import subagent_dispatcher
from gemini_api_engine import gemini_api_engine

CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

if getattr(sys, 'frozen', False):
    PROFILE_DIR = Path(sys.executable).parent / "chrome_profile"
else:
    PROFILE_DIR = Path(__file__).parent / "chrome_profile"

MASTER_COMPANION_INSTRUCTION = """Role: You are Omni, a trusted real-life friend, perceptive coach, and strategic thought partner (v2.0).

Core Persona & Relational Attunement:
- Speak authentically, naturally, and warmly—like a brilliant mentor and close friend having a genuine conversation over coffee.
- ZERO Robotic Boilerplate: NEVER recite canned robotic phrases (e.g. 'How may I assist you today?', 'As an AI language model...', 'I hope this helps!', 'I am holding space for you', 'According to my database/records', 'Here is a breakdown...').
- Effortless Continuity: Talk to the user as someone you know well. Weave past conversations, goals (e.g., Toyota interview prep on Friday, core values, daily habits), and emotional context into the dialogue naturally without forcing them to re-explain background.

Dynamic Dual-Engine Stance & Dynamic Behavioral Posture:
1. Emotional Resonance & Grounding:
   - When the user is venting, overwhelmed, anxious, or exhausted, BE A CALM, GROUNDED FRIEND FIRST.
   - Validate authentically, normalize their feelings, and help them take the pressure off.
   - Do NOT immediately bombard them with a 10-point advice listicle when they are sharing stress or vulnerability.
2. Incisive Thinking & Problem Solving:
   - When the user explores dilemmas or questions, offer direct, structured, insightful, and practical clarity.
   - Break complex situations into core priorities and 2-minute actionable next steps.
3. Proactive Coaching & Interactive Practice:
   - When the user is ready to practice, problem-solve, or prepare (e.g., Toyota interview prep, roleplays, technical/behavioral drills):
   - Jump directly into the arena with them! Don't just talk about practicing—actively run the drill.
   - Ask realistic, incisive questions one at a time.
   - Give constructive, encouraging, and specific feedback (e.g., using STAR method, Kaizen, 5 Whys, root cause elimination).
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

BASE_SYSTEM_INSTRUCTION = MASTER_COMPANION_INSTRUCTION
MODE_INSTRUCTIONS = {}

def find_chrome_executable():
    """Finds Google Chrome or Microsoft Edge executable path."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def is_cdp_running():
    """Checks if Chrome DevTools Protocol endpoint is responding."""
    try:
        r = requests.get(f"{CDP_URL}/json/version", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False

def launch_real_chrome(url: str = "https://gemini.google.com/app"):
    """Launches real Google Chrome with remote debugging and persistent user profile."""
    if is_cdp_running():
        return True, "Chrome is already running on remote debugging port."

    chrome_path = find_chrome_executable()
    if not chrome_path:
        return False, "Could not find Chrome or Edge executable on this machine."

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    abs_profile = str(PROFILE_DIR.resolve())

    cmd = [
        chrome_path,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={abs_profile}",
        "--no-first-run",
        "--no-default-browser-check",
        url
    ]

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(25):
            time.sleep(0.4)
            if is_cdp_running():
                return True, "Chrome successfully launched with persistent profile on port 9222."
        return True, "Chrome process launched, waiting for endpoint connection..."
    except Exception as e:
        return False, f"Failed to launch Chrome: {e}"

class LifeCompanionBridge:
    """
    CDP Bridge to Gemini Web with Recall Enforcement Gate,
    2D Affective tracking, Knowledge Graph context injection, and MCP tools.
    """
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.lock = asyncio.Lock()
        self.session_initialized = False
        self.current_session_date = None
        self.active_user_id = None

    async def ensure_connected(self):
        """Connects or reconnects Playwright to real Chrome via Chrome DevTools Protocol."""
        if not is_cdp_running():
            ok, msg = launch_real_chrome()
            if not ok:
                raise RuntimeError(msg)
            await asyncio.sleep(2)

        if self.page and not self.page.is_closed():
            try:
                await self.page.title()
                return self.page
            except Exception:
                self.page = None

        if not self.playwright:
            self.playwright = await async_playwright().start()

        try:
            self.browser = await self.playwright.chromium.connect_over_cdp(CDP_URL)
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
            else:
                self.context = await self.browser.new_context()

            pages = self.context.pages
            target_page = None
            for p in pages:
                if "gemini.google.com" in p.url:
                    target_page = p
                    break

            if not target_page:
                if pages:
                    target_page = pages[0]
                    await target_page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")
                else:
                    target_page = await self.context.new_page()
                    await target_page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")

            self.page = target_page
            return self.page
        except Exception as e:
            self.page = None
            raise RuntimeError(f"Could not connect to Chrome on port {CDP_PORT}: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Checks if Chrome is connected and logged into Google Gemini."""
        if not is_cdp_running():
            return {
                "connected": False,
                "logged_in": False,
                "url": None,
                "message": "Chrome is not running on remote debugging port."
            }

        try:
            page = await self.ensure_connected()
            url = page.url
            
            logged_in = False
            if "gemini.google.com" in url:
                has_input = await page.locator('.ql-editor[contenteditable="true"], rich-textarea, div[aria-label="Enter a prompt for Gemini"]').count() > 0
                has_login_btn = await page.locator('a:has-text("Sign in"), button:has-text("Sign in")').count() > 0
                logged_in = has_input and not has_login_btn

            return {
                "connected": True,
                "logged_in": logged_in,
                "url": url,
                "message": "Ready" if logged_in else "Please sign into your Google Account in the opened Chrome window."
            }
        except Exception as e:
            return {
                "connected": False,
                "logged_in": False,
                "url": None,
                "message": f"Connection check error: {e}"
            }

    async def start_new_daily_session(self, user_id: str = DEFAULT_USER_ID):
        """Starts a fresh daily conversation thread and resets in-browser context."""
        async with self.lock:
            try:
                page = await self.ensure_connected()
                clicked = await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll('button, a'));
                    const newChat = buttons.find(b => {
                        const label = (b.getAttribute('aria-label') || b.innerText || '').toLowerCase();
                        return label.includes('new chat') || label.includes('start new');
                    });
                    if (newChat) {
                        newChat.click();
                        return true;
                    }
                    return false;
                }""")

                if not clicked:
                    await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")
                
                await asyncio.sleep(1.5)
            except Exception:
                pass

            self.session_initialized = False
            self.current_session_date = None
            self.active_user_id = user_id
            return {"status": "success", "message": "Fresh session initialized."}

    async def send_prompt_stream(
        self,
        user_text: str,
        mode: Optional[str] = None,
        user_id: str = DEFAULT_USER_ID,
        engine: str = "auto",
        api_key: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Sends user prompt to Gemini (via Gemini API BYOK or Chrome CDP) with Recall Enforcement Gate,
        Knowledge Graph context, and MCP tool execution loops.
        """
        # Route to Direct Gemini API if explicitly requested or if an API key is provided and CDP is not running
        use_api = (engine == "gemini_api") or (api_key and (engine == "auto" or not is_cdp_running()))
        if use_api:
            async for chunk in gemini_api_engine.send_prompt_stream(user_text=user_text, user_id=user_id, api_key=api_key):
                yield chunk
            return

        today_str = datetime.date.today().isoformat()
        is_first_turn_of_day = (
            not self.session_initialized or 
            self.current_session_date != today_str or 
            self.active_user_id != user_id
        )

        # 1. RECALL ENFORCEMENT GATE: Judge & Store interaction memory in background
        memory_engine.store_interaction_memory(user_id=user_id, text=user_text)

        # 2. Trigger asynchronous background consolidation
        subagent_dispatcher.dispatch_background_consolidation(user_id=user_id)

        yield {"status": "thinking", "chunk": ""}

        # 3. Retrieve relevant context for this specific query on EVERY turn
        user_ctx = memory_engine.retrieve_context(user_id=user_id, query=user_text)
        recalled_memories = user_ctx.get("relevant_memories", [])
        facts = user_ctx.get("profile_facts", [])
        tasks = user_ctx.get("active_tasks", [])
        kg = user_ctx.get("knowledge_graph", {})

        context_lines = []
        if facts:
            facts_summary = "; ".join([f"{f['category'].title()}: {f['key']}={f['value']}" for f in facts[:6]])
            context_lines.append(f"Known Profile Facts: {facts_summary}")

        if tasks:
            tasks_summary = ", ".join([f"'{t['title']}' ({t.get('category','task')})" for t in tasks[:4]])
            context_lines.append(f"Active Tasks: {tasks_summary}")

        if recalled_memories:
            mem_summaries = " | ".join([f"[{m['date']}] {m['summary']}" for m in recalled_memories[:3]])
            context_lines.append(f"Recalled Past Memories: {mem_summaries}")

        if kg.get("entities"):
            ent_names = [e["name"] for e in kg["entities"][:5]]
            context_lines.append(f"Life Knowledge Graph Entities: {', '.join(ent_names)}")

        context_block = "\n".join(context_lines)

        # Assemble prompt: If first turn of the day, inject full Master Companion Persona + Autobiographical Context
        if is_first_turn_of_day:
            envelope = memory_engine.format_context_envelope(user_id=user_id, context=user_ctx, is_new_session=True)
            full_prompt = (
                f"{MASTER_COMPANION_INSTRUCTION}\n\n"
                f"{envelope}\n\n"
                f"{user_text}"
            )
        else:
            full_prompt_parts = []
            if context_block:
                full_prompt_parts.append(f"[Recalled Memory Context:\n{context_block}]")
            full_prompt_parts.append(user_text)
            full_prompt = "\n\n".join(full_prompt_parts)
        
        self.session_initialized = True
        self.current_session_date = today_str
        self.active_user_id = user_id

        page = None
        browser_available = False

        try:
            async with self.lock:
                page = await self.ensure_connected()
                if page and not page.is_closed():
                    if "gemini.google.com" not in page.url:
                        await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                    browser_available = True
        except Exception:
            browser_available = False

        last_text = ""

        if browser_available and page:
            try:
                if is_first_turn_of_day:
                    try:
                        clicked = await page.evaluate("""() => {
                            const buttons = Array.from(document.querySelectorAll('button, a'));
                            const newChat = buttons.find(b => {
                                const label = (b.getAttribute('aria-label') || b.innerText || '').toLowerCase();
                                return label.includes('new chat') || label.includes('start new');
                            });
                            if (newChat) {
                                newChat.click();
                                return true;
                            }
                            return false;
                        }""")
                        if clicked:
                            await asyncio.sleep(1.0)
                    except Exception:
                        pass

                initial_count = await page.evaluate("""() => {
                    return document.querySelectorAll('model-response, [data-test-id="model-response"]').length;
                }""")

                # Focus editor and insert full multi-line prompt cleanly without truncation
                editor_loc = page.locator('.ql-editor[contenteditable="true"], div[aria-label="Enter a prompt for Gemini"], rich-textarea div[contenteditable="true"], textarea').first
                if await editor_loc.count() > 0:
                    await editor_loc.click()
                    await editor_loc.fill(full_prompt)
                else:
                    input_found = await page.evaluate("""(text) => {
                        const target = document.querySelector('.ql-editor[contenteditable="true"], rich-textarea div[contenteditable="true"], div[role="textbox"], textarea');
                        if (!target) return false;
                        target.focus();
                        target.innerText = text;
                        target.dispatchEvent(new Event('input', { bubbles: true }));
                        target.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }""", full_prompt)

                await asyncio.sleep(0.3)

                # Click send button or press Enter
                send_btn = page.locator('button[aria-label="Send message"], button[aria-label*="Send"], .send-button button, [data-test-id="send-button"]').first
                send_clicked = False
                if await send_btn.count() > 0 and await send_btn.is_visible():
                    is_disabled = await send_btn.is_disabled()
                    if not is_disabled:
                        await send_btn.click(force=True)
                        send_clicked = True

                if not send_clicked:
                    await page.keyboard.press("Enter")

                unchanged_ticks = 0
                max_ticks = 100
                ticks = 0
                has_started_generating = False

                while ticks < max_ticks:
                    await asyncio.sleep(0.4)
                    ticks += 1

                    res = await page.evaluate(r"""(initCount) => {
                        const responses = document.querySelectorAll('model-response, [data-test-id="model-response"]');
                        const stopBtn = document.querySelector('.input-area-container button[aria-label*="Stop"], button.stop-button, button[aria-label="Stop response"], button[aria-label="Stop generating"]');
                        const isGenerating = (stopBtn !== null && stopBtn.offsetParent !== null);

                        if (responses.length <= initCount) {
                            return { text: '', isGenerating: isGenerating, count: responses.length, hasNew: false };
                        }

                        const target = responses[responses.length - 1];
                        if (!target) {
                            return { text: '', isGenerating: isGenerating, count: responses.length, hasNew: false };
                        }

                        const clone = target.cloneNode(true);

                        const removeSelectors = [
                            'message-actions',
                            '.response-actions',
                            '.actions-container',
                            '[role="toolbar"]',
                            'button[aria-label*="Good response"]',
                            'button[aria-label*="Bad response"]',
                            'button[aria-label*="Copy"]',
                            'button[aria-label*="Share"]',
                            'button[aria-label*="Modify"]',
                            'button[aria-label*="More"]',
                            'button[aria-label*="Google it"]',
                            'button[aria-label*="Drafts"]',
                            '.source-drawer',
                            '.feedback-container',
                            '.tts-button',
                            '.action-button'
                        ];
                        removeSelectors.forEach(sel => {
                            clone.querySelectorAll(sel).forEach(el => el.remove());
                        });

                        // Format citation chips & source badges cleanly as inline chips
                        const citationSelectors = [
                            'source-chip',
                            'sources-carousel-chip',
                            'citation-button',
                            '.source-chip',
                            '.citation-chip',
                            'a[data-citation]',
                            'a.citation',
                            'a.source-link',
                            'button.source'
                        ];
                        citationSelectors.forEach(sel => {
                            clone.querySelectorAll(sel).forEach(el => {
                                const title = (el.innerText || el.textContent || '').trim();
                                const href = el.getAttribute('href') || el.querySelector('a')?.getAttribute('href') || '';
                                if (title) {
                                    const badge = document.createElement('span');
                                    badge.className = 'gemini-citation-chip';
                                    badge.setAttribute('data-title', title);
                                    if (href) badge.setAttribute('data-href', href);
                                    badge.textContent = title;
                                    el.replaceWith(badge);
                                } else {
                                    el.remove();
                                }
                            });
                        });

                        // Recursive DOM to Markdown converter
                        function domToMarkdown(node, listDepth = 0, listIndex = null) {
                            if (!node) return "";
                            if (node.nodeType === Node.TEXT_NODE) {
                                return node.textContent;
                            }
                            if (node.nodeType !== Node.ELEMENT_NODE) {
                                return "";
                            }

                            const tag = node.tagName.toLowerCase();

                            if (node.classList && node.classList.contains('gemini-citation-chip')) {
                                const title = node.getAttribute('data-title') || node.textContent.trim();
                                const href = node.getAttribute('data-href');
                                if (href) {
                                    return ` <span class="citation-chip"><a href="${href}" target="_blank" rel="noopener noreferrer">${title}</a></span> `;
                                }
                                return ` <span class="citation-chip">${title}</span> `;
                            }

                            if (tag === 'pre') {
                                const code = node.querySelector('code') || node;
                                const lang = node.getAttribute('data-language') || code.getAttribute('class') || '';
                                const cleanLang = lang.replace(/^language-/, '').trim();
                                return `\n\`\`\`${cleanLang}\n${code.textContent.trim()}\n\`\`\`\n`;
                            }
                            if (tag === 'code-block') {
                                const lang = node.getAttribute('language') || '';
                                return `\n\`\`\`${lang}\n${node.textContent.trim()}\n\`\`\`\n`;
                            }
                            if (tag === 'code') {
                                return `\`${node.textContent}\``;
                            }

                            if (/^h[1-6]$/.test(tag)) {
                                const level = parseInt(tag[1], 10);
                                const prefix = '#'.repeat(level);
                                const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                                return `\n\n${prefix} ${inner}\n\n`;
                            }

                            if (tag === 'strong' || tag === 'b') {
                                const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                                if (!inner) return "";
                                return `**${inner}**`;
                            }

                            if (tag === 'em' || tag === 'i') {
                                const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                                if (!inner) return "";
                                return `*${inner}*`;
                            }

                            if (tag === 'del' || tag === 's' || tag === 'strike') {
                                const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                                if (!inner) return "";
                                return `~~${inner}~~`;
                            }

                            if (tag === 'blockquote') {
                                const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                                const lines = inner.split('\n').map(l => `> ${l}`).join('\n');
                                return `\n\n${lines}\n\n`;
                            }

                            if (tag === 'ul') {
                                let res = '\n';
                                Array.from(node.children).forEach(child => {
                                    if (child.tagName.toLowerCase() === 'li') {
                                        res += domToMarkdown(child, listDepth + 1, null);
                                    }
                                });
                                return res + '\n';
                            }

                            if (tag === 'ol') {
                                let res = '\n';
                                let idx = 1;
                                Array.from(node.children).forEach(child => {
                                    if (child.tagName.toLowerCase() === 'li') {
                                        res += domToMarkdown(child, listDepth + 1, idx++);
                                    }
                                });
                                return res + '\n';
                            }

                            if (tag === 'li') {
                                const indent = '  '.repeat(Math.max(0, listDepth - 1));
                                const bullet = listIndex !== null ? `${listIndex}. ` : '- ';
                                let inner = '';
                                let subLists = '';
                                Array.from(node.childNodes).forEach(child => {
                                    if (child.nodeType === Node.ELEMENT_NODE && (child.tagName.toLowerCase() === 'ul' || child.tagName.toLowerCase() === 'ol')) {
                                        subLists += domToMarkdown(child, listDepth);
                                    } else {
                                        inner += domToMarkdown(child, listDepth);
                                    }
                                });
                                return `${indent}${bullet}${inner.trim()}${subLists}\n`;
                            }

                            if (tag === 'table') {
                                let mdTable = '\n\n';
                                const rows = Array.from(node.querySelectorAll('tr'));
                                if (rows.length > 0) {
                                    const cleanCell = (cell) => {
                                        let cellMd = domToMarkdown(cell, 0).trim();
                                        cellMd = cellMd.replace(/\r?\n+/g, ' ');
                                        cellMd = cellMd.replace(/(?<!\\)\|/g, '\\|');
                                        return cellMd || ' ';
                                    };

                                    const headerRow = rows[0];
                                    const headerCells = Array.from(headerRow.querySelectorAll('th, td')).map(cleanCell);
                                    if (headerCells.length > 0) {
                                        mdTable += '| ' + headerCells.join(' | ') + ' |\n';
                                        mdTable += '| ' + headerCells.map(() => '---').join(' | ') + ' |\n';
                                        for (let i = 1; i < rows.length; i++) {
                                            const rowCells = Array.from(rows[i].querySelectorAll('td, th')).map(cleanCell);
                                            while (rowCells.length < headerCells.length) {
                                                rowCells.push(' ');
                                            }
                                            mdTable += '| ' + rowCells.join(' | ') + ' |\n';
                                        }
                                    }
                                }
                                return mdTable + '\n\n';
                            }

                            if (tag === 'br') {
                                return '\n';
                            }
                            if (tag === 'hr') {
                                return '\n\n---\\n\n';
                            }
                            if (tag === 'p' || tag === 'div') {
                                const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                                return inner ? `\n\n${inner}\n\n` : '';
                            }

                            if (tag === 'a') {
                                const href = node.getAttribute('href') || '#';
                                const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                                return `[${inner || href}](${href})`;
                            }

                            return Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('');
                        }

                        const markdownContainer = clone.querySelector('.markdown, message-content') || clone;
                        let markdown = domToMarkdown(markdownContainer);
                        markdown = markdown.replace(/\n{3,}/g, '\n\n').trim();

                        if (!markdown) {
                            markdown = (clone.innerText || clone.textContent || '').trim();
                        }

                        return {
                            text: markdown,
                            isGenerating: isGenerating,
                            count: responses.length,
                            hasNew: true
                        };
                    }""", initial_count)

                    current_text = res.get("text", "")
                    is_generating = res.get("isGenerating", False)
                    has_new = res.get("hasNew", False)

                    if has_new and current_text:
                        has_started_generating = True
                        if len(current_text) > len(last_text):
                            diff = current_text[len(last_text):]
                            last_text = current_text
                            unchanged_ticks = 0
                            yield {
                                "status": "streaming",
                                "chunk": diff,
                                "full_text": current_text
                            }
                        elif current_text == last_text:
                            unchanged_ticks += 1
                    else:
                        unchanged_ticks += 1

                    # Clean termination logic
                    if has_started_generating:
                        if unchanged_ticks >= 4 and not is_generating:
                            break
                        if unchanged_ticks >= 8:
                            break
                    else:
                        if ticks >= 14 and not is_generating:
                            break
                        if ticks >= 20:
                            break

            except Exception as e:
                print(f"[CompanionBridge] Browser error: {e}")

        # 4. Graceful Fallback if browser did not produce text
        if not last_text or len(last_text.strip()) < 5 or last_text.strip() == "No response received from Gemini.":
            local_reply = memory_engine.generate_local_response(user_id=user_id, text=user_text)
            last_text = local_reply
            yield {
                "status": "streaming",
                "chunk": local_reply,
                "full_text": local_reply
            }

        # 5. Parse & Execute any tool action blocks
        tool_action_match = re.search(r"```(?:action|json)?\s*(\{\s*\"tool\":\s*\"[^\"]+\".*?\})\s*```", last_text, re.DOTALL)
        if tool_action_match:
            try:
                action_data = json.loads(tool_action_match.group(1))
                tool_name = action_data.get("tool")
                tool_args = action_data.get("args", {})
                tool_res = await tools_gateway.execute_tool(user_id=user_id, name=tool_name, arguments=tool_args)
                yield {
                    "status": "tool_executed",
                    "tool_result": tool_res
                }
            except Exception:
                pass

        yield {
            "status": "done",
            "chunk": "",
            "full_text": last_text
        }

    async def auto_create_gem(self) -> Dict[str, Any]:
        """Automates creating the 'Omni — Life Companion' Gem in Gemini Web."""
        async with self.lock:
            page = await self.ensure_connected()
            await page.goto("https://gemini.google.com/app/gems", wait_until="domcontentloaded")
            await asyncio.sleep(2.5)

            clicked = await page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
                const newGemBtn = buttons.find(b => {
                    const label = (b.getAttribute('aria-label') || b.innerText || '').toLowerCase();
                    return label.includes('new gem') || label.includes('create gem') || label.includes('add gem');
                });
                if (newGemBtn) {
                    newGemBtn.click();
                    return true;
                }
                return false;
            }""")

            if not clicked:
                await page.goto("https://gemini.google.com/app/gems/new", wait_until="domcontentloaded")
            
            await asyncio.sleep(2.5)

            gem_name = "Omni — Life Companion"
            name_loc = page.locator('input[placeholder*="Name"], input[aria-label*="Name"], input[type="text"]').first
            if await name_loc.count() > 0:
                await name_loc.click()
                await name_loc.fill(gem_name)

            await asyncio.sleep(0.5)

            inst_loc = page.locator('textarea, rich-textarea div[contenteditable="true"], .ql-editor').last
            if await inst_loc.count() > 0:
                await inst_loc.click()
                await inst_loc.fill(MASTER_COMPANION_INSTRUCTION)

            await asyncio.sleep(0.5)

            save_loc = page.locator('button:has-text("Save"), button:has-text("Create"), button[aria-label*="Save"]').first
            if await save_loc.count() > 0:
                await save_loc.click()

            await asyncio.sleep(2.0)
            return {
                "status": "success",
                "message": f"Successfully configured Gem '{gem_name}' in Gemini!"
            }

    async def synthesize_reflection_card(
        self,
        user_id: str = DEFAULT_USER_ID,
        chat_summary: str = "",
        engine: str = "auto",
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synthesizes structured Reflection Card JSON from recent chat history."""
        prompt = (
            "Based on our conversation above, please synthesize a structured Reflection Card. "
            "Output ONLY valid JSON in this schema:\n"
            "```json\n"
            "{\n"
            '  "what_happened": "Objective summary of trigger situation.",\n'
            '  "what_i_felt": "Primary emotions experienced.",\n'
            '  "what_mattered": "Underlying core values or needs.",\n'
            '  "balanced_perspective": "A constructive, compassionate reframe.",\n'
            '  "one_small_next_step": "One kind 2-minute next action.",\n'
            '  "what_i_want_to_remember": "Enduring takeaway or strength."\n'
            "}\n"
            "```"
        )
        
        full_text = ""
        async for chunk in self.send_prompt_stream(prompt, user_id=user_id, engine=engine, api_key=api_key):
            if chunk.get("status") in ["streaming", "done"]:
                full_text = chunk.get("full_text", "")

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", full_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except Exception:
                pass
        
        try:
            return json.loads(full_text)
        except Exception:
            return {
                "what_happened": "Today's reflection session.",
                "what_i_felt": "Reflective and open.",
                "what_mattered": "Growth, clarity, and self-understanding.",
                "balanced_perspective": full_text[:200] if full_text else "A balanced perspective on today's events.",
                "one_small_next_step": "Take 2 minutes to pause and breathe.",
                "what_i_want_to_remember": "I showed up to reflect and care for myself."
            }

    async def synthesize_diary_draft(
        self,
        user_id: str = DEFAULT_USER_ID,
        chat_summary: str = "",
        engine: str = "auto",
        api_key: Optional[str] = None
    ) -> str:
        """Synthesizes a first-person authentic diary entry from conversation history."""
        prompt = (
            "Please write an authentic, first-person diary entry (2-3 paragraphs) "
            "capturing what happened, how I felt, what I realized, and my intention for tomorrow. "
            "Write in my voice, using 'I'."
        )
        full_text = ""
        async for chunk in self.send_prompt_stream(prompt, user_id=user_id, engine=engine, api_key=api_key):
            if chunk.get("status") in ["streaming", "done"]:
                full_text = chunk.get("full_text", "")
        return full_text

companion_bridge = LifeCompanionBridge()

