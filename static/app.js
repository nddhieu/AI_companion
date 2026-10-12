// Omni — AI Life Companion Frontend State Manager (V2.0 Stateful Memory & MCP)

class LifeCompanionApp {
  constructor() {
    this.currentDate = this.getLocalDateString();
    this.currentUserId = localStorage.getItem("omni_user_id") || "default_user";
    this.currentUser = null;
    this.incognito = false;
    this.socket = null;
    this.activeResponseBubble = null;
    this.isGenerating = false;
    this.isRecordingVoice = false;
    this.speechRecognition = null;
    this.sidebarCollapsed = localStorage.getItem("omni_sidebar_collapsed") === "true";

    // AI Engine & Host Environment Detection
    this.isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    const savedEngine = localStorage.getItem("omni_ai_engine");
    this.aiEngine = savedEngine || (this.isLocal ? "gemini_web" : "gemini_api");
    this.geminiApiKey = localStorage.getItem("omni_gemini_api_key") || "";

    // Configure Markdown Parser
    if (typeof marked !== "undefined") {
      marked.setOptions({
        breaks: true,
        gfm: true
      });
    }

    this.initElements();
    this.applySidebarState();
    this.updateEngineBadgeUI();
    this.initEvents();
    this.initVoiceRecognition();
    this.initWebSocket();
    this.loadUserProfiles();
    this.loadTodayWorkspace();
    this.checkBridgeStatus();
  }

  getLocalDateString(d = new Date()) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  initElements() {
    // App Container & Layout
    this.appContainer = document.querySelector(".app-container");
    this.btnToggleSidebar = document.getElementById("btnToggleSidebar");
    this.btnCollapseSidebar = document.getElementById("btnCollapseSidebar");
    this.btnExpandSidebar = document.getElementById("btnExpandSidebar");

    // Header & Adaptive Intelligence
    this.adaptiveStatusBadge = document.getElementById("adaptiveStatusBadge");
    this.currentDateBadge = document.getElementById("currentDateBadge");
    this.btnConnect = document.getElementById("btnConnect");
    this.statusDot = document.getElementById("statusDot");
    this.statusText = document.getElementById("statusText");
    this.btnNewDay = document.getElementById("btnNewDay");

    this.btnProfileDropdown = document.getElementById("btnProfileDropdown");
    this.profileMenu = document.getElementById("profileMenu");
    this.profileListContainer = document.getElementById("profileListContainer");
    this.btnOpenNewProfileModal = document.getElementById("btnOpenNewProfileModal");
    this.activeUserLabel = document.getElementById("activeUserLabel");
    this.userAvatarIcon = document.getElementById("userAvatarIcon");
    this.arrivalUserName = document.getElementById("arrivalUserName");

    // Incognito
    this.btnIncognitoToggle = document.getElementById("btnIncognitoToggle");
    this.incognitoIcon = document.getElementById("incognitoIcon");
    this.incognitoText = document.getElementById("incognitoText");
    this.privacyIndicatorTag = document.getElementById("privacyIndicatorTag");

    // Sidebar
    this.moodPicker = document.getElementById("moodPicker");
    this.energyPicker = document.getElementById("energyPicker");
    this.checkinStatus = document.getElementById("checkinStatus");
    this.reflectionCardSnippet = document.getElementById("reflectionCardSnippet");
    this.diaryDraftSnippet = document.getElementById("diaryDraftSnippet");
    this.btnViewCard = document.getElementById("btnViewCard");
    this.btnViewDiary = document.getElementById("btnViewDiary");
    
    // Sidebar Navigation Buttons (V2)
    this.btnOpenTasks = document.getElementById("btnOpenTasks");
    this.btnOpenKnowledgeGraph = document.getElementById("btnOpenKnowledgeGraph");
    this.btnOpenMemoryVault = document.getElementById("btnOpenMemoryVault");
    this.btnOpenWisdomLibrary = document.getElementById("btnOpenWisdomLibrary");
    this.btnOpenHistory = document.getElementById("btnOpenHistory");
    this.btnOpenHelplines = document.getElementById("btnOpenHelplines");

    // Chat
    this.chatContainer = document.getElementById("chatContainer");
    this.promptInput = document.getElementById("promptInput");
    this.sendBtn = document.getElementById("sendBtn");
    this.btnVoiceRecord = document.getElementById("btnVoiceRecord");
    this.voiceIcon = document.getElementById("voiceIcon");

    // Floating Action Dock
    this.btnDockReflection = document.getElementById("btnDockReflection");
    this.btnDockDiary = document.getElementById("btnDockDiary");
    this.btnDockWisdom = document.getElementById("btnDockWisdom");

    // Modals: Tasks (V2)
    this.tasksModal = document.getElementById("tasksModal");
    this.closeTasksModal = document.getElementById("closeTasksModal");
    this.btnCloseTasks = document.getElementById("btnCloseTasks");
    this.taskTitleInput = document.getElementById("taskTitleInput");
    this.taskCategoryInput = document.getElementById("taskCategoryInput");
    this.btnCreateTask = document.getElementById("btnCreateTask");
    this.pendingTasksContainer = document.getElementById("pendingTasksContainer");
    this.completedTasksContainer = document.getElementById("completedTasksContainer");

    // Modals: Knowledge Graph (V2)
    this.kgModal = document.getElementById("kgModal");
    this.closeKgModal = document.getElementById("closeKgModal");
    this.btnCloseKg = document.getElementById("btnCloseKg");
    this.kgUserName = document.getElementById("kgUserName");
    this.kgEntitiesContainer = document.getElementById("kgEntitiesContainer");
    this.kgRelationsContainer = document.getElementById("kgRelationsContainer");

    // Modals: Memory Vault & Sovereignty
    this.memoryVaultModal = document.getElementById("memoryVaultModal");
    this.closeMemoryVaultModal = document.getElementById("closeMemoryVaultModal");
    this.btnCloseMemoryVault = document.getElementById("btnCloseMemoryVault");
    this.memoryVaultUserName = document.getElementById("memoryVaultUserName");
    this.factsGridContainer = document.getElementById("factsGridContainer");
    this.factCountBadge = document.getElementById("factCountBadge");
    this.memoriesListContainer = document.getElementById("memoriesListContainer");
    this.auditLogsContainer = document.getElementById("auditLogsContainer");
    this.btnAddFact = document.getElementById("btnAddFact");
    this.factCategorySelect = document.getElementById("factCategorySelect");
    this.factKeyInput = document.getElementById("factKeyInput");
    this.factValInput = document.getElementById("factValInput");
    this.forgetMeInput = document.getElementById("forgetMeInput");
    this.btnExecuteForgetMe = document.getElementById("btnExecuteForgetMe");
    this.forgetMeFeedback = document.getElementById("forgetMeFeedback");

    // Modals: User Profiles & PIN
    this.profileModal = document.getElementById("profileModal");
    this.closeProfileModal = document.getElementById("closeProfileModal");
    this.btnCancelProfile = document.getElementById("btnCancelProfile");
    this.btnCreateProfileSubmit = document.getElementById("btnCreateProfileSubmit");
    this.newUsernameInput = document.getElementById("newUsernameInput");
    this.newDisplayNameInput = document.getElementById("newDisplayNameInput");
    this.newAvatarInput = document.getElementById("newAvatarInput");
    this.newPinInput = document.getElementById("newPinInput");

    this.pinModal = document.getElementById("pinModal");
    this.closePinModal = document.getElementById("closePinModal");
    this.btnCancelPin = document.getElementById("btnCancelPin");
    this.btnSubmitPin = document.getElementById("btnSubmitPin");
    this.loginPinInput = document.getElementById("loginPinInput");

    // Modals: Reflection & Diary
    this.reflectionModal = document.getElementById("reflectionModal");
    this.closeReflectionModal = document.getElementById("closeReflectionModal");
    this.btnSaveCard = document.getElementById("btnSaveCard");
    this.btnCopyCard = document.getElementById("btnCopyCard");

    this.diaryModal = document.getElementById("diaryModal");
    this.closeDiaryModal = document.getElementById("closeDiaryModal");
    this.diaryTextarea = document.getElementById("diaryTextarea");
    this.btnSaveDiary = document.getElementById("btnSaveDiary");
    this.btnCopyDiary = document.getElementById("btnCopyDiary");

    // Modals: Wisdom, History, Crisis
    this.wisdomModal = document.getElementById("wisdomModal");
    this.closeWisdomModal = document.getElementById("closeWisdomModal");
    this.btnCloseWisdom = document.getElementById("btnCloseWisdom");
    this.wisdomCardsContainer = document.getElementById("wisdomCardsContainer");

    this.historyModal = document.getElementById("historyModal");
    this.closeHistoryModal = document.getElementById("closeHistoryModal");
    this.btnCloseHistory = document.getElementById("btnCloseHistory");
    this.historyContainer = document.getElementById("historyContainer");

    this.crisisModal = document.getElementById("crisisModal");
    this.closeCrisisModal = document.getElementById("closeCrisisModal");
    this.btnDismissCrisis = document.getElementById("btnDismissCrisis");

    // Modals: AI Engine & Cloud Settings
    this.btnOpenEngineSettings = document.getElementById("btnOpenEngineSettings");
    this.engineSettingsModal = document.getElementById("engineSettingsModal");
    this.closeEngineSettingsModal = document.getElementById("closeEngineSettingsModal");
    this.btnCancelEngineSettings = document.getElementById("btnCancelEngineSettings");
    this.btnSaveEngineSettings = document.getElementById("btnSaveEngineSettings");
    this.hostStatusText = document.getElementById("hostStatusText");
    this.hostStatusBanner = document.getElementById("hostStatusBanner");
    this.cardEngineWeb = document.getElementById("cardEngineWeb");
    this.cardEngineApi = document.getElementById("cardEngineApi");
    this.tagEngineWeb = document.getElementById("tagEngineWeb");
    this.radioEngineWeb = document.querySelector('input[name="aiEngineRadio"][value="gemini_web"]');
    this.radioEngineApi = document.querySelector('input[name="aiEngineRadio"][value="gemini_api"]');
    this.apiKeySection = document.getElementById("apiKeySection");
    this.geminiApiKeyInput = document.getElementById("geminiApiKeyInput");
    this.btnToggleKeyVisibility = document.getElementById("btnToggleKeyVisibility");
    this.btnValidateKey = document.getElementById("btnValidateKey");
    this.keyValidationFeedback = document.getElementById("keyValidationFeedback");
    this.engineBadgeIcon = document.getElementById("engineBadgeIcon");
    this.engineBadgeText = document.getElementById("engineBadgeText");

    this.toastContainer = document.getElementById("toastContainer");
  }

