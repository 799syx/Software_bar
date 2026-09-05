const DEFAULT_API_BASE = location.protocol.startsWith("http") ? location.origin : "http://127.0.0.1:8000";
const params = new URLSearchParams(location.search);
const API_BASE = (params.get("api") || localStorage.getItem("lingshan_mobile_api") || DEFAULT_API_BASE).replace(/\/$/, "");

const SPOT_IMAGE_OVERRIDES = [
  ["灵山大照壁", "/assets/scenic/photos/lingshan-screen-wall.jpg"],
  ["五明桥", "/assets/scenic/photos/five-brightness-bridge.png"],
  ["佛足坛", "/assets/scenic/photos/buddha-foot-altar.png"],
  ["五智门", "/assets/scenic/photos/five-wisdom-gate.jpg"],
  ["菩提大道", "/assets/scenic/photos/bodhi-avenue.png"],
  ["降魔浮雕", "/assets/scenic/photos/demon-subduing-relief.png"],
  ["阿育王柱", "/assets/scenic/photos/ashoka-pillar.png"],
  ["百子戏弥勒", "/assets/scenic/photos/children-mitreya.png"],
  ["百子弥勒戏", "/assets/scenic/photos/children-mitreya.png"],
  ["佛教文化博览馆", "/assets/scenic/photos/buddhist-culture-museum.jpg"],
  ["佛教文化博物馆", "/assets/scenic/photos/buddhist-culture-museum.jpg"],
  ["梵天花海", "/assets/scenic/photos/brahma-flower-sea.png"],
  ["曼飞龙塔", "/assets/scenic/photos/manfeilong-pagoda.png"],
  ["无尽意斋", "/assets/scenic/photos/wujinyi-zhai.png"],
  ["拈花广场", "/assets/scenic/photos/nianhua-plaza.png"],
  ["拈花堂", "/assets/scenic/photos/nianhua-hall.png"]
];

const FALLBACK_SPOTS = [
  {
    id: 1,
    name: "灵山大佛",
    description: "景区核心地标，适合登顶礼佛、俯瞰太湖并了解佛教造像艺术。",
    tags: ["地标", "文化", "拍照"],
    duration: 60,
    location: "灵山胜境核心区",
    image: "/assets/scenic/photos/lingshan-grand-buddha.jpg"
  },
  {
    id: 2,
    name: "九龙灌浴",
    description: "动态音乐喷泉与佛教典故结合，是亲子游客常问的演艺点位。",
    tags: ["演艺", "亲子"],
    duration: 30,
    location: "菩提大道北端",
    image: "/assets/scenic/photos/nine-dragons-bath.jpg"
  },
  {
    id: 3,
    name: "灵山梵宫",
    description: "以佛教文化艺术和大型室内空间见长，适合避雨、观演和深度讲解。",
    tags: ["建筑", "演艺", "室内"],
    duration: 50,
    location: "灵山大佛南侧",
    image: "/assets/scenic/photos/brahma-palace.jpg"
  },
  {
    id: 4,
    name: "五印坛城",
    description: "藏传佛教艺术风格鲜明，适合拍照和了解不同佛教文化表达。",
    tags: ["文化", "拍照"],
    duration: 35,
    location: "景区东侧",
    image: "/assets/scenic/photos/five-seal-mandala.jpg"
  }
];

const state = {
  spots: loadCache("mobile_spots") || FALLBACK_SPOTS,
  suggestions: ["灵山大佛有什么特色？", "九龙灌浴什么时候表演？", "适合亲子游的路线怎么走？"],
  routeOptions: { durations: [60, 120, 180, 240], preferences: ["佛教文化", "亲子游", "拍照打卡", "轻松休闲"] },
  selectedSpotId: null,
  selectedImageData: "",
  speechRecognition: null,
  listening: false
};

