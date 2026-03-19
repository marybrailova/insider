const regBtn = document.getElementById("regBtn");
const regName = document.getElementById("regName");
const regPass = document.getElementById("regPass");
const regMsg = document.getElementById("regMsg");
const loginBtn = document.getElementById("loginBtn");
const loginName = document.getElementById("loginName");
const loginPass = document.getElementById("loginPass");
const loginMsg = document.getElementById("loginMsg");

function baseUrl() {
  if (window.location.protocol === "http:" || window.location.protocol === "https:") {
    return window.location.origin;
  }
  return "http://127.0.0.1:5001";
}

function apiUrl(path) {
  return `${baseUrl()}${path}`;
}

function pageUrl(path) {
  return `${baseUrl()}${path}`;
}

async function readJson(response) {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(text || "Сервер вернул не JSON");
  }
}

if (regBtn) {
  regBtn.onclick = async () => {
    const username = regName.value.trim();
    const password = regPass.value;
    try {
      const res = await fetch(apiUrl("/api/register"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ username, password })
      });
      const data = await readJson(res);
      regMsg.textContent = data.ok ? "Успешно" : (data.error || "Ошибка");
    } catch (error) {
      regMsg.textContent = "Сервер недоступен";
    }
  };
}

if (loginBtn) {
  loginBtn.onclick = async () => {
    const username = loginName.value.trim();
    const password = loginPass.value;
    try {
      const res = await fetch(apiUrl("/api/login"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ username, password })
      });
      const data = await readJson(res);
      if (data.ok) {
        loginMsg.textContent = "Вход выполнен";
        window.location.href = pageUrl("/lobby.html");
      } else {
        loginMsg.textContent = data.error || "Ошибка";
      }
    } catch (error) {
      loginMsg.textContent = "Сервер недоступен";
    }
  };
}
