// получаем кнопку регистрации по id из html
const regBtn = document.getElementById("regBtn")

// input поле для логина при регистрации
const regName = document.getElementById("regName")

// input поле для пароля
const regPass = document.getElementById("regPass")

// блок для вывода ошибок регистрации
const regMsg = document.getElementById("regMsg")



// кнопка входа в аккаунт
const loginBtn = document.getElementById("loginBtn")

// поле логина при входе
const loginName = document.getElementById("loginName")

// поле пароля при входе
const loginPass = document.getElementById("loginPass")

// блок вывода ошибок входа
const loginMsg = document.getElementById("loginMsg")



// 
// регистрация нового пользователя
// 

// onclick срабатывает при нажатии кнопки регистрации
regBtn.onclick = async function () {

  try {

    // fetch отправляет http запрос на backend
    // запрос идёт на flask маршрут /api/register
    const res = await fetch("/api/register", {

      // используем post потому что отправляем данные
      method: "POST",

      // сообщаем backend что отправляем json
      headers: {
        "Content-Type": "application/json",
      },

      // body содержит данные пользователя
      // JSON.stringify превращает js объект в json строку
      body: JSON.stringify({

        // логин пользователя из input поля
        username: regName.value,

        // пароль пользователя из input поля
        password: regPass.value,
      }),
    })


    // backend возвращает json ответ
    // { ok: true }
    // или
    // { ok: false, error: "пользователь уже существует" }

    const data = await res.json()


    // если регистрация успешна
    if (data.ok) {

      // автоматически переходим на страницу lobby.html
      // window.location.href меняет страницу браузера
      window.location.href = "lobby.html"

    } else {

      // если backend вернул ошибку
      // показываем её пользователю на странице
      regMsg.textContent = data.error
    }

  } catch {

    // catch срабатывает если
    // backend не отвечает
    // сервер выключен
    // произошла ошибка сети
    regMsg.textContent = "Ошибка сервера"
  }
}



// ======================================================
// вход существующего пользователя
// ======================================================

// onclick запускается при нажатии кнопки входа
loginBtn.onclick = async function () {

  try {

    // отправляем post запрос на backend
    // flask обрабатывает его через /api/login
    const res = await fetch("/api/login", {

      // метод отправки данных
      method: "POST",

      // тип данных json
      headers: {
        "Content-Type": "application/json",
      },

      // отправляем логин и пароль пользователя
      body: JSON.stringify({

        // логин из input поля
        username: loginName.value,

        // пароль из input поля
        password: loginPass.value,
      }),
    })


    // получаем json ответ backend
    const data = await res.json()


    // если логин и пароль правильные
    if (data.ok) {

      // переходим в игровое лобби
      window.location.href = "lobby.html"

    } else {

      // если backend вернул ошибку
      // например:
      // "неверный пароль"
      loginMsg.textContent = data.error
    }

  } catch {

    // ошибка соединения с backend
    // например сервер не запущен
    loginMsg.textContent = "Ошибка сервера"
  }
}