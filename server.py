import os
import sys
import json
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from auth_manager import DEFAULT_USER_ID, verify_pin_or_password, hash_pin_or_password
from companion_bridge import companion_bridge, launch_real_chrome, is_cdp_running
from storage import storage
from memory_engine import memory_engine
from tools_engine import tools_gateway
from wisdom_catalog import get_all_wisdom_lessons, find_matching_wisdom
from safety_engine import safety_engine
from mcp_server import mcp_server

app = FastAPI(title="Omni — AI Life Companion (V2.0)", version="2.0.0")

if getattr(sys, 'frozen', False):
    if hasattr(sys, '_MEIPASS'):
        STATIC_DIR = Path(sys._MEIPASS) / "static"
    else:
        STATIC_DIR = Path(sys.executable).parent / "static"
    if not STATIC_DIR.exists():
        STATIC_DIR = Path(sys.executable).parent / "_internal" / "static"
else:
    STATIC_DIR = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------- PYDANTIC REQUEST SCHEMAS ---------------- #

class CreateUserRequest(BaseModel):
    username: str
    display_name: Optional[str] = None
    pin: Optional[str] = None
    avatar: Optional[str] = "🌱"

class LoginUserRequest(BaseModel):
    user_id: str
    pin: Optional[str] = None

class CheckinRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    date: Optional[str] = None
    mood: str
    energy: str

class DiaryRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    date: Optional[str] = None
    diary_draft: str

class ReflectionCardSaveRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    date: Optional[str] = None
    what_happened: str
    what_i_felt: str
    what_mattered: str
    balanced_perspective: str
    one_small_next_step: str
    what_i_want_to_remember: str

class WisdomSaveRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    wisdom_id: str
    title: str
    author_source: str
    topic: str
    concept_summary: str
    user_note: Optional[str] = ""
    micro_practice: Optional[str] = ""

class ProfileFactRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    category: str
    key: str
    value: str

class DeleteFactRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    key: str

class ToolExecuteRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    name: str
    arguments: Dict[str, Any]

class SafetyCheckRequest(BaseModel):
    text: str

class TaskCreateRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    title: str
    description: Optional[str] = ""
    due_date: Optional[str] = None
    category: Optional[str] = "general"

class TaskStatusUpdateRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    status: str

class ForgetMeRequest(BaseModel):
    user_id: Optional[str] = DEFAULT_USER_ID
    target_term: str

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[Dict[str, Any]] = {}

# ---------------- ROUTE HANDLERS ---------------- #

@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Omni AI Life Companion Server Active</h1>")

# ---------------- USER AUTH & PROFILES ---------------- #

@app.get("/api/users")
async def list_users():
    users = storage.get_all_users()
    return {"users": users}

@app.post("/api/users/create")
async def create_user(req: CreateUserRequest):
    user = storage.get_or_create_user(
        username=req.username,
        display_name=req.display_name,
        pin=req.pin,
        avatar=req.avatar or "🌱"
    )
    return {"status": "success", "user": user}

@app.post("/api/users/login")
async def login_user(req: LoginUserRequest):
    user = storage.get_user_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found.")
    
    stored_pin = user.get("pin_hash")
    if stored_pin:
        if not req.pin or not verify_pin_or_password(req.pin, stored_pin):
            raise HTTPException(status_code=401, detail="Invalid PIN for this profile.")
    
    storage.update_user_activity(req.user_id)
    return {"status": "success", "user": user}

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    if user_id == DEFAULT_USER_ID:
        raise HTTPException(status_code=400, detail="Cannot delete default space.")
    deleted = storage.delete_user(user_id)
    return {"status": "success", "deleted": deleted}

# ---------------- STATUS & CDP CONNECTION ---------------- #

@app.get("/api/status")
async def get_status(user_id: str = DEFAULT_USER_ID):
    bridge_status = await companion_bridge.get_status()
    today_workspace = storage.get_or_create_daily_workspace(user_id=user_id)
    user = storage.get_user_by_id(user_id)
    return {
        "bridge": bridge_status,
        "workspace": today_workspace,
        "active_user": user,
        "date": datetime.date.today().strftime("%A, %B %d, %Y")
    }

@app.post("/api/connect")
async def connect_chrome():
    ok, msg = launch_real_chrome()
    return {"status": "success" if ok else "error", "message": msg}

# ---------------- DAILY WORKSPACE & CHECK-IN ---------------- #

@app.get("/api/workspace")
async def get_workspace(user_id: str = DEFAULT_USER_ID, date: Optional[str] = None):
    ws = storage.get_or_create_daily_workspace(user_id=user_id, date_str=date)
    cards = storage.get_reflection_cards(user_id=user_id, date_str=date)
    return {"workspace": ws, "reflection_cards": cards}

