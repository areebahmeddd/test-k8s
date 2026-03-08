let API_BASE = localStorage.getItem("api_base") || "";
let accessToken = localStorage.getItem("access_token");
let refreshToken = localStorage.getItem("refresh_token");
let todos = [];
let clockInterval = null;

const QUOTES = [
  '"The secret of getting ahead is getting started." - Mark Twain',
  '"Well done is better than well said." - Benjamin Franklin',
  '"It always seems impossible until it\'s done." - Nelson Mandela',
  '"Focus on being productive instead of busy." - Tim Ferriss',
  '"Doing what you love is the cornerstone of having abundance in your life." - Wayne Dyer',
  '"Action is the foundational key to all success." - Pablo Picasso',
];

let currentQuoteIndex = Math.floor(Math.random() * QUOTES.length);

function setQuote() {
  $("quote").textContent = QUOTES[currentQuoteIndex];
}

function rotateQuote() {
  const el = $("quote");
  el.style.opacity = "0";
  setTimeout(() => {
    currentQuoteIndex = (currentQuoteIndex + 1) % QUOTES.length;
    el.textContent = QUOTES[currentQuoteIndex];
    el.style.opacity = "1";
  }, 500);
}

const $ = (id) => document.getElementById(id);
const val = (id) => $(id).value.trim();
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");
const toggle = (id, visible) => $(id).classList.toggle("hidden", !visible);
const err = (id, msg) => {
  $(id).textContent = msg;
};
const esc = (s) =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

function setLoading(id, loading) {
  $(id).disabled = loading;
  $(id).textContent = loading
    ? "Please wait…"
    : id === "login-btn"
      ? "Sign in"
      : "Create account";
}

document.addEventListener("DOMContentLoaded", () => {
  $("api-base-input").value = API_BASE;

  setQuote();
  setInterval(rotateQuote, 60000);

  $("login-username").addEventListener(
    "keydown",
    (e) => e.key === "Enter" && doLogin(),
  );
  $("login-password").addEventListener(
    "keydown",
    (e) => e.key === "Enter" && doLogin(),
  );
  $("reg-email").addEventListener(
    "keydown",
    (e) => e.key === "Enter" && doRegister(),
  );
  $("reg-username").addEventListener(
    "keydown",
    (e) => e.key === "Enter" && doRegister(),
  );
  $("reg-password").addEventListener(
    "keydown",
    (e) => e.key === "Enter" && doRegister(),
  );
  $("new-title").addEventListener(
    "keydown",
    (e) => e.key === "Enter" && doAdd(),
  );

  accessToken ? showApp() : showAuth();
});

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...opts.headers };
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  let res = await fetch(API_BASE + path, { ...opts, headers });

  if (res.status === 401 && refreshToken) {
    const ok = await tryRefresh();
    if (ok) {
      headers["Authorization"] = `Bearer ${accessToken}`;
      res = await fetch(API_BASE + path, { ...opts, headers });
    } else {
      clearTokens();
      showAuth();
      return res;
    }
  }
  return res;
}

async function tryRefresh() {
  try {
    const r = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (r.ok) {
      const d = await r.json();
      setTokens(d.access_token, d.refresh_token);
      return true;
    }
  } catch {}
  return false;
}

function setTokens(access, refresh) {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

function clearTokens() {
  accessToken = refreshToken = null;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

function showApp() {
  hide("auth-view");
  show("app-view");
  loadUser();
  loadTodos();
  updateClock();
  if (clockInterval) clearInterval(clockInterval);
  clockInterval = setInterval(updateClock, 1000);
}

function showAuth() {
  hide("app-view");
  show("auth-view");
}

function switchTab(tab) {
  const isLogin = tab === "login";
  $("tab-login").classList.toggle("active", isLogin);
  $("tab-register").classList.toggle("active", !isLogin);
  toggle("login-form", isLogin);
  toggle("register-form", !isLogin);
  err("login-err", "");
  err("register-err", "");
}

async function doLogin() {
  err("login-err", "");
  const username = val("login-username");
  const password = val("login-password");
  if (!username || !password)
    return err("login-err", "Please fill all fields.");

  setLoading("login-btn", true);
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username, password }),
    });
    if (res.ok) {
      const d = await res.json();
      setTokens(d.access_token, d.refresh_token);
      showApp();
    } else {
      const d = await res.json();
      err("login-err", d.detail || "Login failed.");
    }
  } catch {
    err("login-err", "Cannot reach server. Check API config.");
  } finally {
    setLoading("login-btn", false);
  }
}

async function doRegister() {
  err("register-err", "");
  const email = val("reg-email");
  const username = val("reg-username");
  const password = val("reg-password");
  if (!email || !username || !password)
    return err("register-err", "Please fill all fields.");

  setLoading("register-btn", true);
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password }),
    });
    if (res.ok) {
      $("login-username").value = username;
      $("login-password").value = password;
      switchTab("login");
      await doLogin();
    } else {
      const d = await res.json();
      err("register-err", d.detail || "Registration failed.");
    }
  } catch {
    err("register-err", "Cannot reach server. Check API config.");
  } finally {
    setLoading("register-btn", false);
  }
}

