// количество игровых дней
const TOTAL_DAYS = 10

// длительность дня в секундах
const TURN_SECONDS = 60


// id текущей комнаты
let roomId = null

// последнее состояние игры с сервера
let data = null

// таймер обновления состояния
let pollId = null

// таймер обратного отсчёта
let timerId = null

// сколько секунд осталось до конца дня
let secondsLeft = TURN_SECONDS

// показывали ли уже финальное окно
let finalShown = false


// выбранное количество акций для покупки/продажи
let quantities = {
  tnv: 1,
  olc: 1,
  hgn: 1,
}


// красивый вывод монет
function formatCoins(value) {
  return Math.round(value || 0).toLocaleString("ru-RU")
}


// текст направления
function directionText(dir) {
  if (dir === "up") return "⬆️ рост"
  if (dir === "down") return "⬇️ падение"
  return "➡️ нейтрально"
}


// строим точки для мини-графика цены
function makeSpark(history) {
  let values = history || [100]

  if (values.length === 1) {
    return ["0,50", "100,50"]
  }

  let max = Math.max(...values)
  let min = Math.min(...values)
  let range = max - min

  if (range === 0) {
    range = 1
  }

  let points = []

  for (let i = 0; i < values.length; i++) {
    let x = (i / (values.length - 1)) * 100
    let y = 100 - ((values[i] - min) / range) * 100

    points.push(x + "," + y)
  }

  return points
}


// подпись новости или слуха
function infoBadge(info) {
  if (!info) {
    return { label: "—", className: "" }
  }

  if (info.type === "news") {
    return {
      label: "📰 Новость: " + directionText(info.direction),
      className: "badge news",
    }
  }

  if (info.truth) {
    return {
      label: "📢 Слух: " + directionText(info.direction),
      className: "badge rumor-true",
    }
  }

  return {
    label: "📢 Слух: " + directionText(info.direction),
    className: "badge rumor-false",
  }
}


// универсальный запрос к серверу
async function api(url, options) {
  let response = await fetch(url, options)
  let answer = await response.json()

  if (!response.ok || answer.ok === false) {
    throw new Error(answer.error || "Ошибка сервера")
  }

  return answer
}


// скрываем игру, пока комната ждёт игроков
function setGameVisible(visible) {
  let value = "none"

  if (visible) {
    value = ""
  }

  document.querySelector(".topbar").style.display = value
  document.querySelector(".stats").style.display = value
  document.querySelector(".news").style.display = value
  document.querySelector(".bottom").style.display = value
}


// запускаем локальный таймер
function startTimer() {
  if (timerId) {
    clearInterval(timerId)
  }

  timerId = setInterval(function () {
    if (data && data.room.status === "playing") {
      if (secondsLeft > 0) {
        secondsLeft--
      }

      renderTimer()
    }
  }, 1000)
}


// рисуем таймер
function renderTimer() {
  let mm = String(Math.floor(secondsLeft / 60)).padStart(2, "0")
  let ss = String(secondsLeft % 60).padStart(2, "0")

  document.getElementById("timerLabel").textContent =
    mm + ":" + ss + " до конца хода"
}


// показываем модальное окно
function showModal(title, body, button, tone, onClose) {
  let modalRoot = document.getElementById("modalRoot")

  modalRoot.innerHTML = ""

  let overlay = document.createElement("div")
  let card = document.createElement("div")
  let h = document.createElement("h4")
  let text = document.createElement("div")

  overlay.className = "modal"
  card.className = "modal-card"
  text.className = "modal-body"

  if (tone) {
    card.classList.add(tone)
  }

  h.textContent = title
  text.textContent = body

  card.appendChild(h)
  card.appendChild(text)

  // если нужна кнопка OK
  if (button !== false) {
    let btn = document.createElement("button")

    btn.className = "btn"
    btn.textContent = "OK"

    btn.onclick = function () {
      modalRoot.innerHTML = ""

      if (onClose) {
        onClose()
      }
    }

    card.appendChild(btn)
  }

  overlay.appendChild(card)
  modalRoot.appendChild(overlay)
}


// останавливаем таймеры
function stopAll() {
  if (timerId) {
    clearInterval(timerId)
  }

  if (pollId) {
    clearInterval(pollId)
  }
}