@app.post("/api/checkin")
async def update_checkin(req: CheckinRequest):
    today_str = req.date or datetime.date.today().isoformat()
    ws = storage.update_checkin(user_id=req.user_id, date_str=today_str, mood=req.mood, energy=req.energy)
    return {"status": "success", "workspace": ws}

@app.post("/api/diary")
async def save_diary(req: DiaryRequest):
    today_str = req.date or datetime.date.today().isoformat()
    ws = storage.update_diary_draft(user_id=req.user_id, date_str=today_str, diary_draft=req.diary_draft)
    return {"status": "success", "workspace": ws}

@app.get("/api/workspaces/history")
async def list_workspaces(user_id: str = DEFAULT_USER_ID, limit: int = 30):
    history = storage.get_all_workspaces(user_id=user_id, limit=limit)
    return {"workspaces": history}

# ---------------- CHAT HISTORY ---------------- #

@app.get("/api/chat/history")
async def get_chat_history(user_id: str = DEFAULT_USER_ID, date: Optional[str] = None):
    today_str = date or datetime.date.today().isoformat()
    history = storage.get_chat_history(user_id=user_id, session_date=today_str)
    return {"history": history}

@app.get("/api/companion/greeting")
async def get_companion_greeting(user_id: str = DEFAULT_USER_ID):
    greeting_data = memory_engine.generate_personalized_greeting(user_id=user_id)
    return greeting_data

@app.delete("/api/chat/messages/{message_id}")
async def delete_chat_message(message_id: int, user_id: str = DEFAULT_USER_ID):
    deleted = storage.delete_chat_message(user_id=user_id, message_id=message_id)
    return {"status": "success" if deleted else "not_found", "deleted": deleted}

# ---------------- REFLECTION CARDS ---------------- #

@app.post("/api/reflection-card")
async def save_reflection_card(req: ReflectionCardSaveRequest):
    card_id = storage.save_reflection_card(user_id=req.user_id, card_data=req.dict())
    return {"status": "success", "card_id": card_id}

@app.get("/api/reflection-cards")
async def list_reflection_cards(user_id: str = DEFAULT_USER_ID):
    cards = storage.get_reflection_cards(user_id=user_id)
    return {"cards": cards}

# ---------------- WISDOM CATALOG & SAVED LESSONS ---------------- #

@app.get("/api/wisdom/catalog")
async def get_wisdom_catalog():
    lessons = get_all_wisdom_lessons()
    return {"catalog": lessons}

@app.get("/api/wisdom/saved")
async def get_saved_wisdom(user_id: str = DEFAULT_USER_ID):
    saved = storage.get_saved_wisdom(user_id=user_id)
    return {"saved_wisdom": saved}

@app.post("/api/wisdom/save")
async def save_wisdom_lesson(req: WisdomSaveRequest):
    item_id = storage.save_wisdom_item(user_id=req.user_id, wisdom_data=req.dict())
    return {"status": "success", "item_id": item_id}

@app.delete("/api/wisdom/{item_id}")
async def delete_wisdom(item_id: int, user_id: str = DEFAULT_USER_ID):
    deleted = storage.delete_wisdom_item(user_id=user_id, item_id=item_id)
    return {"status": "success", "deleted": deleted}

# ---------------- KNOWLEDGE GRAPH (V2) ---------------- #

@app.get("/api/knowledge-graph")
async def get_knowledge_graph(user_id: str = DEFAULT_USER_ID):
    kg = storage.get_knowledge_graph(user_id=user_id)
    return kg

@app.delete("/api/knowledge-graph/entity/{entity_id}")
async def delete_entity(entity_id: str, user_id: str = DEFAULT_USER_ID):
    deleted = storage.delete_entity(user_id=user_id, entity_id=entity_id)
    return {"status": "success", "deleted": deleted}

# ---------------- TASKS & ACTION MANAGEMENT (V2) ---------------- #

@app.get("/api/tasks")
async def get_tasks(user_id: str = DEFAULT_USER_ID, status: Optional[str] = None, category: Optional[str] = None):
    tasks = storage.get_tasks(user_id=user_id, status=status, category=category)
    return {"tasks": tasks}

@app.post("/api/tasks")
async def create_task(req: TaskCreateRequest):
    task = storage.create_task(
        user_id=req.user_id,
        title=req.title,
        description=req.description or "",
        due_date=req.due_date,
        category=req.category or "general"
    )
    return {"status": "success", "task": task}

@app.patch("/api/tasks/{task_id}/status")
async def update_task_status(task_id: str, req: TaskStatusUpdateRequest):
    task = storage.update_task_status(user_id=req.user_id, task_id=task_id, status=req.status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"status": "success", "task": task}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, user_id: str = DEFAULT_USER_ID):
    deleted = storage.delete_task(user_id=user_id, task_id=task_id)
    return {"status": "success", "deleted": deleted}

# ---------------- USER PROFILE & MEMORY VAULT ---------------- #

