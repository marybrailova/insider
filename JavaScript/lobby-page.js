// поля для создания комнаты
const roomTitle = document.getElementById("roomTitle")
const roomType = document.getElementById("roomType")
const roomMaxPlayers = document.getElementById("roomMaxPlayers")

// кнопка создания комнаты и сообщение
const createRoomBtn = document.getElementById("createRoomBtn")
const createRoomMsg = document.getElementById("createRoomMsg")

// поле для кода комнаты
const joinCode = document.getElementById("joinCode")
const joinByCodeBtn = document.getElementById("joinByCodeBtn")
const joinCodeMsg = document.getElementById("joinCodeMsg")

// список публичных комнат
const roomsList = document.getElementById("roomsList")


// загрузка списка комнат
async function loadRooms() {
  try {

    // получаем комнаты с сервера
    const res = await fetch("/api/rooms")
    const data = await res.json()

    roomsList.innerHTML = ""

    // проходим по всем комнатам
    for (let i = 0; i < data.rooms.length; i++) {
      const room = data.rooms[i]

      // показываем только публичные комнаты
      if (room.room_type !== "public") {
        continue
      }

      // создаём карточку комнаты
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

      // кнопка входа в комнату
      const btn = document.createElement("button")
      btn.className = "btn"
      btn.textContent = "войти"

      btn.onclick = async function () {

        // запрос на вход в публичную комнату
        const res = await fetch("/api/rooms/" + room.id + "/join", {
          method: "POST",
        })

        const data = await res.json()

        if (data.ok) {

          // если вошли — открываем игру
          window.location.href = "game.html"

        } else {

          // если ошибка — показываем сообщение
          createRoomMsg.textContent = data.error
        }
      }

      card.appendChild(btn)
      roomsList.appendChild(card)
    }

    // если публичных комнат нет
    if (roomsList.innerHTML === "") {
      const card = document.createElement("div")

      card.className = "card"
      card.textContent = "Пока нет публичных игр"

      roomsList.appendChild(card)
    }

  } catch {

    // если сервер недоступен
    roomsList.innerHTML = "Не удалось загрузить игры"
  }
}


// создание новой комнаты
createRoomBtn.onclick = async function () {
  try {

    // отправляем данные комнаты на сервер
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

      // если комната приватная — показываем код
      if (data.room_type === "private") {
        createRoomMsg.textContent = "Код: " + data.code

      } else {

        // если публичная — просто сообщаем о создании
        createRoomMsg.textContent = "Публичная комната создана"
      }

      // обновляем список комнат
      loadRooms()

    } else {

      // ошибка создания комнаты
      createRoomMsg.textContent = data.error
    }

  } catch {

    // ошибка сервера
    createRoomMsg.textContent = "Сервер недоступен"
  }
}


// вход в приватную комнату по коду
joinByCodeBtn.onclick = async function () {
  try {

    // отправляем код комнаты на сервер
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

      // если вошли — открываем игру
      window.location.href = "game.html"

    } else {

      // ошибка входа
      joinCodeMsg.textContent = data.error
    }

  } catch {

    // ошибка сервера
    joinCodeMsg.textContent = "Сервер недоступен"
  }
}


// первая загрузка комнат
loadRooms()

// обновляем список комнат каждые 3 секунды
setInterval(loadRooms, 3000)