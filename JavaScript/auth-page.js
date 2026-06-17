// ЭЛЕМЕНТЫ РЕГИСТРАЦИИ
const regBtn = document.getElementById("regBtn")
const regName = document.getElementById("regName")
const regPass = document.getElementById("regPass")
const regMsg = document.getElementById("regMsg")


// ЭЛЕМЕНТЫ ВХОДА
const loginBtn = document.getElementById("loginBtn")
const loginName = document.getElementById("loginName")
const loginPass = document.getElementById("loginPass")
const loginMsg = document.getElementById("loginMsg")


// РЕГИСТРАЦИЯ
regBtn.onclick = async function () {
  try {
    // отправляем данные регистрации
    const res = await fetch("/api/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: regName.value,
        password: regPass.value,
      }),
    })

    const data = await res.json()

    // переходим в лобби или показываем ошибку
    if (data.ok) {
      window.location.href = "lobby.html"
    } else {
      regMsg.textContent = data.error
    }
  } catch {
    regMsg.textContent = "Ошибка сервера"
  }
}


// ВХОД
loginBtn.onclick = async function () {
  try {
    // отправляем данные входа
    const res = await fetch("/api/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: loginName.value,
        password: loginPass.value,
      }),
    })

    const data = await res.json()

    // переходим в лобби или показываем ошибку
    if (data.ok) {
      window.location.href = "lobby.html"
    } else {
      loginMsg.textContent = data.error
    }
  } catch {
    loginMsg.textContent = "Ошибка сервера"
  }
}