const el = {
  personaName: document.querySelector("#personaName"),
  serviceStatus: document.querySelector("#serviceStatus"),
  spotPhoto: document.querySelector("#spotPhoto"),
  spotZone: document.querySelector("#spotZone"),
  spotName: document.querySelector("#spotName"),
  spotMeta: document.querySelector("#spotMeta"),
  spotDescription: document.querySelector("#spotDescription"),
  spotTags: document.querySelector("#spotTags"),
  spotList: document.querySelector("#spotList"),
  speakSpotButton: document.querySelector("#speakSpotButton"),
  locateButton: document.querySelector("#locateButton"),
  chatMessages: document.querySelector("#chatMessages"),
  suggestions: document.querySelector("#suggestions"),
  chatForm: document.querySelector("#chatForm"),
  questionInput: document.querySelector("#questionInput"),
  voiceButton: document.querySelector("#voiceButton"),
  photoInput: document.querySelector("#photoInput"),
  photoPreview: document.querySelector("#photoPreview"),
  photoPlaceholder: document.querySelector("#photoPlaceholder"),
  photoQuestion: document.querySelector("#photoQuestion"),
  analyzePhotoButton: document.querySelector("#analyzePhotoButton"),
  photoAnswer: document.querySelector("#photoAnswer"),
  durationSelect: document.querySelector("#durationSelect"),
  preferenceSelect: document.querySelector("#preferenceSelect"),
  routeButton: document.querySelector("#routeButton"),
  routeResult: document.querySelector("#routeResult")
};

function loadCache(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "");
  } catch {
    return null;
  }
}

function saveCache(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage limits on kiosk browsers.
  }
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || `${path} 请求失败`);
  return data;
}

function selectedSpot() {
  return state.spots.find((spot) => spot.id === state.selectedSpotId) || state.spots[0] || FALLBACK_SPOTS[0];
}

function isLegacyPlaceholderImage(image) {
  return /^\/?assets\/spot-[\w-]+\.svg$/.test(image || "");
}

function imageForSpot(spot) {
  if (!spot) return "/assets/scenic/photos/lingshan-grand-buddha.jpg";
  if (spot.image && spot.image.startsWith("/") && !isLegacyPlaceholderImage(spot.image)) return spot.image;
  if (spot.image && spot.image.startsWith("assets/") && !isLegacyPlaceholderImage(spot.image)) return `/${spot.image}`;
  const name = spot.name || "";
  const override = SPOT_IMAGE_OVERRIDES.find(([keyword]) => name.includes(keyword));
  if (override) return override[1];
  if (name.includes("九龙")) return "/assets/scenic/photos/nine-dragons-bath.jpg";
  if (name.includes("梵宫")) return "/assets/scenic/photos/brahma-palace.jpg";
  if (name.includes("五印")) return "/assets/scenic/photos/five-seal-mandala.jpg";
  if (name.includes("拈花")) return "/assets/scenic/photos/nianhua-bay.jpg";
  return "/assets/scenic/photos/lingshan-grand-buddha.jpg";
}

function setStatus(mode, text, title = "") {
  el.serviceStatus.className = `service-pill ${mode}`;
  el.serviceStatus.textContent = text;
  el.serviceStatus.title = title || text;
}

function clearElement(element) {
  element.replaceChildren();
}

function appendText(parent, tagName, text, className = "") {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.appendChild(element);
  return element;
}

function createSpotSummary(spot, includeLocation = true) {
  const wrapper = document.createElement("span");
  const title = appendText(wrapper, "strong", spot.name || "景区点位");
  title.title = spot.name || "";
  const detailText = includeLocation
    ? `${spot.location || "景区点位"} · ${spot.duration || 30} 分钟`
    : `${spot.duration || 30} 分钟`;
  appendText(wrapper, "span", detailText);
  return wrapper;
}

function appendRouteStep(container, spot, index, includeLocation = true) {
  const step = document.createElement("div");
  step.className = "route-step";
  appendText(step, "b", String(index + 1));
  step.appendChild(createSpotSummary(spot, includeLocation));
  container.appendChild(step);
}

function renderSpot() {
  const spot = selectedSpot();
  el.spotPhoto.src = imageForSpot(spot);
  el.spotName.textContent = spot.name;
  el.spotZone.textContent = spot.location || "推荐景点";
  el.spotMeta.textContent = `建议游览 ${spot.duration || 30} 分钟`;
  el.spotDescription.textContent = spot.description || "暂无简介，可咨询景区工作人员。";
  clearElement(el.spotTags);
  (spot.tags || ["导览"]).slice(0, 5).forEach((tag) => {
    const chip = document.createElement("span");
    chip.textContent = tag;
    el.spotTags.appendChild(chip);
  });
  renderSpotList();
}

