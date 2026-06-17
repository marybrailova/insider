// ЦВЕТА ГРАФИКА
const COLORS = ["#8ecae6", "#ffb3c1", "#b7e4c7", "#cdb4db", "#ffd6a5"]


// формат монет
function money(value) {
  return Math.round(value || 0).toLocaleString("ru-RU")
}


// запрос к серверу
async function api(url) {
  const response = await fetch(url)
  const data = await response.json()

  // проверяем ошибку
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "Ошибка")
  }

  return data
}


// подписи дней
function labels(count) {
  const result = ["Старт"]

  // добавляем игровые дни
  for (let i = 1; i < count; i++) {
    result.push("День " + i)
  }

  return result
}


// рисуем график
function drawChart(players) {
  let maxDays = 0

  // создаём линии игроков
  const datasets = players.map(function (player, index) {
    const history = player.capital_history || [2000, player.capital]

    if (history.length > maxDays) {
      maxDays = history.length
    }

    return {
      label: player.name,
      data: history,
      borderColor: COLORS[index % COLORS.length],
      backgroundColor: COLORS[index % COLORS.length],
      borderWidth: 3,
      tension: 0.25,
    }
  })

  // создаём график
  new Chart(document.getElementById("capitalChart"), {
    type: "line",
    data: {
      labels: labels(maxDays),
      datasets: datasets,
    },
  })
}


// рисуем рейтинг
function drawRating(players) {
  const root = document.getElementById("rating")

  root.innerHTML = ""

  // создаём строки игроков
  players.forEach(function (player, index) {
    const row = document.createElement("div")

    row.className = "row"

    row.innerHTML = `
      <div class="place">${index + 1}</div>
      <div class="name">${player.name}</div>
      <div class="capital">${money(player.capital)} монет</div>
    `

    root.appendChild(row)
  })
}


// загрузка итогов
async function init() {
  // получаем пользователя
  const me = await api("/api/me")

  // получаем состояние игры
  const state = await api(
    "/api/rooms/" + me.user.current_room_id + "/state",
  )

  const players = state.ranking

  // выводим график и рейтинг
  drawChart(players)
  drawRating(players)
}


// запускаем страницу
init().catch(function () {
  document.body.innerHTML = "Не удалось загрузить итоги игры"
})