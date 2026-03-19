const roomTitle = document.getElementById("roomTitle")

const roomType = document.getElementById("roomType")

const roomMaxPlayers = document.getElementById("roomMaxPlayers")

const createRoomBtn = document.getElementById("createRoomBtn")

const createRoomMsg = document.getElementById("createRoomMsg")

const joinCode = document.getElementById("joinCode")

const joinByCodeBtn = document.getElementById("joinByCodeBtn")

const joinCodeMsg = document.getElementById("joinCodeMsg")

const roomsList = document.getElementById("roomsList")

function baseUrl() {
  if (window.location.protocol === "http:" || window.location.protocol === "https:") {
    return window.location.origin
  }
  return "http://127.0.0.1:5001"
}

function apiUrl(path) {
  return `${baseUrl()}${path}`
}

function pageUrl(path) {
  return `${baseUrl()}${path}`
}

async function readJson(response) {
  const text = await response.text()
  try {
    return JSON.parse(text)
  } catch (error) {
    throw new Error(text || "Сервер вернул не JSON")
  }
}

async function loadRooms() {
  if (!roomsList) return
  try {
    const res = await fetch(apiUrl("/api/rooms"))
    const data = await readJson(res)
    roomsList.innerHTML = ""
    const publicRooms = (data.rooms || []).filter((room) => room.room_type === "public")
    if (!data.ok || !publicRooms.length) {
      const card = document.createElement("div")
      card.className = "card"
      card.textContent = "Пока нет публичных игр"
      roomsList.appendChild(card)
      return
    }
    publicRooms.forEach((room) => {
      const card = document.createElement("div")
      card.className = "card"
      card.innerHTML = `
        <div class="company">
          <div class="company-icon">🌍</div>
          <div>
            <div class="company-name">${room.title}</div>
            <div class="company-ticker">${room.players_count}/${room.max_players} игроков</div>
          </div>
        </div>
      `
      const btn = document.createElement("button")
      btn.className = "btn"
      btn.textContent = "войти"
      btn.onclick = async () => {
        try {
          const res = await fetch(apiUrl(`/api/rooms/${room.id}/join`), {
            method: "POST",
          })
          const data = await readJson(res)
          if (data.ok) {
            window.location.href = pageUrl("/game.html")
          } else {
            createRoomMsg.textContent = data.error || "Не удалось войти"
          }
        } catch (error) {
          createRoomMsg.textContent = "Сервер недоступен"
        }
      }
      card.appendChild(btn)
      roomsList.appendChild(card)
    })
  } catch (error) {
    roomsList.innerHTML = ""
    const card = document.createElement("div")
    card.className = "card"
    card.textContent = "Не удалось загрузить игры"
    roomsList.appendChild(card)
  }
}

if (createRoomBtn) {
  createRoomBtn.onclick = async () => {
    const title = roomTitle.value.trim()
    const max_players = Number(roomMaxPlayers.value || 3)
    const selectedType = roomType.value
    try {
      const res = await fetch(apiUrl("/api/rooms"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, max_players, room_type: selectedType }),
      })
      const data = await readJson(res)
      if (data.ok) {
        if (data.room_type === "private") {
          createRoomMsg.textContent = `Код: ${data.code}`
        } else {
          createRoomMsg.textContent = "Публичная комната создана"
        }
        loadRooms()
      } else {
        createRoomMsg.textContent = data.error || "Не удалось создать игру"
      }
    } catch (error) {
      createRoomMsg.textContent = "Сервер недоступен"
    }
  }
}

if (joinByCodeBtn) {
  joinByCodeBtn.onclick = async () => {
    const code = joinCode.value.trim().toUpperCase()
    try {
      const res = await fetch(apiUrl("/api/rooms/join-by-code"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      })
      const data = await readJson(res)
      if (data.ok) {
        window.location.href = pageUrl("/game.html")
      } else {
        joinCodeMsg.textContent = data.error || "Не удалось войти"
      }
    } catch (error) {
      joinCodeMsg.textContent = "Сервер недоступен"
    }
  }
}
loadRooms()
setInterval(loadRooms, 3000)