function renderSpotList() {
  clearElement(el.spotList);
  state.spots.slice(0, 16).forEach((spot) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `spot-item ${spot.id === selectedSpot().id ? "active" : ""}`;
    const image = document.createElement("img");
    image.src = imageForSpot(spot);
    image.alt = spot.name || "景区照片";
    button.appendChild(image);
    button.appendChild(createSpotSummary(spot));
    button.addEventListener("click", () => {
      state.selectedSpotId = spot.id;
      renderSpot();
      switchView("guide");
    });
    el.spotList.appendChild(button);
  });
}

function renderSuggestions() {
  clearElement(el.suggestions);
  state.suggestions.slice(0, 6).forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item;
    button.addEventListener("click", () => askQuestion(item));
    el.suggestions.appendChild(button);
  });
}

function renderRouteOptions() {
  clearElement(el.durationSelect);
  state.routeOptions.durations.forEach((duration) => {
    el.durationSelect.appendChild(new Option(`${duration} 分钟`, String(duration)));
  });
  clearElement(el.preferenceSelect);
  state.routeOptions.preferences.forEach((item) => {
    el.preferenceSelect.appendChild(new Option(item, item));
  });
  el.durationSelect.value = String(state.routeOptions.durations[1] || state.routeOptions.durations[0] || 120);
  el.preferenceSelect.value = state.routeOptions.preferences[0] || "佛教文化";
}

function addMessage(role, text, meta = "") {
  const item = document.createElement("article");
  item.className = `message ${role}`;
  const body = document.createElement("p");
  body.textContent = text;
  item.appendChild(body);
  if (meta) {
    const small = document.createElement("small");
    small.textContent = meta;
    item.appendChild(small);
  }
  el.chatMessages.appendChild(item);
  el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
  return body;
}

async function loadData() {
  renderSpot();
  renderSuggestions();
  renderRouteOptions();
  try {
    const [spots, persona, status, suggestions, routes] = await Promise.all([
      api("/api/spots"),
      api("/api/persona"),
      api("/api/llm/status"),
      api("/api/chat/suggestions"),
      api("/api/routes/options")
    ]);
    state.spots = spots.items && spots.items.length ? spots.items : state.spots;
    state.suggestions = suggestions.items && suggestions.items.length ? suggestions.items : state.suggestions;
    state.routeOptions = routes;
    saveCache("mobile_spots", state.spots);
    saveCache("mobile_suggestions", state.suggestions);
    el.personaName.textContent = persona.name || "AI 导览";
    const online = status.visionAvailable && status.visionMultimodal;
    setStatus(online ? "online" : "offline", online ? "在线千问" : "本地资料", online ? status.visionModel : status.reason);
  } catch {
    state.suggestions = loadCache("mobile_suggestions") || state.suggestions;
    setStatus("offline", "本地资料", "后端或公网不可达，当前使用缓存资料。");
  }
  renderSpot();
  renderSuggestions();
  renderRouteOptions();
}

function switchView(name) {
  document.querySelectorAll(".mobile-view").forEach((view) => view.classList.remove("active"));
  document.querySelector(`#${name}View`)?.classList.add("active");
  document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
}

async function askQuestion(text) {
  const question = String(text || el.questionInput.value || "").trim();
  if (!question) return;
  switchView("chat");
  el.questionInput.value = "";
  addMessage("user", question);
  const pending = addMessage("assistant", "正在查询景区资料。");
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ question })
    });
    pending.textContent = data.answer || "暂时没有查到明确答案，请咨询现场工作人员。";
    speak(pending.textContent);
  } catch (error) {
    const spot = selectedSpot();
    pending.textContent = `${spot.name}：${spot.description || "当前无公网，先使用本地景点资料。"} 如需票务、演出实时信息，请以景区公告为准。`;
  }
}