  initEvents() {
    // Engine & Cloud Settings Events
    if (this.btnOpenEngineSettings) {
      this.btnOpenEngineSettings.addEventListener("click", () => this.openEngineSettingsModal());
    }
    if (this.closeEngineSettingsModal) {
      this.closeEngineSettingsModal.addEventListener("click", () => this.closeModal(this.engineSettingsModal));
    }
    if (this.btnCancelEngineSettings) {
      this.btnCancelEngineSettings.addEventListener("click", () => this.closeModal(this.engineSettingsModal));
    }
    if (this.btnSaveEngineSettings) {
      this.btnSaveEngineSettings.addEventListener("click", () => this.handleSaveEngineSettings());
    }
    if (this.btnValidateKey) {
      this.btnValidateKey.addEventListener("click", () => this.handleValidateApiKey());
    }
    if (this.btnToggleKeyVisibility) {
      this.btnToggleKeyVisibility.addEventListener("click", () => {
        const isPwd = this.geminiApiKeyInput.type === "password";
        this.geminiApiKeyInput.type = isPwd ? "text" : "password";
        this.btnToggleKeyVisibility.textContent = isPwd ? "🙈" : "👁️";
      });
    }
    document.querySelectorAll('input[name="aiEngineRadio"]').forEach(r => {
      r.addEventListener("change", (e) => {
        document.querySelectorAll(".engine-card").forEach(c => c.classList.remove("active"));
        e.target.closest(".engine-card")?.classList.add("active");
      });
    });
    // Profile Dropdown
    this.btnProfileDropdown.addEventListener("click", (e) => {
      e.stopPropagation();
      this.profileMenu.classList.toggle("open");
    });
    document.addEventListener("click", () => this.profileMenu.classList.remove("open"));

    this.btnOpenNewProfileModal.addEventListener("click", () => {
      this.profileMenu.classList.remove("open");
      this.openModal(this.profileModal);
    });
    this.closeProfileModal.addEventListener("click", () => this.closeModal(this.profileModal));
    this.btnCancelProfile.addEventListener("click", () => this.closeModal(this.profileModal));
    this.btnCreateProfileSubmit.addEventListener("click", () => this.handleCreateProfile());

    this.closePinModal.addEventListener("click", () => this.closeModal(this.pinModal));
    this.btnCancelPin.addEventListener("click", () => this.closeModal(this.pinModal));
    this.btnSubmitPin.addEventListener("click", () => this.handlePinSubmit());

    // Incognito Toggle
    this.btnIncognitoToggle.addEventListener("click", () => {
      this.incognito = !this.incognito;
      if (this.incognito) {
        this.btnIncognitoToggle.classList.add("active");
        this.incognitoIcon.textContent = "🕶️";
        this.incognitoText.textContent = "Incognito: Active";
        this.privacyIndicatorTag.textContent = "🕶️ Incognito (Zero Memory Saved)";
        this.showToast("🕶️ Incognito Active: Conversations won't be saved to memory.", "info");
      } else {
        this.btnIncognitoToggle.classList.remove("active");
        this.incognitoIcon.textContent = "🧠";
        this.incognitoText.textContent = "Memory: Active";
        this.privacyIndicatorTag.textContent = "🔒 Isolated Profile Storage (v2.0)";
        this.showToast("🧠 Memory Active: Insights will help Omni remember context.", "info");
      }
    });

    // Checkin Pickers
    this.moodPicker.addEventListener("click", (e) => {
      const btn = e.target.closest(".emoji-btn");
      if (!btn) return;
      document.querySelectorAll(".emoji-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      this.saveCheckin();
    });

    this.energyPicker.addEventListener("click", (e) => {
      const btn = e.target.closest(".energy-btn");
      if (!btn) return;
      document.querySelectorAll(".energy-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      this.saveCheckin();
    });

    // Chat Inputs & Voice
    this.sendBtn.addEventListener("click", () => this.sendMessage());
    this.promptInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    if (this.btnVoiceRecord) {
      this.btnVoiceRecord.addEventListener("click", () => this.toggleVoiceRecording());
    }

    this.promptInput.addEventListener("input", () => {
      this.promptInput.style.height = "auto";
      this.promptInput.style.height = Math.min(this.promptInput.scrollHeight, 140) + "px";
    });

    // Quick Starters
    this.chatContainer.addEventListener("click", (e) => {
      const starter = e.target.closest(".starter-chip");
      if (!starter) return;
      this.promptInput.value = starter.dataset.text;
      this.sendMessage();
    });

    // Sidebar Collapsible Controls
    if (this.btnToggleSidebar) this.btnToggleSidebar.addEventListener("click", () => this.toggleSidebar());
    if (this.btnCollapseSidebar) this.btnCollapseSidebar.addEventListener("click", () => this.toggleSidebar(true));
    if (this.btnExpandSidebar) this.btnExpandSidebar.addEventListener("click", () => this.toggleSidebar(false));

    // Connect & New Day Buttons
    this.btnConnect.addEventListener("click", () => this.connectChrome());
    this.btnNewDay.addEventListener("click", () => this.startNewDailySession());

    // Navigation Modals
    this.btnViewCard.addEventListener("click", () => this.openModal(this.reflectionModal));
    this.btnViewDiary.addEventListener("click", () => this.openModal(this.diaryModal));
    
    if (this.btnOpenTasks) {
      this.btnOpenTasks.addEventListener("click", () => this.openTasksModal());
    }
    if (this.btnOpenKnowledgeGraph) {
      this.btnOpenKnowledgeGraph.addEventListener("click", () => this.openKnowledgeGraphModal());
    }

    this.btnOpenMemoryVault.addEventListener("click", () => this.openMemoryVault());
    this.btnOpenWisdomLibrary.addEventListener("click", () => this.loadAllWisdomLessons());
    this.btnOpenHistory.addEventListener("click", () => this.loadWorkspaceHistory());
    this.btnOpenHelplines.addEventListener("click", () => this.openModal(this.crisisModal));

    // Action Dock
    this.btnDockReflection.addEventListener("click", () => this.generateReflectionCard());
    this.btnDockDiary.addEventListener("click", () => this.generateDiaryDraft());
    this.btnDockWisdom.addEventListener("click", () => this.matchWisdomLessons());

    // Modal Close Buttons
    if (this.closeTasksModal) this.closeTasksModal.addEventListener("click", () => this.closeModal(this.tasksModal));
    if (this.btnCloseTasks) this.btnCloseTasks.addEventListener("click", () => this.closeModal(this.tasksModal));
    if (this.btnCreateTask) this.btnCreateTask.addEventListener("click", () => this.handleCreateTask());

    if (this.closeKgModal) this.closeKgModal.addEventListener("click", () => this.closeModal(this.kgModal));
    if (this.btnCloseKg) this.btnCloseKg.addEventListener("click", () => this.closeModal(this.kgModal));

    this.closeMemoryVaultModal.addEventListener("click", () => this.closeModal(this.memoryVaultModal));
    this.btnCloseMemoryVault.addEventListener("click", () => this.closeModal(this.memoryVaultModal));
    this.btnAddFact.addEventListener("click", () => this.handleAddCustomFact());
    
    if (this.btnExecuteForgetMe) {
      this.btnExecuteForgetMe.addEventListener("click", () => this.handleForgetMePurge());
    }

    this.closeReflectionModal.addEventListener("click", () => this.closeModal(this.reflectionModal));
    this.btnSaveCard.addEventListener("click", () => this.saveReflectionCard());
    this.btnCopyCard.addEventListener("click", () => this.copyCardText());

    this.closeDiaryModal.addEventListener("click", () => this.closeModal(this.diaryModal));
    this.btnSaveDiary.addEventListener("click", () => this.saveDiaryDraft());
    this.btnCopyDiary.addEventListener("click", () => this.copyDiaryText());

    this.closeWisdomModal.addEventListener("click", () => this.closeModal(this.wisdomModal));
    this.btnCloseWisdom.addEventListener("click", () => this.closeModal(this.wisdomModal));

    this.closeHistoryModal.addEventListener("click", () => this.closeModal(this.historyModal));
    this.btnCloseHistory.addEventListener("click", () => this.closeModal(this.historyModal));

    this.closeCrisisModal.addEventListener("click", () => this.closeModal(this.crisisModal));
    this.btnDismissCrisis.addEventListener("click", () => this.closeModal(this.crisisModal));
  }

  // ---------------- VOICE RECOGNITION (STT) & SPEECH (TTS) ---------------- //

  initVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.speechRecognition = new SpeechRecognition();
      this.speechRecognition.continuous = false;
      this.speechRecognition.interimResults = true;
      this.speechRecognition.lang = "en-US";

      this.speechRecognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        this.promptInput.value = transcript;
        this.promptInput.style.height = "auto";
        this.promptInput.style.height = Math.min(this.promptInput.scrollHeight, 140) + "px";
      };

      this.speechRecognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        this.stopVoiceRecording();
      };

