const TOTAL_DAYS = 10;
const TURN_SECONDS = 60;
const state = {
  roomId: null,
  data: null,
  pollId: null,
  timerId: null,
  secondsLeft: TURN_SECONDS,
  modalOpen: false,
  finalShown: false,
  quantities: {
    tnv: 1,
    olc: 1,
    hgn: 1,
  },
};

function formatCoins(value) {
  return Math.round(value || 0).toLocaleString('ru-RU');
}

function directionText(dir) {
  if (dir === 'up') return '⬆️ рост';
  if (dir === 'down') return '⬇️ падение';
  return '➡️ нейтрально';
}

function makeSpark(history) {
  const values = Array.isArray(history) && history.length ? history.slice(0, TOTAL_DAYS) : [100];
  if (values.length === 1) return ['0,50', '100,50'];
  const max = Math.max(...values);
  const min = Math.min(...values);
  const pad = Math.max(1, (max - min) * 0.1);
  const top = max + pad;
  const bottom = min - pad;
  const range = top - bottom || 1;
  return values.map((value, idx) => {
    const x = (idx / (values.length - 1)) * 100;
    const y = 100 - ((value - bottom) / range) * 100;
    return `${x},${y}`;
  });
}

function infoBadge(info) {
  if (!info) return { label: '—', className: '' };
  if (info.type === 'news') {
    return { label: `📰 Новость: ${directionText(info.direction)}`, className: 'badge news' };
  }
  return { label: `📢 Слух: ${directionText(info.direction)}`, className: info.truth ? 'badge rumor-true' : 'badge rumor-false' };
}

async function api(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  let data = null;
  try {
    data = JSON.parse(text);
  } catch (error) {
    throw new Error(text || 'Сервер вернул не JSON');
  }
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || 'Ошибка сервера');
  }
  return data;
}

function setGameVisible(visible) {
  const topbar = document.querySelector('.topbar');
  const stats = document.querySelector('.stats');
  const news = document.querySelector('.news');
  const bottom = document.querySelector('.bottom');
  const value = visible ? '' : 'none';
  if (topbar) topbar.style.display = value;
  if (stats) stats.style.display = value;
  if (news) news.style.display = value;
  if (bottom) bottom.style.display = value;
}

function startTimer() {
  stopTimer();
  state.timerId = setInterval(() => {
    if (!state.data) return;
    if (state.data.room.status !== 'playing') return;
    if (state.secondsLeft > 0) {
      state.secondsLeft -= 1;
    }
    renderTimer();
  }, 1000);
}

function stopTimer() {
  if (state.timerId) clearInterval(state.timerId);
  state.timerId = null;
}

function renderTimer() {
  const timerLabel = document.getElementById('timerLabel');
  if (!timerLabel) return;
  const mm = String(Math.floor(state.secondsLeft / 60)).padStart(2, '0');
  const ss = String(state.secondsLeft % 60).padStart(2, '0');
  timerLabel.textContent = `${mm}:${ss} до конца хода`;
}

function showModal(modal) {
  const modalRoot = document.getElementById('modalRoot');
  if (!modalRoot) return;
  modalRoot.innerHTML = '';
  state.modalOpen = true;
  const overlay = document.createElement('div');
  overlay.className = 'modal';
  const card = document.createElement('div');
  card.className = 'modal-card';
  if (modal.tone === 'warn') card.classList.add('warn');
  if (modal.tone === 'danger') card.classList.add('danger');
  const title = document.createElement('h4');
  title.textContent = modal.title;
  const body = document.createElement('div');
  body.className = 'modal-body';
  body.textContent = modal.body;
  card.appendChild(title);
  card.appendChild(body);
  if (modal.button !== false) {
    const btn = document.createElement('button');
    btn.className = 'btn';
    btn.textContent = modal.buttonText || 'OK';
    btn.onclick = () => {
      modalRoot.innerHTML = '';
      state.modalOpen = false;
      if (modal.onClose) modal.onClose();
    };
    card.appendChild(btn);
  }
  overlay.appendChild(card);
  modalRoot.appendChild(overlay);
}

function clearModal() {
  const modalRoot = document.getElementById('modalRoot');
  if (modalRoot) modalRoot.innerHTML = '';
  state.modalOpen = false;
}