function speak(text) {
  if (!text || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = 0.96;
  window.speechSynthesis.speak(utterance);
}

function setupVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    el.voiceButton.disabled = true;
    el.voiceButton.textContent = "文字";
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = "zh-CN";
  recognition.interimResults = false;
  recognition.continuous = false;
  recognition.onstart = () => {
    state.listening = true;
    el.voiceButton.classList.add("active");
    el.voiceButton.textContent = "停止";
  };
  recognition.onend = () => {
    state.listening = false;
    el.voiceButton.classList.remove("active");
    el.voiceButton.textContent = "语音";
  };
  recognition.onresult = (event) => {
    const text = Array.from(event.results)
      .map((result) => result[0]?.transcript || "")
      .join("")
      .trim();
    if (text) el.questionInput.value = text;
  };
  state.speechRecognition = recognition;
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function handlePhoto(file) {
  if (!file) return;
  if (file.size > 4 * 1024 * 1024) {
    el.photoAnswer.hidden = false;
    el.photoAnswer.textContent = "图片超过 4MB，请压缩后再上传。";
    return;
  }
  state.selectedImageData = await fileToDataUrl(file);
  el.photoPreview.src = state.selectedImageData;
  el.photoPreview.hidden = false;
  el.photoPlaceholder.hidden = true;
}

async function analyzePhoto() {
  if (!state.selectedImageData) {
    el.photoAnswer.hidden = false;
    el.photoAnswer.textContent = "请先选择或拍摄一张景区照片。";
    return;
  }
  el.photoAnswer.hidden = false;
  el.photoAnswer.textContent = "正在识别照片。";
  try {
    const data = await api("/api/vision/analyze", {
      method: "POST",
      body: JSON.stringify({ image: state.selectedImageData, question: el.photoQuestion.value.trim() })
    });
    el.photoAnswer.textContent = data.answer || "暂时无法识别照片。";
    speak(el.photoAnswer.textContent);
  } catch (error) {
    el.photoAnswer.textContent = "当前视觉模型不可用。无网场景可先使用景点列表和文字问答，本地大模型部署后可恢复离线图片讲解。";
  }
}

async function buildRoute() {
  el.routeResult.textContent = "正在生成路线。";
  try {
    const data = await api("/api/routes/recommend", {
      method: "POST",
      body: JSON.stringify({ duration: Number(el.durationSelect.value), preference: el.preferenceSelect.value })
    });
    clearElement(el.routeResult);
    appendText(el.routeResult, "p", `${data.title || "推荐路线"}，预计 ${data.estimatedDuration || el.durationSelect.value} 分钟。`);
    (data.spots || []).forEach((spot, index) => {
      appendRouteStep(el.routeResult, spot, index);
    });
  } catch {
    const fallback = state.spots.slice(0, 4);
    clearElement(el.routeResult);
    appendText(el.routeResult, "p", "当前使用本地资料生成简化路线。");
    fallback.forEach((spot, index) => {
      appendRouteStep(el.routeResult, spot, index, false);
    });
  }
}

function locateNearby() {
  if (!navigator.geolocation) {
    addMessage("assistant", "当前设备不支持定位。可以在问答里描述你附近的建筑或上传现场照片。");
    switchView("chat");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      try {
        const data = await api(`/api/spots/nearby?lat=${position.coords.latitude}&lon=${position.coords.longitude}&limit=5`);
        if (data.items?.[0]) {
          state.selectedSpotId = data.items[0].id;
          renderSpot();
        }
        addMessage("assistant", `已根据 GPS 推荐附近景点，定位精度约 ${Math.round(position.coords.accuracy || 0)} 米。`);
      } catch {
        addMessage("assistant", "定位已获得，但后端暂不可用，先展示本地推荐景点。");
      }
      switchView("chat");
    },
    () => {
      addMessage("assistant", "没有获得定位权限。可以手动选择景点，或上传现场照片辅助判断位置。");
      switchView("chat");
    },
    { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }
  );
}

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

el.chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  askQuestion();
});

el.speakSpotButton.addEventListener("click", () => {
  const spot = selectedSpot();
  speak(`${spot.name}。${spot.description || ""}`);
});

el.locateButton.addEventListener("click", locateNearby);
el.routeButton.addEventListener("click", buildRoute);
el.analyzePhotoButton.addEventListener("click", analyzePhoto);
el.photoInput.addEventListener("change", () => handlePhoto(el.photoInput.files?.[0]));
el.voiceButton.addEventListener("click", () => {
  if (!state.speechRecognition) return;
  if (state.listening) state.speechRecognition.stop();
  else state.speechRecognition.start();
});

if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/mobile/sw.js", { scope: "/mobile/" }).catch(() => {});
  });
}

setupVoice();
loadData();
