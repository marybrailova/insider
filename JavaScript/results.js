// цвета линий игроков на графике
const COLORS = ["#8ecae6", "#ffb3c1", "#b7e4c7", "#cdb4db", "#ffd6a5"]

// превращает число в сумму с разделителями
function money(value) {
  return Math.round(value || 0).toLocaleString("ru-RU")
}

// отправляет запрос на backend и возвращает json
async function api(url) {
  const response = await fetch(url)
  const data = await response.json()

  // если backend вернул ошибку, останавливаем загрузку
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "Ошибка")
  }

  return data
}

// создаёт подписи дней для графика
function labels(count) {
  // первая точка показывает капитал до начала игры
  const result = ["Старт"]

  // добавляем подпись для каждого игрового дня
  for (let i = 1; i < count; i++) {
    result.push("День " + i)
  }

  return result
}

// рисует график изменения капитала игроков
function drawChart(players) {
  let maxDays = 0

  // для каждого игрока создаём отдельную линию графика
  const datasets = players.map(function (player, index) {
    // если история пустая, используем стартовый и текущий капитал
    const history = player.capital_history || [2000, player.capital]

    // запоминаем самое большое количество дней
    if (history.length > maxDays) {
      maxDays = history.length
    }

    // настройки линии одного игрока
    return {
      label: player.name,
      data: history,
      borderColor: COLORS[index % COLORS.length],
      backgroundColor: COLORS[index % COLORS.length],
      borderWidth: 3,
      tension: 0.25,
    }
  })

  // создаём линейный график через библиотеку chart.js
  new Chart(document.getElementById("capitalChart"), {
    type: "line",
    data: {
      labels: labels(maxDays),
      datasets: datasets,
    },
  })
}

// выводит итоговый рейтинг игроков
function drawRating(players) {
  // получаем блок рейтинга из results.html
  const root = document.getElementById("rating")
  // очищаем старые строки перед выводом
  root.innerHTML = ""

  // создаём строку для каждого игрока
  players.forEach(function (player, index) {
    const row = document.createElement("div")
    row.className = "row"
    // добавляем место, имя и итоговый капитал
    row.innerHTML = `
      <div class="place">${index + 1}</div>
      <div class="name">${player.name}</div>
      <div class="capital">${money(player.capital)} монет</div>
    `
    // добавляем готовую строку на страницу
    root.appendChild(row)
  })
}

// загружает данные текущей игры и показывает результаты
async function init() {
  // получаем текущего пользователя и его комнату
  const me = await api("/api/me")
  // получаем состояние завершённой игры
  const state = await api("/api/rooms/" + me.user.current_room_id + "/state")
  const players = state.ranking

  // рисуем график и рейтинг
  drawChart(players)
  drawRating(players)
}

// запускаем загрузку итогов после открытия страницы
init().catch(function () {
  // показываем сообщение, если backend не ответил
  document.body.innerHTML = "Не удалось загрузить итоги игры"
})