// подтверждаем событие игрока
async function acknowledgeEvent() {
  try {
    data = await api("/api/rooms/" + roomId + "/events/ack", {
      method: "POST",
    })

    secondsLeft = data.room.turn_seconds_left || 0

    render()

  } catch (error) {
    alert(error.message)
  }
}


// проверяем, нужно ли показать модальное окно
function checkModal() {
  let room = data.room

  // ожидание игроков
  if (room.status === "waiting") {
    showModal(
      "Ожидание игроков",
      "Игроков " + room.players_count + "/" + room.max_players +
        ". Игра начнётся, когда все войдут в комнату",
      false,
      "warn",
    )

    return
  }

  // событие игрока
  if (data.event) {
    showModal(
      data.event.title,
      data.event.body,
      true,
      data.event.tone,
      acknowledgeEvent,
    )

    return
  }

  // финал игры
  if (room.status === "finished" && !finalShown) {
    finalShown = true

    stopAll()

    let winner = "Игрок"

    if (data.ranking[0]) {
      winner = data.ranking[0].name
    }

    showModal(
      "Итог игры",
      "Победитель: " + winner,
      true,
      "warn",
      function () {
        window.location.href = "results.html"
      },
    )

    return
  }

  // если ничего показывать не надо
  document.getElementById("modalRoot").innerHTML = ""
}


// рисуем рейтинг игроков
function renderRanking() {
  let ranking = document.getElementById("ranking")

  ranking.innerHTML = ""

  for (let i = 0; i < data.ranking.length; i++) {
    let item = data.ranking[i]
    let li = document.createElement("li")

    if (item.name === data.me.username) {
      li.className = "you"
    }

    li.innerHTML =
      "<span>" + item.name + "</span><span>" +
      formatCoins(item.capital) + "</span>"

    ranking.appendChild(li)
  }
}


// рисуем карточки компаний
function renderCompanies() {
  let cards = document.getElementById("cards")

  cards.innerHTML = ""

  for (let i = 0; i < data.companies.length; i++) {
    let company = data.companies[i]

    let badge = infoBadge(company.info)
    let spark = makeSpark(company.history)
    let hint = data.me.insider_hints[company.id]

    // блокировка кнопок, если действие уже сделано
    let locked =
      data.me.day_actions[company.id] ||
      data.me.finished_day ||
      data.room.status !== "playing"

    let card = document.createElement("div")
    card.className = "card"

    card.innerHTML = `
      <div class="card-head">
        <div class="company">
          <div class="company-icon">${company.icon}</div>
          <div>
            <div class="company-name">${company.name}</div>
            <div class="company-ticker">${company.ticker}</div>
          </div>
        </div>
        <div class="sector">${company.sector}</div>
      </div>

      <div class="${badge.className}">${badge.label}</div>
      <div class="price">${formatCoins(company.price)} монет</div>

      <svg viewBox="0 0 100 100" class="spark">
        <polyline points="${spark.join(" ")}" fill="none" stroke="#1f1f1f" stroke-width="3" />
        <line x1="0" y1="95" x2="100" y2="95" stroke="#111" stroke-width="2" />
      </svg>

      <div class="actions">
        <button class="btn buy" id="buy-${company.id}">Купить</button>
        <button class="btn sell" id="sell-${company.id}">Продать</button>
      </div>

      <button class="btn insider" id="insider-${company.id}">💎 Инсайд 50м</button>

      <div class="insider-info">${hint ? "Инсайд: " + directionText(hint) : ""}</div>

      <div class="qty">
        <span>Количество акций:</span>
        <div class="qty-controls">
          <button id="up-${company.id}">▲</button>
          <div id="value-${company.id}">${quantities[company.id]}</div>
          <button id="down-${company.id}">▼</button>
        </div>
      </div>

      <div class="holdings">
        У вас: ${data.me.holdings[company.id] || 0} шт
        (${formatCoins((data.me.holdings[company.id] || 0) * company.price)} м)
      </div>
    `

    cards.appendChild(card)

    // кнопка купить
    document.getElementById("buy-" + company.id).onclick = function () {
      buy(company.id)
    }

    // кнопка продать
    document.getElementById("sell-" + company.id).onclick = function () {
      sell(company.id)
    }

    // кнопка инсайда
    document.getElementById("insider-" + company.id).onclick = function () {
      buyInsider(company.id)
    }

    // увеличить количество
    document.getElementById("up-" + company.id).onclick = function () {
      quantities[company.id]++

      document.getElementById("value-" + company.id).textContent =
        quantities[company.id]
    }

    // уменьшить количество
    document.getElementById("down-" + company.id).onclick = function () {
      if (quantities[company.id] > 0) {
        quantities[company.id]--
      }

      document.getElementById("value-" + company.id).textContent =
        quantities[company.id]
    }

    // блокируем кнопки, если нельзя ходить
    document.getElementById("buy-" + company.id).disabled = locked
    document.getElementById("sell-" + company.id).disabled = locked
    document.getElementById("up-" + company.id).disabled = locked
    document.getElementById("down-" + company.id).disabled = locked

    document.getElementById("insider-" + company.id).disabled =
      data.me.insider_used ||
      data.me.finished_day ||
      data.room.status !== "playing"
  }
}