function stopPolling() {
  if (state.pollId) clearInterval(state.pollId);
  state.pollId = null;
}

async function acknowledgeEvent() {
  try {
    const data = await api(`/api/rooms/${state.roomId}/events/ack`, {
      method: 'POST',
    });
    state.data = data;
    state.secondsLeft = data.room.turn_seconds_left || 0;
    render();
  } catch (error) {
    alert(error.message);
  }
}

function checkModal() {
  if (!state.data) return;
  const room = state.data.room;
  if (room.status === 'waiting') {
    showModal({
      title: 'Ожидание игроков',
      body: `Игроков ${room.players_count}/${room.max_players}. Игра начнётся, когда все войдут в комнату`,
      button: false,
      tone: 'warn',
    });
    return;
  }
  if (state.data.event) {
    showModal({
      title: state.data.event.title,
      body: state.data.event.body,
      tone: state.data.event.tone,
      onClose: acknowledgeEvent,
    });
    return;
  }
  if (room.status === 'finished' && !state.finalShown) {
    state.finalShown = true;
    stopTimer();
    stopPolling();
    const winner = state.data.ranking[0] ? state.data.ranking[0].name : 'Игрок';
    showModal({
      title: 'Итог игры',
      body: `Победитель: ${winner}`,
      tone: 'warn',
      onClose: () => {
        window.location.href = 'lobby.html';
      },
    });
    return;
  }
  clearModal();
}

function renderRanking() {
  const ranking = document.getElementById('ranking');
  if (!ranking) return;
  ranking.innerHTML = '';
  const me = state.data.me;
  state.data.ranking.forEach((item) => {
    const li = document.createElement('li');
    if (item.name === me.username) li.className = 'you';
    li.innerHTML = `<span>${item.name}</span><span>${formatCoins(item.capital)}</span>`;
    ranking.appendChild(li);
  });
}

