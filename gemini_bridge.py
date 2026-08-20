import os
import sys
import time
import subprocess
import asyncio
import requests
from pathlib import Path
from playwright.async_api import async_playwright

CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
PROFILE_DIR = Path(__file__).parent / "chrome_profile"

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
        subprocess.Popen(cmd, shell=False)
        # Wait up to 8 seconds for CDP to become alive
        for _ in range(16):
            time.sleep(0.5)
            if is_cdp_running():
                return True, "Chrome launched successfully."
        return True, "Chrome process started (waiting for CDP connection)."
    except Exception as e:
        return False, f"Failed to launch Chrome: {e}"


class GeminiBridge:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.lock = asyncio.Lock()

    async def ensure_connected(self):
        """Connects to real Chrome via CDP and locates the Gemini page."""
        if not is_cdp_running():
            launched, msg = launch_real_chrome()
            if not launched:
                raise RuntimeError(msg)

        if not self.playwright:
            self.playwright = await async_playwright().start()

        if not self.browser or not self.browser.is_connected():
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp(CDP_URL)
            except Exception as e:
                raise RuntimeError(f"Could not connect to Chrome CDP on port {CDP_PORT}: {e}")

        # Find existing Gemini tab or open one
        contexts = self.browser.contexts
        if not contexts:
            raise RuntimeError("No browser context found in Chrome.")
        
        self.context = contexts[0]
        pages = self.context.pages
        gemini_page = None

        for p in pages:
            if "gemini.google.com" in p.url:
                gemini_page = p
                break

        if not gemini_page:
            gemini_page = await self.context.new_page()
            await gemini_page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")
            await asyncio.sleep(2)

        self.page = gemini_page
        return self.page

    async def get_status(self):
        """Returns connection status and login state."""
        cdp_active = is_cdp_running()
        if not cdp_active:
            return {
                "connected": False,
                "logged_in": False,
                "url": None,
                "message": "Chrome is not running. Click 'Launch Real Chrome' to start."
            }

        try:
            page = await self.ensure_connected()
            url = page.url

            # Check if user is logged into Gemini
            logged_in = False
            if "gemini.google.com" in url:
                # Check for prompt input or user profile elements
                has_input = await page.evaluate("""() => {
                    const el = document.querySelector('rich-textarea, .ql-editor, [contenteditable="true"], [role="textbox"], textarea');
                    const signInBtn = Array.from(document.querySelectorAll('a, button')).some(b => (b.innerText || '').toLowerCase().includes('sign in'));
                    return el !== null && !signInBtn;
                }""")
                logged_in = bool(has_input)

            return {
                "connected": True,
                "logged_in": logged_in,
                "url": url,
                "message": "Ready" if logged_in else "Please sign in to your Google Account in the opened Chrome window."
            }
        except Exception as e:
            return {
                "connected": False,
                "logged_in": False,
                "url": None,
                "message": f"Connection check error: {e}"
            }

    async def get_cookies(self):
        """Retrieves cookies from the Gemini session."""
        try:
            await self.ensure_connected()
            cookies = await self.context.cookies(["https://gemini.google.com"])
            return cookies
        except Exception as e:
            return {"error": str(e)}

    async def start_new_chat(self):
        """Clicks New Chat or navigates to fresh Gemini conversation."""
        async with self.lock:
            page = await self.ensure_connected()
            # Try finding new chat button or navigate
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
            return {"status": "success", "message": "Started new conversation"}

    async def send_prompt_stream(self, prompt: str):
        """
        Sends a prompt to Gemini in Chrome and streams the response text in real-time.
        Yields chunks of generated text as they appear.
        """
        async with self.lock:
            page = await self.ensure_connected()

            # Ensure we are on gemini app
            if "gemini.google.com" not in page.url:
                await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")
                await asyncio.sleep(2)

            # Count existing model-response elements
            initial_count = await page.evaluate("""() => {
                return document.querySelectorAll('model-response').length;
            }""")

            # Focus editor and insert text cleanly
            editor_loc = page.locator('.ql-editor[contenteditable="true"], div[aria-label="Enter a prompt for Gemini"], rich-textarea div[contenteditable="true"], textarea').first
            if await editor_loc.count() > 0:
                await editor_loc.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")

            # Fill prompt input using execCommand for Angular/Quill binding
            input_found = await page.evaluate("""(text) => {
                const target = document.querySelector('.ql-editor[contenteditable="true"], rich-textarea div[contenteditable="true"], div[role="textbox"], textarea');
                if (!target) return false;
                
                target.focus();
                if (target.tagName.toLowerCase() === 'textarea' || target.tagName.toLowerCase() === 'input') {
                    target.value = text;
                    target.dispatchEvent(new Event('input', { bubbles: true }));
                    target.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                    document.execCommand('insertText', false, text);
                    target.dispatchEvent(new Event('input', { bubbles: true }));
                    target.dispatchEvent(new Event('change', { bubbles: true }));
                }
                return true;
            }""", prompt)

            if not input_found:
                if await editor_loc.count() > 0:
                    await editor_loc.click()
                    await editor_loc.press_sequentially(prompt, delay=10)
                else:
                    yield {"error": "Could not locate Gemini chat input box. Please ensure you are logged into Gemini."}
                    return

            await asyncio.sleep(0.3)

            # Click send button or press Enter
            send_btn = page.locator('button[aria-label="Send message"], button[aria-label*="Send"], .send-button button').first
            send_clicked = False
            if await send_btn.count() > 0 and await send_btn.is_visible():
                is_disabled = await send_btn.is_disabled()
                if not is_disabled:
                    await send_btn.click(force=True)
                    send_clicked = True

            if not send_clicked:
                await page.keyboard.press("Enter")

            # Stream the response
            yield {"status": "thinking", "chunk": ""}

            last_text = ""
            unchanged_ticks = 0
            max_ticks = 240  # 120 seconds max timeout
            ticks = 0
            has_started_generating = False

            while ticks < max_ticks:
                await asyncio.sleep(0.5)
                ticks += 1

                # Extract latest response data
                res = await page.evaluate(r"""(initCount) => {
                    const responses = document.querySelectorAll('model-response');
                    const isGenerating = document.querySelector('button[aria-label*="Stop"], button.stop-button, .generating-indicator') !== null;

                    if (responses.length <= initCount) {
                        return { text: '', html: '', isGenerating: isGenerating, count: responses.length, hasNew: false };
                    }

                    const target = responses[responses.length - 1];
                    if (!target) {
                        return { text: '', html: '', isGenerating: isGenerating, count: responses.length, hasNew: false };
                    }

                    const clone = target.cloneNode(true);

                    // Remove non-content elements (action buttons, toolbars, feedback)
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
                            return `\\n\`\`\`${cleanLang}\\n${code.textContent.trim()}\\n\`\`\`\\n`;
                        }
                        if (tag === 'code-block') {
                            const lang = node.getAttribute('language') || '';
                            return `\\n\`\`\`${lang}\\n${node.textContent.trim()}\\n\`\`\`\\n`;
                        }
                        if (tag === 'code') {
                            return `\`${node.textContent}\``;
                        }

                        if (/^h[1-6]$/.test(tag)) {
                            const level = parseInt(tag[1], 10);
                            const prefix = '#'.repeat(level);
                            const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                            return `\\n\\n${prefix} ${inner}\\n\\n`;
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

                        if (tag === 'blockquote') {
                            const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                            const lines = inner.split('\\n').map(l => `> ${l}`).join('\\n');
                            return `\\n\\n${lines}\\n\\n`;
                        }

                        if (tag === 'ul') {
                            let res = '\\n';
                            Array.from(node.children).forEach(child => {
                                if (child.tagName.toLowerCase() === 'li') {
                                    res += domToMarkdown(child, listDepth + 1, null);
                                }
                            });
                            return res + '\\n';
                        }

                        if (tag === 'ol') {
                            let res = '\\n';
                            let idx = 1;
                            Array.from(node.children).forEach(child => {
                                if (child.tagName.toLowerCase() === 'li') {
                                    res += domToMarkdown(child, listDepth + 1, idx++);
                                }
                            });
                            return res + '\\n';
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
                            return `${indent}${bullet}${inner.trim()}${subLists}\\n`;
                        }

                        if (tag === 'table') {
                            let mdTable = '\\n\\n';
                            const rows = Array.from(node.querySelectorAll('tr'));
                            if (rows.length > 0) {
                                const cleanCell = (cell) => {
                                    let cellMd = domToMarkdown(cell, 0).trim();
                                    cellMd = cellMd.replace(/\\r?\\n+/g, ' ');
                                    cellMd = cellMd.replace(/(?<!\\\\)\\|/g, '\\\\|');
                                    return cellMd || ' ';
                                };

                                const headerRow = rows[0];
                                const headerCells = Array.from(headerRow.querySelectorAll('th, td')).map(cleanCell);
                                if (headerCells.length > 0) {
                                    mdTable += '| ' + headerCells.join(' | ') + ' |\\n';
                                    mdTable += '| ' + headerCells.map(() => '---').join(' | ') + ' |\\n';
                                    for (let i = 1; i < rows.length; i++) {
                                        const rowCells = Array.from(rows[i].querySelectorAll('td, th')).map(cleanCell);
                                        while (rowCells.length < headerCells.length) {
                                            rowCells.push(' ');
                                        }
                                        mdTable += '| ' + rowCells.join(' | ') + ' |\\n';
                                    }
                                }
                            }
                            return mdTable + '\\n\\n';
                        }

                        if (tag === 'br') {
                            return '\\n';
                        }
                        if (tag === 'hr') {
                            return '\\n\\n---\\n\\n';
                        }
                        if (tag === 'p') {
                            const inner = Array.from(node.childNodes).map(c => domToMarkdown(c, listDepth)).join('').trim();
                            return inner ? `\\n\\n${inner}\\n\\n` : '';
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
                    markdown = markdown.replace(/\\n{3,}/g, '\\n\\n').trim();

                    if (!markdown) {
                        markdown = (clone.innerText || clone.textContent || '').trim();
                    }

                    return {
                        text: markdown,
                        html: target.innerHTML || '',
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
                            "full_text": current_text,
                            "full_html": res.get("html", "")
                        }
                    elif current_text == last_text:
                        unchanged_ticks += 1
                else:
                    unchanged_ticks += 1

                # If text has stopped changing and is not actively generating
                if has_started_generating and unchanged_ticks >= 4 and not is_generating:
                    break

                # If after 15 seconds no text at all appeared and not generating
                if not has_started_generating and ticks > 30 and not is_generating:
                    break

            # Final yield
            yield {
                "status": "done",
                "chunk": "",
                "full_text": last_text if last_text else "No response received from Gemini.",
                "full_html": res.get("html", "") if 'res' in locals() else ""
            }

bridge = GeminiBridge()