// полная перерисовка страницы
function render() {
  let room = data.room
  let me = data.me

  // если ждём игроков — скрываем игру
  setGameVisible(room.status !== "waiting")

  document.getElementById("dayLabel").textContent =
    "день " + room.current_day + "/" + TOTAL_DAYS

  document.getElementById("balanceLabel").textContent =
    "баланс: " + formatCoins(me.cash) + " монет"

  document.getElementById("capitalLabel").textContent =
    "капитал: " + formatCoins(me.capital) + " монет"

  document.getElementById("riskFill").style.width = me.risk + "%"

  document.getElementById("riskLabel").textContent = me.risk + "%"

  secondsLeft = room.turn_seconds_left || 0

  renderTimer()
  renderCompanies()
  renderRanking()

  let endDayBtn = document.getElementById("endDayBtn")

  endDayBtn.disabled =
    room.status !== "playing" ||
    me.finished_day

  if (me.finished_day) {
    endDayBtn.textContent = "ожидание остальных"
  } else {
    endDayBtn.textContent = "завершить день"
  }

  checkModal()
}


// загрузка состояния игры с сервера
async function loadState() {
  try {
    data = await api("/api/rooms/" + roomId + "/state")

    secondsLeft = data.room.turn_seconds_left || 0

    render()

  } catch (error) {
    alert(error.message)

    window.location.href = "lobby.html"
  }
}


// купить акции
async function buy(companyId) {
  try {
    data = await api("/api/rooms/" + roomId + "/trade", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        company_id: companyId,
        action: "buy",
        qty: quantities[companyId],
        current_day: data.room.current_day,
      }),
    })

    render()

  } catch (error) {
    alert(error.message)
  }
}


// продать акции
async function sell(companyId) {
  try {
    data = await api("/api/rooms/" + roomId + "/trade", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        company_id: companyId,
        action: "sell",
        qty: quantities[companyId],
        current_day: data.room.current_day,
      }),
    })

    render()

  } catch (error) {
    alert(error.message)
  }
}


// купить инсайд
async function buyInsider(companyId) {
  try {
    data = await api("/api/rooms/" + roomId + "/insider", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        company_id: companyId,
        current_day: data.room.current_day,
      }),
    })

    render()

  } catch (error) {
    alert(error.message)
  }
}


// завершить день
async function endDay() {
  try {
    data = await api("/api/rooms/" + roomId + "/finish-day", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        current_day: data.room.current_day,
      }),
    })

    secondsLeft = data.room.turn_seconds_left || 0

    render()

  } catch (error) {
    alert(error.message)
  }
}


// запуск страницы игры
async function init() {
  try {

    // узнаём текущего пользователя
    let me = await api("/api/me")

    // берём id комнаты из session
    roomId = me.user.current_room_id

    // если комнаты нет — возвращаемся в лобби
    if (!roomId) {
      window.location.href = "lobby.html"
      return
    }

    // кнопка завершения дня
    document.getElementById("endDayBtn").onclick = endDay

    // запускаем таймер
    startTimer()

    // раз в 2 секунды обновляем состояние
    pollId = setInterval(loadState, 2000)

    // первая загрузка состояния
    await loadState()

  } catch (error) {

    // если пользователь не вошёл
    window.location.href = "auth.html"
  }
}


init()
