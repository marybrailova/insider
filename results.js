const COLORS = ["#8ecae6", "#ffb3c1", "#b7e4c7", "#cdb4db", "#ffd6a5"]

function money(value) {
  return Math.round(value || 0).toLocaleString("ru-RU")
}

async function api(url) {
  const response = await fetch(url)
  const data = await response.json()

  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "Ошибка")
  }

  return data
}

function labels(count) {
  const result = ["Старт"]

  for (let i = 1; i < count; i++) {
    result.push("День " + i)
  }

  return result
}

function drawChart(players) {
  let maxDays = 0
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

  new Chart(document.getElementById("capitalChart"), {
    type: "line",
    data: {
      labels: labels(maxDays),
      datasets: datasets,
    },
  })
}

function drawRating(players) {
  const root = document.getElementById("rating")
  root.innerHTML = ""

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

async function init() {
  const me = await api("/api/me")
  const state = await api("/api/rooms/" + me.user.current_room_id + "/state")
  const players = state.ranking

  drawChart(players)
  drawRating(players)
}

init().catch(function () {
  document.body.innerHTML = "Не удалось загрузить итоги игры"
})
