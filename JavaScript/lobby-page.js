// ПОЛЯ СОЗДАНИЯ КОМНАТЫ
const roomTitle = document.getElementById("roomTitle")
const roomType = document.getElementById("roomType")
const roomMaxPlayers = document.getElementById("roomMaxPlayers")


// КНОПКА СОЗДАНИЯ КОМНАТЫ
const createRoomBtn = document.getElementById("createRoomBtn")
const createRoomMsg = document.getElementById("createRoomMsg")


// ВХОД ПО КОДУ
const joinCode = document.getElementById("joinCode")
const joinByCodeBtn = document.getElementById("joinByCodeBtn")
const joinCodeMsg = document.getElementById("joinCodeMsg")


// СПИСОК КОМНАТ
const roomsList = document.getElementById("roomsList")


// ЗАГРУЗКА КОМНАТ
async function loadRooms() {
  try {
    // получаем комнаты
    const res = await fetch("/api/rooms")
    const data = await res.json()

    roomsList.innerHTML = ""

    // выводим публичные комнаты
    for (let i = 0; i < data.rooms.length; i++) {
      const room = data.rooms[i]

      if (room.room_type !== "public") {
        continue
      }

      // создаём карточку
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

      // кнопка входа
      const btn = document.createElement("button")

      btn.className = "btn"
      btn.textContent = "войти"

      btn.onclick = async function () {
        // входим в комнату
        const res = await fetch("/api/rooms/" + room.id + "/join", {
          method: "POST",
        })

        const data = await res.json()

        if (data.ok) {
          window.location.href = "game.html"
        } else {
          createRoomMsg.textContent = data.error
        }
      }

      card.appendChild(btn)
      roomsList.appendChild(card)
    }

    // если комнат нет
    if (roomsList.innerHTML === "") {
      const card = document.createElement("div")

      card.className = "card"
      card.textContent = "Пока нет публичных игр"

      roomsList.appendChild(card)
    }
  } catch {
    roomsList.innerHTML = "Не удалось загрузить игры"
  }
}


// СОЗДАНИЕ КОМНАТЫ
createRoomBtn.onclick = async function () {
  try {
    // отправляем данные комнаты
    const res = await fetch("/api/rooms", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: roomTitle.value,
        max_players: roomMaxPlayers.value,
        room_type: roomType.value,
      }),
    })

    const data = await res.json()

    if (data.ok) {
      // показываем результат
      if (data.room_type === "private") {
        createRoomMsg.textContent = "Код: " + data.code
      } else {
        createRoomMsg.textContent = "Публичная комната создана"
      }

      // обновляем комнаты
      loadRooms()
    } else {
      createRoomMsg.textContent = data.error
    }
  } catch {
    createRoomMsg.textContent = "Сервер недоступен"
  }
}


// ВХОД ПО КОДУ
joinByCodeBtn.onclick = async function () {
  try {
    // отправляем код
    const res = await fetch("/api/rooms/join-by-code", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        code: joinCode.value,
      }),
    })

    const data = await res.json()

    if (data.ok) {
      window.location.href = "game.html"
    } else {
      joinCodeMsg.textContent = data.error
    }
  } catch {
    joinCodeMsg.textContent = "Сервер недоступен"
  }
}


// первая загрузка
loadRooms()

// автообновление комнат
setInterval(loadRooms, 3000)