function renderCompanies() {
  const cards = document.getElementById('cards');
  if (!cards) return;
  cards.innerHTML = '';
  const me = state.data.me;
  const room = state.data.room;
  state.data.companies.forEach((company) => {
    const badge = infoBadge(company.info);
    const spark = makeSpark(company.history);
    const hint = me.insider_hints[company.id];
    const card = document.createElement('div');
    card.className = 'card';
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
        <polyline points="${spark.join(' ')}" fill="none" stroke="#1f1f1f" stroke-width="3" />
        <line x1="0" y1="95" x2="100" y2="95" stroke="#111" stroke-width="2" />
      </svg>
    `; // Шаблон HTML карточки
    const actions = document.createElement('div');
    actions.className = 'actions';
    const actionLocked = !!me.day_actions[company.id] || me.finished_day || room.status !== 'playing';
    const buyBtn = document.createElement('button');
    buyBtn.className = 'btn buy';
    buyBtn.textContent = 'Купить';
    buyBtn.disabled = actionLocked;
    buyBtn.onclick = () => buy(company.id);
    const sellBtn = document.createElement('button');
    sellBtn.className = 'btn sell';
    sellBtn.textContent = 'Продать';
    sellBtn.disabled = actionLocked;
    sellBtn.onclick = () => sell(company.id);
    actions.appendChild(buyBtn);
    actions.appendChild(sellBtn);
    const insiderBtn = document.createElement('button');
    insiderBtn.className = 'btn insider';
    insiderBtn.textContent = '💎 Инсайд 50м';
    insiderBtn.disabled = me.insider_used || me.finished_day || room.status !== 'playing';
    insiderBtn.onclick = () => buyInsider(company.id);
    const insiderInfo = document.createElement('div');
    insiderInfo.className = 'insider-info';
    insiderInfo.textContent = hint ? `Инсайд: завтра реальная стоимость — ${directionText(hint)}` : '';
    const qty = document.createElement('div');
    qty.className = 'qty';
    qty.innerHTML = `
      <span>Количество акций:</span>
      <div class="qty-controls">
        <button data-up="${company.id}">▲</button>
        <div data-value="${company.id}">${state.quantities[company.id] || 1}</div>
        <button data-down="${company.id}">▼</button>
      </div>
    `; // Шаблон количества
    const upBtn = qty.querySelector(`[data-up="${company.id}"]`);
    const downBtn = qty.querySelector(`[data-down="${company.id}"]`);
    const valueEl = qty.querySelector(`[data-value="${company.id}"]`);
    upBtn.onclick = () => {
      state.quantities[company.id] += 1;
      valueEl.textContent = String(state.quantities[company.id]);
    };
    downBtn.onclick = () => {
      state.quantities[company.id] = Math.max(0, state.quantities[company.id] - 1);
      valueEl.textContent = String(state.quantities[company.id]);
    };
    if (actionLocked) {
      upBtn.disabled = true;
      downBtn.disabled = true;
    }
    const count = me.holdings[company.id] || 0;
    const holdings = document.createElement('div');
    holdings.className = 'holdings';
    holdings.textContent = `У вас: ${count} шт (${formatCoins(count * company.price)} м)`;
    card.appendChild(actions);
    card.appendChild(insiderBtn);
    card.appendChild(insiderInfo);
    card.appendChild(qty);
    card.appendChild(holdings);
    cards.appendChild(card);
  });
}

function render() {
  if (!state.data) return;
  const room = state.data.room;
  const me = state.data.me;
  setGameVisible(room.status !== 'waiting');
  const dayLabel = document.getElementById('dayLabel');
  const balanceLabel = document.getElementById('balanceLabel');
  const capitalLabel = document.getElementById('capitalLabel');
  const youCapital = document.getElementById('youCapital');
  const riskFill = document.getElementById('riskFill');
  const riskLabel = document.getElementById('riskLabel');
  const endDayBtn = document.getElementById('endDayBtn');
  if (dayLabel) dayLabel.textContent = `день ${room.current_day}/${TOTAL_DAYS}`;
  if (balanceLabel) balanceLabel.textContent = `баланс: ${formatCoins(me.cash)} монет`;
  if (capitalLabel) capitalLabel.textContent = `капитал: ${formatCoins(me.capital)} монет`;
  if (youCapital) youCapital.textContent = formatCoins(me.capital);
  if (riskFill) riskFill.style.width = `${me.risk}%`;
  if (riskLabel) riskLabel.textContent = `${me.risk}%`;
  state.secondsLeft = room.turn_seconds_left || 0;
  renderTimer();
  renderCompanies();
  renderRanking();
  if (endDayBtn) {
    endDayBtn.disabled = room.status !== 'playing' || me.finished_day;
    endDayBtn.textContent = me.finished_day ? 'ожидание остальных' : 'завершить день';
  }
  checkModal();
}

async function loadState() {
  try {
    const data = await api(`/api/rooms/${state.roomId}/state`);
    state.data = data;
    state.secondsLeft = data.room.turn_seconds_left || 0;
    render();
  } catch (error) {
    alert(error.message);
    window.location.href = 'lobby.html';
  }
}

function startPolling() {
  if (state.pollId) clearInterval(state.pollId);
  state.pollId = setInterval(loadState, 2000);
}

async function buy(companyId) {
  try {
    const qty = state.quantities[companyId] || 0;
    const data = await api(`/api/rooms/${state.roomId}/trade`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company_id: companyId, action: 'buy', qty }),
    });
    state.data = data;
    render();
  } catch (error) {
    alert(error.message);
  }
}

async function sell(companyId) {
  try {
    const qty = state.quantities[companyId] || 0;
    const data = await api(`/api/rooms/${state.roomId}/trade`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company_id: companyId, action: 'sell', qty }),
    });
    state.data = data;
    render();
  } catch (error) {
    alert(error.message);
  }
}

async function buyInsider(companyId) {
  try {
    const data = await api(`/api/rooms/${state.roomId}/insider`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company_id: companyId }),
    });
    state.data = data;
    render();
  } catch (error) {
    alert(error.message);
  }
}

async function endDay() {
  try {
    const data = await api(`/api/rooms/${state.roomId}/finish-day`, {
      method: 'POST',
    });
    state.data = data;
    state.secondsLeft = data.room.turn_seconds_left || 0;
    render();
  } catch (error) {
    alert(error.message);
  }
}

async function init() {
  try {
    const meData = await api('/api/me');
    state.roomId = meData.user.current_room_id;
    if (!state.roomId) {
      window.location.href = 'lobby.html';
      return;
    }
    document.getElementById('endDayBtn').onclick = endDay;
    startTimer();
    startPolling();
    await loadState();
  } catch (error) {
    window.location.href = 'auth.html';
  }
}
init();