async function doLogout() {
  if (refreshToken) {
    await api("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {});
  }
  clearTokens();
  if (clockInterval) {
    clearInterval(clockInterval);
    clockInterval = null;
  }
  showAuth();
}

async function loadUser() {
  try {
    const res = await api("/api/v1/auth/me");
    if (res.ok) {
      const u = await res.json();
      $("welcome-text").textContent = `Welcome ${u.username}!`;
    }
  } catch {}
}

function updateClock() {
  const now = new Date();
  const day = now.toLocaleDateString("en-US", { weekday: "long" });
  const date = now.toLocaleDateString("en-US", {
    month: "long",
    day: "2-digit",
    year: "numeric",
  });
  const time = now.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  $("header-datetime").textContent = `${day}, ${date} | ${time}`;
}

async function loadTodos() {
  $("todos").innerHTML = '<div class="state-msg">Loading…</div>';
  err("todos-err", "");
  try {
    const res = await api("/api/v1/todos");
    if (res.ok) {
      todos = await res.json();
      render();
    } else {
      $("todos").innerHTML = "";
      err("todos-err", "Failed to load todos.");
    }
  } catch {
    $("todos").innerHTML = "";
    err("todos-err", "Connection error.");
  }
}

function render() {
  const el = $("todos");
  if (!todos.length) {
    el.innerHTML = '<div class="state-msg">No tasks yet. Add one above!</div>';
    updateFooter();
    return;
  }
  el.innerHTML = todos
    .map((t) => {
      const due = t.due_date
        ? new Date(t.due_date).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })
        : "";
      const hasMeta = t.description || due;
      return `
      <div class="todo-item pri-${t.priority} ${t.completed ? "done" : ""}">
        <input type="checkbox" class="todo-check"
          ${t.completed ? "checked" : ""}
          onchange="doToggle('${t.id}', this.checked)" />
        <div class="todo-body">
          <div class="todo-title">${esc(t.title)}</div>
          ${
            hasMeta
              ? `<div class="todo-meta">
            ${t.description ? `<span class="todo-desc">${esc(t.description)}</span>` : ""}
            ${due ? `<span class="todo-due">${due}</span>` : ""}
          </div>`
              : ""
          }
        </div>
        <button class="btn-del" onclick="doDelete('${t.id}')" title="Delete">×</button>
      </div>`;
    })
    .join("");
  updateFooter();
}

function updateFooter() {
  const n = todos.filter((t) => !t.completed).length;
  $("remaining").textContent = `Your remaining todos : ${n}`;
}

async function doAdd() {
  const titleEl = $("new-title");
  const title = titleEl.value.trim();
  if (!title) return;

  const body = {
    title,
    description: val("new-desc") || null,
    priority: $("new-priority").value,
    due_date: $("new-due").value
      ? new Date($("new-due").value).toISOString()
      : null,
  };

  err("todos-err", "");
  try {
    const res = await api("/api/v1/todos", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (res.ok) {
      todos.unshift(await res.json());
      titleEl.value = "";
      $("new-desc").value = "";
      $("new-due").value = "";
      $("new-priority").value = "medium";
      render();
    } else {
      const d = await res.json();
      err("todos-err", d.detail || "Failed to create task.");
    }
  } catch {
    err("todos-err", "Connection error.");
  }
}

async function doToggle(id, completed) {
  const idx = todos.findIndex((t) => t.id === id);
  if (idx < 0) return;
  const prev = todos[idx].completed;
  todos[idx].completed = completed;
  render();
  try {
    const res = await api(`/api/v1/todos/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ completed }),
    });
    if (res.ok) {
      todos[idx] = await res.json();
      render();
    } else {
      todos[idx].completed = prev;
      render();
      err("todos-err", "Update failed.");
    }
  } catch {
    todos[idx].completed = prev;
    render();
    err("todos-err", "Connection error.");
  }
}

async function doDelete(id) {
  const idx = todos.findIndex((t) => t.id === id);
  if (idx < 0) return;
  const [removed] = todos.splice(idx, 1);
  render();
  try {
    const res = await api(`/api/v1/todos/${id}`, { method: "DELETE" });
    if (!res.ok) {
      todos.splice(idx, 0, removed);
      render();
      err("todos-err", "Delete failed.");
    }
  } catch {
    todos.splice(idx, 0, removed);
    render();
    err("todos-err", "Connection error.");
  }
}

function toggleConfig() {
  $("config-panel").classList.toggle("hidden");
}

function saveApiBase() {
  const v = $("api-base-input").value.trim().replace(/\/$/, "");
  if (!v) return;
  API_BASE = v;
  localStorage.setItem("api_base", v);
  hide("config-panel");
}