      this.speechRecognition.onend = () => {
        this.stopVoiceRecording();
      };
    }
  }

  toggleVoiceRecording() {
    if (!this.speechRecognition) {
      this.showToast("Voice speech-to-text not supported in this browser.", "info");
      return;
    }

    if (this.isRecordingVoice) {
      this.speechRecognition.stop();
      this.stopVoiceRecording();
    } else {
      try {
        this.speechRecognition.start();
        this.isRecordingVoice = true;
        this.btnVoiceRecord.classList.add("recording");
        this.voiceIcon.textContent = "🔴";
        this.showToast("🎙️ Listening... speak your thoughts.", "info");
      } catch (e) {
        this.stopVoiceRecording();
      }
    }
  }

  stopVoiceRecording() {
    this.isRecordingVoice = false;
    if (this.btnVoiceRecord) {
      this.btnVoiceRecord.classList.remove("recording");
      this.voiceIcon.textContent = "🎙️";
    }
  }

  speakText(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const cleanText = text.replace(/[*#`_\[\]]/g, "").trim();
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  }

  // ---------------- TASKS & ACTION MANAGEMENT (V2) ---------------- //

  async openTasksModal() {
    this.openModal(this.tasksModal);
    this.loadTasks();
  }

  async loadTasks() {
    try {
      const res = await fetch(`/api/tasks?user_id=${this.currentUserId}`);
      const data = await res.json();
      const tasks = data.tasks || [];

      this.pendingTasksContainer.innerHTML = "";
      this.completedTasksContainer.innerHTML = "";

      const pending = tasks.filter(t => t.status === "pending" || t.status === "in_progress");
      const completed = tasks.filter(t => t.status === "completed");

      if (pending.length === 0) {
        this.pendingTasksContainer.innerHTML = "<p class='empty-hint'>No pending action steps. Omni will help you create small 2-minute tasks!</p>";
      } else {
        pending.forEach(t => {
          const item = document.createElement("div");
          item.className = "task-item";
          item.innerHTML = `
            <input type="checkbox" class="task-checkbox" data-id="${t.id}">
            <div class="task-info">
              <strong>${t.title}</strong>
              <small class="task-cat">${t.category || "general"}</small>
            </div>
            <button class="task-del" data-id="${t.id}">×</button>
          `;
          item.querySelector(".task-checkbox").addEventListener("change", () => this.toggleTaskStatus(t.id, "completed"));
          item.querySelector(".task-del").addEventListener("click", () => this.deleteTask(t.id));
          this.pendingTasksContainer.appendChild(item);
        });
      }

      if (completed.length === 0) {
        this.completedTasksContainer.innerHTML = "<p class='empty-hint'>Completed tasks will appear here.</p>";
      } else {
        completed.forEach(t => {
          const item = document.createElement("div");
          item.className = "task-item completed";
          item.innerHTML = `
            <input type="checkbox" class="task-checkbox" checked data-id="${t.id}">
            <div class="task-info">
              <span class="strikethrough">${t.title}</span>
              <small class="task-cat">${t.category || "general"}</small>
            </div>
            <button class="task-del" data-id="${t.id}">×</button>
          `;
          item.querySelector(".task-checkbox").addEventListener("change", () => this.toggleTaskStatus(t.id, "pending"));
          item.querySelector(".task-del").addEventListener("click", () => this.deleteTask(t.id));
          this.completedTasksContainer.appendChild(item);
        });
      }
    } catch (e) {
      console.error("Failed to load tasks", e);
    }
  }

  async handleCreateTask() {
    const title = this.taskTitleInput.value.trim();
    const category = this.taskCategoryInput.value.trim() || "general";
    if (!title) return;

    try {
      await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId, title, category })
      });
      this.taskTitleInput.value = "";
      this.loadTasks();
      this.showToast("Small action step created!", "success");
    } catch (e) {
      alert("Failed to create task.");
    }
  }

  async toggleTaskStatus(taskId, status) {
    try {
      await fetch(`/api/tasks/${taskId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId, status })
      });
      this.loadTasks();
      this.showToast(`Task marked ${status}!`, "success");
    } catch (e) {
      alert("Failed to update task.");
    }
  }

  async deleteTask(taskId) {
    try {
      await fetch(`/api/tasks/${taskId}?user_id=${this.currentUserId}`, { method: "DELETE" });
      this.loadTasks();
      this.showToast("Task deleted.", "info");
    } catch (e) {
      alert("Failed to delete task.");
    }
  }

  // ---------------- KNOWLEDGE GRAPH (V2) ---------------- //

  async openKnowledgeGraphModal() {
    this.openModal(this.kgModal);
    this.kgUserName.textContent = this.currentUser?.display_name || "My Space";
    this.loadKnowledgeGraph();
  }

  async loadKnowledgeGraph() {
    try {
      const res = await fetch(`/api/knowledge-graph?user_id=${this.currentUserId}`);
      const data = await res.json();
      const entities = data.entities || [];
      const relations = data.relations || [];

      this.kgEntitiesContainer.innerHTML = "";
      this.kgRelationsContainer.innerHTML = "";

      if (entities.length === 0) {
        this.kgEntitiesContainer.innerHTML = "<p class='empty-hint'>No entity nodes found. As you converse, Omni extracts people, goals, and values.</p>";
      } else {
        entities.forEach(ent => {
          const chip = document.createElement("div");
          chip.className = `fact-chip cat-${ent.category}`;
          chip.innerHTML = `
            <div class="fact-cat">${ent.category.toUpperCase()}</div>
            <div class="fact-body">
              <strong>${ent.name}</strong>
              <span>Weight: ${ent.emotional_weight > 0 ? "+" : ""}${ent.emotional_weight}</span>
            </div>
            <button class="fact-delete" title="Delete entity">×</button>
          `;
          chip.querySelector(".fact-delete").addEventListener("click", async () => {
            if (confirm(`Delete entity "${ent.name}" from Knowledge Graph?`)) {
              await fetch(`/api/knowledge-graph/entity/${ent.id}?user_id=${this.currentUserId}`, { method: "DELETE" });
              this.loadKnowledgeGraph();
            }
          });
          this.kgEntitiesContainer.appendChild(chip);
        });
      }

      if (relations.length === 0) {
        this.kgRelationsContainer.innerHTML = "<p class='empty-hint'>No relationship graph edges created yet.</p>";
      } else {
        relations.forEach(rel => {
          const item = document.createElement("div");
          item.className = "relation-item";
          item.innerHTML = `
            <span class="rel-source">(${rel.source_name})</span>
            <span class="rel-arrow">--[ ${rel.relation_type} ]--></span>
            <span class="rel-target">(${rel.target_name})</span>
            <small class="rel-conf">Conf: ${(rel.confidence * 100).toFixed(0)}%</small>
          `;
          this.kgRelationsContainer.appendChild(item);
        });
      }
    } catch (e) {
      console.error("Failed to load knowledge graph", e);
    }
  }

  // ---------------- USER PROFILE MANAGEMENT ---------------- //

  async loadUserProfiles() {
    try {
      const res = await fetch("/api/users");
      const data = await res.json();
      const users = data.users || [];
      this.renderProfileList(users);

      const active = users.find(u => u.id === this.currentUserId) || users[0];
      if (active) {
        this.setCurrentUser(active);
      }
    } catch (e) {
      console.error("Failed to load user profiles", e);
    }
  }

  resolveSalutationName(name) {
    if (!name) return "Friend";
    const clean = name.trim();
    if (["my space", "default", "default_user", "friend", "user", "workspace", "none"].includes(clean.toLowerCase())) {
      return "Friend";
    }
    return clean;
  }

  setCurrentUser(user) {
    this.currentUser = user;
    this.currentUserId = user.id;
    localStorage.setItem("omni_user_id", user.id);
    
    this.activeUserLabel.textContent = user.display_name || user.username;
    this.userAvatarIcon.textContent = user.avatar || "🌱";
    this.arrivalUserName.textContent = this.resolveSalutationName(user.display_name || user.username);
    this.memoryVaultUserName.textContent = user.display_name || user.username;
  }

  renderProfileList(users) {
    this.profileListContainer.innerHTML = "";
    users.forEach(u => {
      const item = document.createElement("div");
      item.className = `profile-item ${u.id === this.currentUserId ? "active" : ""}`;
      item.innerHTML = `
        <span class="avatar">${u.avatar || "🌱"}</span>
        <div class="info">
          <strong>${u.display_name}</strong>
          <small>@${u.username}</small>
        </div>
      `;
      item.addEventListener("click", () => this.requestSwitchProfile(u));
      this.profileListContainer.appendChild(item);
    });
  }

  requestSwitchProfile(user) {
    this.profileMenu.classList.remove("open");
    if (user.id === this.currentUserId) return;

    if (user.pin_hash) {
      this.pendingSwitchUser = user;
      this.loginPinInput.value = "";
      this.openModal(this.pinModal);
      this.loginPinInput.focus();
    } else {
      this.switchProfileDirect(user);
    }
  }

  async handlePinSubmit() {
    if (!this.pendingSwitchUser) return;
    const pin = this.loginPinInput.value.trim();
    try {
      const res = await fetch("/api/users/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.pendingSwitchUser.id, pin: pin })
      });
      const data = await res.json();
      if (res.ok) {
        this.closeModal(this.pinModal);
        this.switchProfileDirect(data.user);
      } else {
        alert(data.detail || "Invalid PIN");
      }
    } catch (e) {
      alert("PIN verification failed.");
    }
  }

  switchProfileDirect(user) {
    this.setCurrentUser(user);
    this.loadUserProfiles();
    this.loadTodayWorkspace();
    this.showToast(`Switched space to ${user.display_name}`, "success");
  }

  async handleCreateProfile() {
    const username = this.newUsernameInput.value.trim();
    const displayName = this.newDisplayNameInput.value.trim();
    const avatar = this.newAvatarInput.value.trim() || "🌱";
    const pin = this.newPinInput.value.trim();

    if (!username) {
      alert("Please enter a unique username.");
      return;
    }

    try {
      const res = await fetch("/api/users/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, display_name: displayName, avatar, pin })
      });
      const data = await res.json();
      if (data.status === "success") {
        this.closeModal(this.profileModal);
        this.newUsernameInput.value = "";
        this.newDisplayNameInput.value = "";
        this.newPinInput.value = "";
        this.switchProfileDirect(data.user);
      }
    } catch (e) {
      alert("Failed to create profile: " + e);
    }
  }

  // ---------------- MEMORY VAULT & SOVEREIGNTY ---------------- //

  async openMemoryVault() {
    this.openModal(this.memoryVaultModal);
    this.loadMemoryFacts();
    this.loadEpisodicMemories();
    this.loadMemoryAuditLogs();
  }

  async loadMemoryFacts() {
    try {
      const res = await fetch(`/api/profile/facts?user_id=${this.currentUserId}`);
      const data = await res.json();
      const facts = data.facts || [];
      this.factCountBadge.textContent = `${facts.length} facts`;
      this.factsGridContainer.innerHTML = "";

      if (facts.length === 0) {
        this.factsGridContainer.innerHTML = `<p class="empty-hint">Omni hasn't extracted any personal facts yet. As you converse, they will appear here.</p>`;
        return;
      }

      facts.forEach(f => {
        const chip = document.createElement("div");
        chip.className = `fact-chip cat-${f.category}`;
        chip.innerHTML = `
          <div class="fact-cat">${f.category.toUpperCase()}</div>
          <div class="fact-body">
            <strong>${f.key}</strong>
            <span>${f.value}</span>
          </div>
          <button class="fact-delete" title="Delete this fact">×</button>
        `;
        chip.querySelector(".fact-delete").addEventListener("click", () => this.deleteMemoryFact(f.key));
        this.factsGridContainer.appendChild(chip);
      });
    } catch (e) {
      console.error("Failed to load facts", e);
    }
  }

  async handleAddCustomFact() {
    const category = this.factCategorySelect.value;
    const key = this.factKeyInput.value.trim();
    const value = this.factValInput.value.trim();

    if (!key || !value) {
      alert("Please provide both a label and details.");
      return;
    }

    try {
      await fetch("/api/profile/facts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId, category, key, value })
      });
      this.factKeyInput.value = "";
      this.factValInput.value = "";
      this.loadMemoryFacts();
      this.showToast(`Saved fact: ${key}`, "success");
    } catch (e) {
      alert("Failed to add fact.");
    }
  }

  async deleteMemoryFact(key) {
    if (!confirm(`Delete memory fact "${key}"?`)) return;
    try {
      await fetch("/api/profile/facts", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId, key })
      });
      this.loadMemoryFacts();
      this.showToast(`Deleted fact: ${key}`, "info");
    } catch (e) {
      alert("Failed to delete fact.");
    }
  }

  async loadEpisodicMemories() {
    try {
      const res = await fetch(`/api/memory/search?user_id=${this.currentUserId}&limit=10`);
      const data = await res.json();
      const memories = data.memories || [];
      this.memoriesListContainer.innerHTML = "";

      if (memories.length === 0) {
        this.memoriesListContainer.innerHTML = `<p class="empty-hint">No episodic reflection memories recorded yet.</p>`;
        return;
      }

      memories.forEach(m => {
        const item = document.createElement("div");
        item.className = "memory-item";
        item.innerHTML = `
          <div class="mem-date">📅 ${m.date} <span class="valence">Valence: ${m.emotional_valence} | Imp: ${m.importance_score || 5}/10</span></div>
          <div class="mem-summary">${m.summary}</div>
          <div class="mem-reason"><em>🔍 ${m.recall_reason || "Indexed in vector vault"}</em></div>
        `;
        this.memoriesListContainer.appendChild(item);
      });
    } catch (e) {
      console.error("Failed to load episodic memories", e);
    }
  }

  async loadMemoryAuditLogs() {
    try {
      const res = await fetch(`/api/memory/audit?user_id=${this.currentUserId}&limit=20`);
      const data = await res.json();
      const logs = data.audit_logs || [];
      this.auditLogsContainer.innerHTML = "";

      if (logs.length === 0) {
        this.auditLogsContainer.innerHTML = "<p class='empty-hint'>No audit events recorded yet.</p>";
        return;
      }

      logs.forEach(l => {
        const item = document.createElement("div");
        item.className = "audit-item";
        item.innerHTML = `
          <div class="audit-header">
            <span class="audit-action badge">${l.action.toUpperCase()}</span>
            <span class="audit-status ${l.verification_status.toLowerCase()}">${l.verification_status}</span>
            <span class="audit-time">${l.timestamp}</span>
          </div>
          <p class="audit-details">${l.details}</p>
          ${l.reason ? `<small class="audit-reason">Reason: ${l.reason}</small>` : ""}
          ${l.signature ? `<code class="audit-sig">Tombstone Sig: ${l.signature.substring(0, 16)}...</code>` : ""}
        `;
        this.auditLogsContainer.appendChild(item);
      });
    } catch (e) {
      console.error("Failed to load audit logs", e);
    }
  }

  async handleForgetMePurge() {
    const term = this.forgetMeInput.value.trim();
    if (!term) return;

    if (!confirm(`Are you sure you want to permanently purge all facts and memories relating to "${term}"?`)) return;

    try {
      const res = await fetch("/api/memory/forget-me", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId, target_term: term })
      });
      const data = await res.json();
      if (data.status === "success") {
        this.forgetMeFeedback.innerHTML = `
          <div class="purge-success">
            ✅ Purged ${data.deleted_facts} facts, ${data.deleted_memories} memories, ${data.deleted_entities} entities.<br>
            <small>Cryptographic Tombstone: <code>${data.tombstone_signature}</code></small>
          </div>
        `;
        this.forgetMeInput.value = "";
        this.loadMemoryFacts();
        this.loadEpisodicMemories();
        this.loadMemoryAuditLogs();
        this.showToast(`Permanently scrubbed records for "${term}"`, "success");
      }
    } catch (e) {
      alert("Purge failed: " + e);
    }
  }

  // ---------------- WEBSOCKET STREAMING ---------------- //

  initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log("Connected to AI Companion WebSocket stream.");
    };

    this.socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      this.handleSocketMessage(payload);
    };

    this.socket.onclose = () => {
      setTimeout(() => this.initWebSocket(), 2000);
    };
  }

  handleSocketMessage(payload) {
    if (payload.status === "thinking") {
      this.setGeneratingState(true);
      this.activeResponseBubble = this.createCompanionMessageBubble();
      this.activeResponseBubble.innerHTML = `<div class="thinking-indicator"><span class="dot"></span><span class="dot"></span><span class="dot"></span> Thinking...</div>`;
      this.scrollToBottom();
    } else if (payload.status === "streaming") {
      if (this.activeResponseBubble) {
        const fullMarkdown = payload.full_text;
        this.activeResponseBubble.innerHTML = this.renderMarkdown(fullMarkdown);
        const msgEl = this.activeResponseBubble.closest(".message");
        if (msgEl) msgEl.dataset.rawText = fullMarkdown;
        this.scrollToBottom();
      }
    } else if (payload.status === "tool_executed") {
      const toolRes = payload.tool_result || {};
      if (toolRes.status === "success") {
        this.showToast(`✨ Omni executed tool: ${toolRes.tool}`, "success");
        if (toolRes.tool === "save_reflection_card") {
          this.loadTodayWorkspace();
        }
      }
    } else if (payload.status === "crisis") {
      this.setGeneratingState(false);
      this.openModal(this.crisisModal);
      const crisisBubble = this.createCompanionMessageBubble();
      crisisBubble.innerHTML = this.renderMarkdown(`### ❤️ Immediate Crisis Support\n${payload.message}`);
      const msgEl = crisisBubble.closest(".message");
      if (msgEl) msgEl.dataset.rawText = payload.message;
      this.scrollToBottom();
    } else if (payload.status === "done") {
      this.setGeneratingState(false);
      if (this.activeResponseBubble) {
        const fullText = payload.full_text || this.activeResponseBubble.innerText;
        const msgEl = this.activeResponseBubble.closest(".message");
        if (msgEl) msgEl.dataset.rawText = fullText;
      }
      this.activeResponseBubble = null;
      this.loadTodayWorkspace();
    } else if (payload.status === "error") {
      this.setGeneratingState(false);
      if (this.activeResponseBubble) {
        this.activeResponseBubble.innerHTML += `<div class="error-badge">⚠️ ${payload.error}</div>`;
      }
    }
  }

  isGreetingTrigger(text) {
    if (!text) return false;
    const t = text.toLowerCase().trim();
    return (
      t.includes("personalized greeting and recap") ||
      t.includes("give me a personalized greeting") ||
      t.includes("give me a greeting") ||
      t === "personalized greeting & recap" ||
      t.startsWith("give me a personalized greeting")
    );
  }

  sendMessage(overrideText = null, hideUserBubble = false) {
    const text = (overrideText !== null ? overrideText : this.promptInput.value).trim();
    if (!text || this.isGenerating) return;

    if (this.aiEngine === "gemini_api" && !this.geminiApiKey) {
      this.openEngineSettingsModal();
      this.showToast("Please enter your free Gemini API key to chat.", "info");
      return;
    }

    if (!hideUserBubble && !this.isGreetingTrigger(text)) {
      this.addUserMessageBubble(text);
    }
    if (overrideText === null) {
      this.promptInput.value = "";
      this.promptInput.style.height = "auto";
    }

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        text: text,
        user_id: this.currentUserId,
        incognito: this.incognito,
        engine: this.aiEngine,
        api_key: this.geminiApiKey
      }));
    } else {
      this.showToast("Chat connection is offline. Reconnecting...", "error");
    }
  }

  // ---------------- WORKSPACE & CHECK-IN ---------------- //

  async loadTodayWorkspace() {
    try {
      const res = await fetch(`/api/workspace?user_id=${this.currentUserId}&date=${this.currentDate}`);
      const data = await res.json();
      const ws = data.workspace || {};
      const cards = data.reflection_cards || [];

      // Check-in status
      if (ws.mood) {
        document.querySelectorAll(".emoji-btn").forEach(b => {
          b.classList.toggle("active", b.dataset.mood === ws.mood);
        });
      }
      if (ws.energy) {
        document.querySelectorAll(".energy-btn").forEach(b => {
          b.classList.toggle("active", b.dataset.energy === ws.energy);
        });
      }

      // Reflection Card Snippet
      if (cards.length > 0) {
        const latest = cards[0];
        this.reflectionCardSnippet.textContent = `"${latest.what_i_want_to_remember || latest.balanced_perspective}"`;
        this.populateReflectionModal(latest);
      } else {
        this.reflectionCardSnippet.textContent = `No reflection card generated yet today.`;
      }

      // Diary snippet
      if (ws.diary_draft) {
        this.diaryDraftSnippet.textContent = ws.diary_draft.substring(0, 95) + "...";
        this.diaryTextarea.value = ws.diary_draft;
      } else {
        this.diaryDraftSnippet.textContent = `Your daily first-person journal draft will appear here.`;
      }

      // Load chat history or render dynamic personalized greeting
      const chatRes = await fetch(`/api/chat/history?user_id=${this.currentUserId}&date=${this.currentDate}`);
      const chatData = await chatRes.json();
      const history = chatData.history || [];

      this.chatContainer.innerHTML = "";

      if (history.length > 0) {
        history.forEach(m => {
          if (m.role === "user") {
            if (this.isGreetingTrigger(m.content)) {
              return; // Hide synthetic greeting command bubble
            }
            this.addUserMessageBubble(m.content, m.id);
          } else {
            const b = this.createCompanionMessageBubble(m.id);
            b.innerHTML = this.renderMarkdown(m.content);
            const msgEl = b.closest(".message");
            if (msgEl) msgEl.dataset.rawText = m.content;
          }
        });
        this.scrollToBottom();
      } else {
        await this.renderPersonalizedGreetingCard();
      }
    } catch (e) {
      console.error("Error loading today workspace:", e);
    }
  }

  async saveCheckin() {
    const activeMood = document.querySelector(".emoji-btn.active")?.dataset.mood || "Calm";
    const activeEnergy = document.querySelector(".energy-btn.active")?.dataset.energy || "Medium";

    try {
      this.checkinStatus.textContent = "Saving...";
      await fetch("/api/checkin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId, date: this.currentDate, mood: activeMood, energy: activeEnergy })
      });
      this.checkinStatus.textContent = "Saved";
      setTimeout(() => this.checkinStatus.textContent = "Saved", 1500);
    } catch (e) {
      this.checkinStatus.textContent = "Error";
    }
  }

  async generateReflectionCard() {
    this.showToast("Synthesizing Reflection Card from conversation...", "info");
    try {
      const res = await fetch("/api/synthesize/reflection-card", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId })
      });
      const data = await res.json();
      if (data.status === "success" && data.card) {
        this.populateReflectionModal(data.card);
        this.openModal(this.reflectionModal);
      }
    } catch (e) {
      alert("Failed to synthesize reflection card: " + e);
    }
  }

  populateReflectionModal(card) {
    document.getElementById("rcWhatHappened").value = card.what_happened || "";
    document.getElementById("rcWhatIFelt").value = card.what_i_felt || "";
    document.getElementById("rcWhatMattered").value = card.what_mattered || "";
    document.getElementById("rcBalancedPerspective").value = card.balanced_perspective || "";
    document.getElementById("rcNextStep").value = card.one_small_next_step || "";
    document.getElementById("rcWhatToRemember").value = card.what_i_want_to_remember || "";
  }

  async saveReflectionCard() {
    const cardData = {
      user_id: this.currentUserId,
      date: this.currentDate,
      what_happened: document.getElementById("rcWhatHappened").value,
      what_i_felt: document.getElementById("rcWhatIFelt").value,
      what_mattered: document.getElementById("rcWhatMattered").value,
      balanced_perspective: document.getElementById("rcBalancedPerspective").value,
      one_small_next_step: document.getElementById("rcNextStep").value,
      what_i_want_to_remember: document.getElementById("rcWhatToRemember").value
    };

    try {
      await fetch("/api/reflection-card", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cardData)
      });
      this.closeModal(this.reflectionModal);
      this.loadTodayWorkspace();
      this.showToast("Reflection Card saved to growth history!", "success");
    } catch (e) {
      alert("Failed to save reflection card.");
    }
  }

  async generateDiaryDraft() {
    this.showToast("Synthesizing diary entry in your voice...", "info");
    try {
      const res = await fetch("/api/synthesize/diary-draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId })
      });
      const data = await res.json();
      if (data.status === "success") {
        this.diaryTextarea.value = data.diary_draft;
        this.openModal(this.diaryModal);
      }
    } catch (e) {
      alert("Failed to generate diary: " + e);
    }
  }

  async saveDiaryDraft() {
    const text = this.diaryTextarea.value;
    try {
      await fetch("/api/diary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId, date: this.currentDate, diary_draft: text })
      });
      this.closeModal(this.diaryModal);
      this.loadTodayWorkspace();
      this.showToast("Diary draft saved!", "success");
    } catch (e) {
      alert("Failed to save diary.");
    }
  }

  async loadWorkspaceHistory() {
    this.openModal(this.historyModal);
    try {
      const res = await fetch(`/api/workspaces/history?user_id=${this.currentUserId}`);
      const data = await res.json();
      const workspaces = data.workspaces || [];
      this.historyContainer.innerHTML = "";

      if (workspaces.length === 0) {
        this.historyContainer.innerHTML = `<p class="empty-hint">No past workspaces recorded yet.</p>`;
        return;
      }

      workspaces.forEach(w => {
        const item = document.createElement("div");
        item.className = "history-card";
        item.innerHTML = `
          <div class="history-card-header">
            <h4>📅 ${w.date}</h4>
            <span class="badge">Mood: ${w.mood || "—"} | Energy: ${w.energy || "—"}</span>
          </div>
          <div class="history-card-body">
            <p>${w.diary_draft ? w.diary_draft.substring(0, 180) + "..." : "No diary saved for this day."}</p>
          </div>
        `;
        this.historyContainer.appendChild(item);
      });
    } catch (e) {
      console.error("Failed to load history", e);
    }
  }

  async loadAllWisdomLessons() {
    this.openModal(this.wisdomModal);
    try {
      const res = await fetch("/api/wisdom/catalog");
      const data = await res.json();
      const catalog = data.catalog || [];
      this.renderWisdomCards(catalog);
    } catch (e) {
      console.error("Failed to load wisdom catalog", e);
    }
  }

  async matchWisdomLessons() {
    this.openModal(this.wisdomModal);
    try {
      const lastUserMsg = Array.from(this.chatContainer.querySelectorAll(".user-message .bubble"))
        .map(el => el.innerText).pop() || "";
      
      const res = await fetch(`/api/wisdom/catalog`);
      const data = await res.json();
      this.renderWisdomCards(data.catalog || []);
    } catch (e) {
      console.error("Failed to match wisdom", e);
    }
  }

  renderWisdomCards(lessons) {
    this.wisdomCardsContainer.innerHTML = "";
    if (lessons.length === 0) {
      this.wisdomCardsContainer.innerHTML = "<p class='empty-hint'>No matching wisdom lessons found.</p>";
      return;
    }

    lessons.forEach(l => {
      const card = document.createElement("div");
      card.className = "wisdom-card";
      card.innerHTML = `
        <div class="wisdom-header">
          <span class="wisdom-topic">${l.topic}</span>
          <span class="wisdom-author">📖 ${l.author_source}</span>
        </div>
        <h3 class="wisdom-title">${l.title}</h3>
        <p class="wisdom-summary">${l.concept_summary}</p>
        <div class="wisdom-practice">
          <strong>⚡ 2-Minute Practice:</strong>
          <span>${l.micro_practice}</span>
        </div>
        <div class="wisdom-actions">
          <button class="btn-save-wisdom" data-id="${l.id}">Bookmark in Personal Library</button>
        </div>
      `;
      card.querySelector(".btn-save-wisdom").addEventListener("click", () => this.saveWisdomToLibrary(l));
      this.wisdomCardsContainer.appendChild(card);
    });
  }

  async saveWisdomToLibrary(lesson) {
    try {
      await fetch("/api/wisdom/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: this.currentUserId,
          wisdom_id: lesson.id,
          title: lesson.title,
          author_source: lesson.author_source,
          topic: lesson.topic,
          concept_summary: lesson.concept_summary,
          micro_practice: lesson.micro_practice,
          user_note: "Bookmarked from guided session."
        })
      });
      this.showToast(`Saved "${lesson.title}" to Personal Library!`, "success");
    } catch (e) {
      alert("Failed to bookmark wisdom.");
    }
  }

  // ---------------- DOM & UI UTILITIES ---------------- //

  toggleSidebar(forceState = null) {
    if (forceState !== null) {
      this.sidebarCollapsed = forceState;
    } else {
      this.sidebarCollapsed = !this.sidebarCollapsed;
    }
    localStorage.setItem("omni_sidebar_collapsed", this.sidebarCollapsed);
    this.applySidebarState();
  }

  applySidebarState() {
    if (!this.appContainer) {
      this.appContainer = document.querySelector(".app-container");
    }
    if (this.appContainer) {
      if (this.sidebarCollapsed) {
        this.appContainer.classList.add("sidebar-collapsed");
      } else {
        this.appContainer.classList.remove("sidebar-collapsed");
      }
    }
  }

  renderMarkdown(text) {
    if (!text) return "";
    try {
      if (typeof marked !== "undefined" && marked.parse) {
        return marked.parse(text);
      }
    } catch (e) {
      console.warn("Marked parse error:", e);
    }
    return text.replace(/\n/g, "<br>");
  }

  addUserMessageBubble(text, messageId = null) {
    const msg = document.createElement("div");
    msg.className = "message user-message";
    if (messageId) msg.dataset.id = messageId;
    msg.dataset.rawText = text;

    msg.innerHTML = `
      <div class="message-wrapper">
        <div class="bubble">${text}</div>
        <div class="msg-actions-bar">
          <button class="msg-action-btn btn-copy" title="Copy message text">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            <span>Copy</span>
          </button>
          <button class="msg-action-btn btn-retry" title="Edit & Re-send prompt">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>
            <span>Retry</span>
          </button>
          <button class="msg-action-btn btn-delete" title="Delete message">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            <span>Delete</span>
          </button>
        </div>
      </div>
    `;

    msg.querySelector(".btn-copy").addEventListener("click", (e) => this.handleCopyMessage(e.currentTarget, text));
    msg.querySelector(".btn-retry").addEventListener("click", () => this.handleRetryUserMessage(text));
    msg.querySelector(".btn-delete").addEventListener("click", () => this.handleDeleteMessage(msg, messageId));

    this.chatContainer.appendChild(msg);
    this.scrollToBottom();
    return msg;
  }

  createCompanionMessageBubble(messageId = null) {
    const msg = document.createElement("div");
    msg.className = "message companion-message";
    if (messageId) msg.dataset.id = messageId;

    msg.innerHTML = `
      <div class="avatar">✦</div>
      <div class="message-wrapper">
        <div class="bubble"></div>
        <div class="msg-actions-bar">
          <button class="msg-action-btn btn-copy" title="Copy response markdown">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            <span>Copy</span>
          </button>
          <button class="msg-action-btn btn-retry" title="Regenerate response">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>
            <span>Regenerate</span>
          </button>
          <button class="msg-action-btn btn-speak" title="Read aloud">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
            <span>Listen</span>
          </button>
          <button class="msg-action-btn btn-delete" title="Delete response">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            <span>Delete</span>
          </button>
        </div>
      </div>
    `;

    const bubble = msg.querySelector(".bubble");
    msg.querySelector(".btn-copy").addEventListener("click", (e) => this.handleCopyMessage(e.currentTarget, msg.dataset.rawText || bubble.innerText));
    msg.querySelector(".btn-retry").addEventListener("click", () => this.handleRegenerateCompanionMessage(msg));
    msg.querySelector(".btn-speak").addEventListener("click", () => this.speakText(msg.dataset.rawText || bubble.innerText));
    msg.querySelector(".btn-delete").addEventListener("click", () => this.handleDeleteMessage(msg, messageId));

    this.chatContainer.appendChild(msg);
    return bubble;
  }

  async handleCopyMessage(btn, text) {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      const originalHtml = btn.innerHTML;
      btn.classList.add("copied");
      btn.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <span>Copied!</span>
      `;
      this.showToast("Message copied to clipboard!", "success");
      setTimeout(() => {
        btn.classList.remove("copied");
        btn.innerHTML = originalHtml;
      }, 1800);
    } catch (err) {
      this.showToast("Failed to copy text.", "error");
    }
  }

  handleRetryUserMessage(text) {
    this.promptInput.value = text;
    this.promptInput.focus();
    this.promptInput.style.height = "auto";
    this.promptInput.style.height = Math.min(this.promptInput.scrollHeight, 140) + "px";
    this.showToast("Prompt loaded into input. Press Enter to re-send.", "info");
  }

  handleRegenerateCompanionMessage(companionMsgEl) {
    let prevEl = companionMsgEl.previousElementSibling;
    let userText = "";
    while (prevEl) {
      if (prevEl.classList.contains("user-message")) {
        userText = prevEl.dataset.rawText || prevEl.querySelector(".bubble")?.innerText || "";
        break;
      }
      prevEl = prevEl.previousElementSibling;
    }
    if (!userText) {
      userText = this.promptInput.value.trim();
    }
    if (userText) {
      this.showToast("Regenerating response from Omni...", "info");
      this.sendMessage(userText);
    } else {
      this.showToast("No prompt found to regenerate.", "info");
    }
  }

  async handleDeleteMessage(msgEl, messageId) {
    if (!confirm("Are you sure you want to delete this message?")) return;
    msgEl.style.opacity = "0";
    msgEl.style.transform = "scale(0.95)";
    setTimeout(() => msgEl.remove(), 250);

    if (messageId) {
      try {
        await fetch(`/api/chat/messages/${messageId}?user_id=${this.currentUserId}`, { method: "DELETE" });
      } catch (e) {
        console.error("Failed to delete message from database", e);
      }
    }
    this.showToast("Message deleted.", "info");
  }

  async renderPersonalizedGreetingCard() {
    try {
      const res = await fetch(`/api/companion/greeting?user_id=${this.currentUserId}`);
      const data = await res.json();
      const markdown = data.greeting_markdown || "Good to see you back. What's on your mind today?";
      const starters = data.starters || [];

      const msg = document.createElement("div");
      msg.className = "message companion-message greeting-message";
      
      let startersHtml = "";
      if (starters.length > 0) {
        startersHtml = `
          <div class="greeting-starters">
            ${starters.map((s, idx) => `
              <button class="starter-chip ${idx === 0 ? 'starter-highlight' : ''}" data-text="${s.text}">
                ${s.label}
              </button>
            `).join("")}
          </div>
        `;
      }

      msg.innerHTML = `
        <div class="avatar">✦</div>
        <div class="message-wrapper">
          <div class="bubble">
            ${this.renderMarkdown(markdown)}
            ${startersHtml}
          </div>
          <div class="msg-actions-bar">
            <button class="msg-action-btn btn-copy" title="Copy greeting text">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              <span>Copy</span>
            </button>
            <button class="msg-action-btn btn-speak" title="Read aloud">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
              <span>Listen</span>
            </button>
          </div>
        </div>
      `;

      msg.dataset.rawText = markdown;
      msg.querySelector(".btn-copy").addEventListener("click", (e) => this.handleCopyMessage(e.currentTarget, markdown));
      msg.querySelector(".btn-speak").addEventListener("click", () => this.speakText(markdown));

      // Attach starter chip click handlers
      msg.querySelectorAll(".starter-chip").forEach(chip => {
        chip.addEventListener("click", (e) => {
          const text = e.currentTarget.dataset.text;
          if (text) {
            this.sendMessage(text);
          }
        });
      });

      this.chatContainer.appendChild(msg);
      this.scrollToBottom();
    } catch (e) {
      console.error("Error loading personalized greeting:", e);
    }
  }

  async startNewDailySession() {
    try {
      this.showToast("Starting fresh session with Omni...", "info");
      await fetch("/api/session/new", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.currentUserId })
      });
      
      this.chatContainer.innerHTML = "";
      await this.renderPersonalizedGreetingCard();
      this.showToast("✨ Fresh daily session started.", "success");
    } catch (e) {
      console.error("Error starting new session:", e);
      this.showToast("Could not start new session.", "error");
    }
  }

  setGeneratingState(isGen) {
    this.isGenerating = isGen;
    this.sendBtn.disabled = isGen;
    this.sendBtn.style.opacity = isGen ? "0.5" : "1.0";
  }

  scrollToBottom() {
    this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
  }

  openModal(modal) {
    modal.classList.add("active");
  }

  closeModal(modal) {
    modal.classList.remove("active");
  }

  showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    this.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("fade-out");
      setTimeout(() => toast.remove(), 400);
    }, 3500);
  }

  copyCardText() {
    const what = document.getElementById("rcWhatHappened").value;
    const felt = document.getElementById("rcWhatIFelt").value;
    const perspective = document.getElementById("rcBalancedPerspective").value;
    const step = document.getElementById("rcNextStep").value;
    const text = `Reflection Card:\n- What Happened: ${what}\n- What I Felt: ${felt}\n- Balanced Perspective: ${perspective}\n- Small Next Step: ${step}`;
    navigator.clipboard.writeText(text);
    this.showToast("Reflection Card copied to clipboard!", "success");
  }

  copyDiaryText() {
    navigator.clipboard.writeText(this.diaryTextarea.value);
    this.showToast("Diary text copied to clipboard!", "success");
  }

  async connectChrome() {
    this.statusText.textContent = "Connecting...";
    try {
      const res = await fetch("/api/connect", { method: "POST" });
      const data = await res.json();
      if (data.status === "success") {
        this.checkBridgeStatus();
      } else {
        alert(data.message || "Failed to launch Chrome.");
      }
    } catch (e) {
      alert("Error connecting to Chrome.");
    }
  }

  updateEngineBadgeUI() {
    if (!this.engineBadgeText) return;
    if (this.aiEngine === "gemini_web") {
      this.engineBadgeIcon.textContent = "🌐";
      this.engineBadgeText.textContent = "Gemini Web (CDP)";
      if (this.btnConnect) this.btnConnect.style.display = "inline-flex";
    } else {
      this.engineBadgeIcon.textContent = "⚡";
      this.engineBadgeText.textContent = this.geminiApiKey ? "Gemini API (Ready)" : "Gemini API (Set Key)";
      if (this.btnConnect) this.btnConnect.style.display = "none";
    }
  }

  openEngineSettingsModal() {
    if (this.isLocal) {
      if (this.hostStatusBanner) this.hostStatusBanner.className = "host-status-banner host-local";
      if (this.hostStatusText) this.hostStatusText.textContent = "📍 Localhost detected (127.0.0.1) — Gemini Web (Chrome CDP) & Gemini API available.";
      if (this.radioEngineWeb) this.radioEngineWeb.disabled = false;
      if (this.cardEngineWeb) this.cardEngineWeb.classList.remove("disabled");
      if (this.tagEngineWeb) this.tagEngineWeb.textContent = "Localhost Ready";
    } else {
      if (this.hostStatusBanner) this.hostStatusBanner.className = "host-status-banner host-cloud";
      if (this.hostStatusText) this.hostStatusText.textContent = "📍 Cloud Public Domain detected — Gemini API (BYOK) enabled for remote visitors.";
      if (this.radioEngineWeb) this.radioEngineWeb.disabled = true;
      if (this.cardEngineWeb) this.cardEngineWeb.classList.add("disabled");
      if (this.tagEngineWeb) this.tagEngineWeb.textContent = "Localhost Only";
    }

    if (this.aiEngine === "gemini_web" && this.isLocal) {
      if (this.radioEngineWeb) this.radioEngineWeb.checked = true;
      this.cardEngineWeb?.classList.add("active");
      this.cardEngineApi?.classList.remove("active");
    } else {
      if (this.radioEngineApi) this.radioEngineApi.checked = true;
      this.cardEngineApi?.classList.add("active");
      this.cardEngineWeb?.classList.remove("active");
    }

    if (this.geminiApiKeyInput) this.geminiApiKeyInput.value = this.geminiApiKey || "";
    if (this.keyValidationFeedback) {
      this.keyValidationFeedback.textContent = "";
      this.keyValidationFeedback.className = "key-validation-feedback";
    }
    this.openModal(this.engineSettingsModal);
  }

  async handleValidateApiKey() {
    const key = this.geminiApiKeyInput.value.trim();
    if (!key) {
      this.keyValidationFeedback.textContent = "Please enter an API key to test.";
      this.keyValidationFeedback.className = "key-validation-feedback error";
      return;
    }

    this.btnValidateKey.disabled = true;
    this.btnValidateKey.textContent = "Testing...";
    this.keyValidationFeedback.textContent = "Validating with Google Gemini API...";
    this.keyValidationFeedback.className = "key-validation-feedback info";

    try {
      const res = await fetch("/api/settings/validate-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key })
      });
      const data = await res.json();
      if (data.valid) {
        this.keyValidationFeedback.textContent = "✅ API Key Valid! Connected to Google Gemini.";
        this.keyValidationFeedback.className = "key-validation-feedback success";
      } else {
        this.keyValidationFeedback.textContent = `❌ ${data.message || "Invalid API key"}`;
        this.keyValidationFeedback.className = "key-validation-feedback error";
      }
    } catch (e) {
      this.keyValidationFeedback.textContent = "Validation request failed.";
      this.keyValidationFeedback.className = "key-validation-feedback error";
    } finally {
      this.btnValidateKey.disabled = false;
      this.btnValidateKey.textContent = "Test Key";
    }
  }

  handleSaveEngineSettings() {
    const selectedRadio = document.querySelector('input[name="aiEngineRadio"]:checked');
    const chosenEngine = selectedRadio ? selectedRadio.value : "gemini_api";
    const apiKey = this.geminiApiKeyInput.value.trim();

    if (chosenEngine === "gemini_api" && !apiKey) {
      if (!confirm("No API key entered. You won't be able to chat in Gemini API mode until an API key is saved. Proceed anyway?")) {
        return;
      }
    }

    this.aiEngine = chosenEngine;
    this.geminiApiKey = apiKey;
    localStorage.setItem("omni_ai_engine", this.aiEngine);
    localStorage.setItem("omni_gemini_api_key", this.geminiApiKey);

    this.updateEngineBadgeUI();
    this.closeModal(this.engineSettingsModal);
    this.showToast(`AI Engine set to: ${chosenEngine === "gemini_web" ? "Gemini Web (CDP)" : "Gemini API (BYOK)"}`, "success");
  }

  async checkBridgeStatus() {
    if (this.aiEngine === "gemini_api") {
      if (this.geminiApiKey) {
        this.statusDot.className = "status-dot connected";
        this.statusText.textContent = "Gemini API Ready";
      } else {
        this.statusDot.className = "status-dot waiting";
        this.statusText.textContent = "Set API Key (⚙️)";
      }
      return;
    }

    try {
      const res = await fetch(`/api/status?user_id=${this.currentUserId}`);
      const data = await res.json();
      const bridge = data.bridge || {};
      if (bridge.connected && bridge.logged_in) {
        this.statusDot.className = "status-dot connected";
        this.statusText.textContent = "Gemini Ready";
      } else if (bridge.connected) {
        this.statusDot.className = "status-dot waiting";
        this.statusText.textContent = "Sign in to Gemini";
      } else {
        this.statusDot.className = "status-dot disconnected";
        this.statusText.textContent = "Connect Gemini";
      }
    } catch (e) {
      this.statusDot.className = "status-dot disconnected";
      this.statusText.textContent = "Bridge Offline";
    }
  }

  async startNewDailySession() {
    if (confirm("Start a clean session for today?")) {
      await fetch(`/api/session/new?user_id=${this.currentUserId}`, { method: "POST" });
      this.chatContainer.innerHTML = `
        <div class="message companion-message arrival-message">
          <div class="avatar">✦</div>
          <div class="bubble">
            <div class="arrival-header">
              <h2>How are you arriving today, ${this.resolveSalutationName(this.currentUser?.display_name)}?</h2>
              <p>Fresh session initialized. I remember your core preferences and growth journey.</p>
            </div>
          </div>
        </div>
      `;
      this.showToast("Fresh session started.", "info");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  window.app = new LifeCompanionApp();
});

