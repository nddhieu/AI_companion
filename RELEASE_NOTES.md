# 🚀 Release Notes — Omni: Stateful AI Life Companion (v2.0.0)

> **Release Tag**: `v2.0.0`  
> **Release Title**: Omni v2.0.0: Stateful Memory, Real Browser CDP Bridge, MCP 2.0 & Windows Desktop App  
> **Author**: Hieu Nguyen (@nddhieu)  
> **Date**: August 2026  

---

## 🌟 Overview

**Omni v2.0.0** is a major milestone release introducing an evolving, private, local-first AI Life Companion that **remembers, sees, and does**. 

This release transforms Omni from a chat interface into an autonomous, stateful personal growth partner with an autobiographical memory layer, an unblockable real-browser CDP bridge, official Model Context Protocol (MCP JSON-RPC 2.0) integration, emotional intelligence tracking, and a packaged standalone Windows desktop application.

---

## 📦 What's New in v2.0.0

### 1. 🧠 Autobiographical Memory Engine (`hypermem` Judge-Store-Recall)
* **Hybrid 4-Factor Retrieval**: Combines dense vector embeddings (semantic similarity), BM25 token matching (lexical precision), user importance ratings ($1–10$), and exponential recency decay ($e^{-\lambda \Delta t}$).
* **Recall-Before-Action Gate**: Validates that past user context and active memory nodes are loaded before executing critical tools, preventing hallucinated actions.
* **Automatic Consolidation**: Asynchronously identifies key milestones, personal facts, recurring goals, and core values across conversation sessions.

### 2. 🌐 Zero-Bot-Detection Real Chrome & Edge CDP Bridge
* **Direct CDP Connection**: Launches genuine Google Chrome or Microsoft Edge using the Chrome DevTools Protocol (`--remote-debugging-port=9222`).
* **Persistent Google Session**: Operates directly within your personal authenticated Google Gemini web session with persistent browser profiles in `chrome_profile/`.
* **Zero Automation Fingerprint**: Eliminates automated WebDriver/bot detection flags and authentication blocks.

### 3. ⚡ Official Model Context Protocol (MCP JSON-RPC 2.0)
Standardized tool server interface supporting local tools, agentic sandboxes, and external clients:
* `remember` / `search_memories` / `get_user_profile`: Bi-directional memory querying.
* `create_task` / `list_tasks` / `complete_task`: Actionable goal & task tracking.
* `read_file` / `write_file` / `list_files`: Sandboxed local workspace file operations (`companion_workspace/`).
* `search_web`: Live search retrieval for real-time web facts.
* `save_reflection_card` / `save_wisdom_lesson`: Stoic and CBT cognitive reflection frameworks.

### 4. 🎭 2D Affective Circumplex EQ Engine
* **Continuous Emotion State Tracking**: Analyzes conversation turns for:
  * **Valence** $\in [-1.0, 1.0]$ (*Unpleasant $\leftrightarrow$ Pleasant*)
  * **Arousal** $\in [-1.0, 1.0]$ (*Low Energy / Deactivated $\leftrightarrow$ High Energy / Activated*)
* **Adaptive Tone Modulation**: Automatically switches between gentle, grounding empathy when overwhelmed to structured, incisive coaching when focused.

### 5. 🛡️ Constitutional Verifier & Cryptographic Privacy Sovereignty
* **Trauma & Sensitive Topic Suppression**: Automatically suppresses sensitive or traumatic memory nodes during light conversation.
* **Cryptographic "Forget Me" Hard Purge**: Permanently purges user-specified memory items and generates tamper-evident, cryptographically signed tombstones.

### 6. 🖥️ Standalone Windows Desktop App (`.exe`)
* Native WebView2 desktop application packaged with PyInstaller.
* Runs standalone without requiring manual Python environment setup.
* One-click build script (`build.bat`) and fast local launcher (`run.bat`).

### 7. 🎙️ Voice Journaling & Modern Web Interface
* Full glassmorphic UI with dark mode, real-time WebSocket communication, hands-free Speech-to-Text (STT) voice input, and audio Speech-to-Text (TTS) playback.

---

## 📥 Installation & Download

### Option 1: Standalone Windows Executable (.exe)
1. Download the release asset `Omni-Life-Companion-v2.0.0.zip` or `Omni-Life-Companion.exe` from the [GitHub Releases Page](https://github.com/nddhieu/AI_companion/releases).
2. Extract the archive and launch **`Omni-Life-Companion.exe`**.
3. Log into Google Gemini on your browser when prompted on initial launch.

### Option 2: Run from Source (Python 3.10+)

```powershell
# 1. Clone the repository
git clone https://github.com/nddhieu/AI_companion.git
cd AI_companion

# 2. Install dependencies
python -m pip install -r requirements.txt

# 3. Launch Omni
python main.py
# or double-click run.bat
```

---

## 🛠️ System Requirements
* **Operating System**: Windows 10 or Windows 11 (64-bit)
* **Browser**: Google Chrome or Microsoft Edge (for CDP Gemini bridge)
* **Runtime** (if running from source): Python 3.10 to 3.12
* **Storage**: ~200 MB free space for memory database and profile cache

---

## 🧪 Verification & Test Suite
All core subsystems have been verified with automated unit and integration tests:
```powershell
python test_v2_features.py
python test_prompt_and_flow.py
python test_natural_prompt.py
```
* **Memory Engine Tests**: 100% pass (hybrid ranking, BM25, recency decay)
* **MCP 2.0 Handlers**: 100% pass (sandbox I/O, task actions, wisdom catalog)
* **Safety Engine**: 100% pass (hard purge verification, trauma suppression)