@app.get("/api/profile/facts")
async def get_facts(user_id: str = DEFAULT_USER_ID, category: Optional[str] = None):
    facts = storage.get_profile_facts(user_id=user_id, category=category)
    return {"facts": facts}

@app.post("/api/profile/facts")
async def save_fact(req: ProfileFactRequest):
    storage.save_profile_fact(user_id=req.user_id, category=req.category, key=req.key, value=req.value)
    return {"status": "success", "fact": req.dict()}

@app.delete("/api/profile/facts")
async def delete_fact(req: DeleteFactRequest):
    deleted = storage.delete_profile_fact(user_id=req.user_id, key=req.key)
    return {"status": "success", "deleted": deleted}

@app.get("/api/memory/search")
async def search_memories(user_id: str = DEFAULT_USER_ID, query: str = "", limit: int = 5):
    memories = memory_engine.recall_memories(user_id=user_id, query=query, limit=limit)
    return {"memories": memories}

@app.get("/api/memory/audit")
async def get_memory_audit_logs(user_id: str = DEFAULT_USER_ID, limit: int = 50):
    logs = storage.get_memory_audit_logs(user_id=user_id, limit=limit)
    return {"audit_logs": logs}

@app.post("/api/memory/forget-me")
async def purge_forget_me(req: ForgetMeRequest):
    result = storage.purge_memories_forget_me(user_id=req.user_id, target_term=req.target_term)
    return result

# ---------------- MCP SERVER JSON-RPC ENDPOINT (V2) ---------------- #

@app.post("/api/mcp")
async def handle_mcp_request(req: JsonRpcRequest, user_id: str = DEFAULT_USER_ID):
    res = await mcp_server.handle_json_rpc(request_data=req.dict(), user_id=user_id)
    return res

# ---------------- TOOLS & AUTOMATION ---------------- #

@app.get("/api/tools/definitions")
async def get_tool_definitions():
    tools = tools_gateway.get_tool_definitions()
    return {"tools": tools}

@app.post("/api/tools/execute")
async def execute_tool(req: ToolExecuteRequest):
    res = await tools_gateway.execute_tool(user_id=req.user_id, name=req.name, arguments=req.arguments)
    return res

@app.post("/api/safety/check")
async def safety_check(req: SafetyCheckRequest):
    result = safety_engine.evaluate_text(req.text)
    return result

@app.post("/api/session/new")
async def start_new_session(user_id: str = DEFAULT_USER_ID):
    res = await companion_bridge.start_new_daily_session(user_id=user_id)
    return res

@app.post("/api/gem/auto-create")
async def auto_create_gem():
    res = await companion_bridge.auto_create_gem()
    return res

@app.post("/api/synthesize/reflection-card")
async def synthesize_card(user_id: str = DEFAULT_USER_ID):
    today_str = datetime.date.today().isoformat()
    card_data = await companion_bridge.synthesize_reflection_card(user_id=user_id, chat_summary="")
    card_data["date"] = today_str
    return {"status": "success", "card": card_data}

@app.post("/api/synthesize/diary-draft")
async def synthesize_diary(user_id: str = DEFAULT_USER_ID):
    draft = await companion_bridge.synthesize_diary_draft(user_id=user_id, chat_summary="")
    return {"status": "success", "diary_draft": draft}

# ---------------- WEBSOCKET STREAMING ---------------- #

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    today_str = datetime.date.today().isoformat()

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_text = payload.get("text", "").strip()
            mode = payload.get("mode", "Adaptive")
            user_id = payload.get("user_id", DEFAULT_USER_ID)
            incognito = payload.get("incognito", False)

            if not user_text:
                continue

            # 1. Safety check
            safety_eval = safety_engine.evaluate_text(user_text)
            if safety_eval["level"] == 3:
                await websocket.send_json({
                    "status": "crisis",
                    "resources": safety_eval["resources"],
                    "message": safety_eval["guidance"]
                })
                if not incognito:
                    storage.save_chat_message(user_id, today_str, "user", user_text, mode)
                    storage.save_chat_message(user_id, today_str, "companion", safety_eval["resources"]["message"], "Crisis Support")
                continue

            # 2. Record user message if not incognito
            if not incognito:
                storage.save_chat_message(user_id, today_str, "user", user_text, mode)

            # 3. Stream from Gemini with Recall Enforcement Gate & Adaptive Intelligence
            full_reply = ""
            async for chunk in companion_bridge.send_prompt_stream(user_text, user_id=user_id):
                await websocket.send_json(chunk)
                if chunk.get("status") in ["streaming", "done"]:
                    full_reply = chunk.get("full_text", full_reply)

            # 4. Save companion reply if not incognito
            if not incognito and full_reply:
                storage.save_chat_message(user_id, today_str, "companion", full_reply, mode)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"status": "error", "error": str(e)})
        except Exception:
            pass
