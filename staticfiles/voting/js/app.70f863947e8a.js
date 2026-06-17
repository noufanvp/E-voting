const state = {
  election: null,
  ballotId: null,
  sessionToken: null,
  votes: {},
  currentSectionIndex: 0,
};

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.content : '';
}

function jsonHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCsrfToken(),
  };
}

function setWaitingMode() {
  document.getElementById('waiting-screen').classList.remove('hidden');
  document.getElementById('voting-content').classList.add('hidden');
  document.getElementById('success-screen').classList.remove('active');
  document.getElementById('progress-fill').style.width = '0%';
  document.getElementById('progress-text').textContent = '0 of 0 positions voted';
  document.getElementById('progress-percent').textContent = '0%';
}

function setActiveVotingMode() {
  document.getElementById('waiting-screen').classList.add('hidden');
  document.getElementById('voting-content').classList.remove('hidden');
  document.getElementById('success-screen').classList.remove('active');
}

function blockBackNavigation() {
  history.pushState(null, document.title, location.href);
  window.addEventListener('popstate', () => {
    history.pushState(null, document.title, location.href);
  });
}

function countVotes() {
  return Object.keys(state.votes).length;
}

function cardColumns(count) {
  if (count <= 2) return 2;
  if (count <= 3) return 3;
  return 4;
}

function getInitials(name) {
  return name.split(' ').slice(0, 2).map((w) => w[0]).join('').toUpperCase();
}

function getAvatarColor(id) {
  return `av-${id % 8}`;
}

function updateProgress() {
  const total = state.election.positions.length;
  const done = countVotes();
  const percent = total ? Math.round((done / total) * 100) : 0;

  document.getElementById('progress-fill').style.width = `${percent}%`;
  document.getElementById('progress-text').textContent = `${done} of ${total} positions voted`;
  document.getElementById('progress-percent').textContent = `${percent}%`;

  const statusEl = document.getElementById('submit-status');
  if (!statusEl) return;

  statusEl.innerHTML = done < total
    ? `<strong>${done}</strong> / <strong>${total}</strong> positions voted`
    : `All <strong>${total}</strong> positions voted`;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || 'Request failed.');
  }
  return data;
}

async function startSession() {
  const btn = document.getElementById('btn-start-session');
  btn.disabled = true;

  try {
    const payload = await api('/api/kiosk/start-session/', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({}),
    });

    state.ballotId = payload.ballot_id;
    state.sessionToken = payload.session_token;
    state.election = payload.election;
    state.votes = {};
    state.currentSectionIndex = 0;

    document.getElementById('school-name').textContent = state.election.school_name;
    document.getElementById('election-title').textContent = state.election.title;
    document.title = `${state.election.title} | ${state.election.school_name}`;

    setActiveVotingMode();
    renderSection(state.currentSectionIndex);
  } catch (error) {
    alert(error.message);
  } finally {
    btn.disabled = false;
  }
}

async function saveSelection(positionId, candidateId) {
  await api('/api/kiosk/save-selection/', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({
      ballot_id: state.ballotId,
      position_id: positionId,
      candidate_id: candidateId,
    }),
  });
}

function renderSection(index) {
  const container = document.getElementById('voting-container');
  const section = state.election.positions[index];
  const total = state.election.positions.length;

  container.innerHTML = '';

  const posEl = document.createElement('div');
  posEl.className = 'position-section';

  const voted = state.votes[section.id];
  const badgeText = voted ? `✓ ${voted.name}` : 'Not voted';
  const badgeCls = voted ? 'position-badge voted' : 'position-badge';

  posEl.innerHTML = `
    <div class="position-header">
      <span class="position-icon">${section.icon || '🗳️'}</span>
      <div>
        <div class="position-title">${section.position}</div>
        <div class="position-subtitle">Step ${index + 1} of ${total} - Choose one candidate</div>
      </div>
      <span class="${badgeCls}" id="badge-single">${badgeText}</span>
    </div>
    <div class="candidates-grid" id="grid-single" style="--card-cols:${cardColumns(section.candidates.length)}"></div>
  `;

  const grid = posEl.querySelector('#grid-single');

  section.candidates.forEach((candidate) => {
    const card = document.createElement('div');
    card.className = 'candidate-card';

    // ── Build photo/avatar area (top, fills flex space) ──
    let mediaHTML = '';
    if (candidate.photo) {
      const photoSrc = `/${candidate.photo.startsWith('voting/') ? 'static/' : ''}${candidate.photo}`;
      mediaHTML = `
        <div class="candidate-media">
          <img src="${photoSrc}" alt="${candidate.name}" loading="lazy">
        </div>
      `;
    } else {
      mediaHTML = `
        <div class="candidate-media">
          <div class="initials-avatar ${getAvatarColor(candidate.id)}">${getInitials(candidate.name)}</div>
        </div>
      `;
    }

    // ── Build symbol badge (shown inside details row if symbol exists) ──
    let symbolHTML = '';
    if (candidate.symbol) {
      const symbolSrc = `/${candidate.symbol.startsWith('voting/') ? 'static/' : ''}${candidate.symbol}`;
      // Extract human-readable name: "voting/symbols/symbol_cricketBatAndBall.png" → "Cricket Bat And Ball"
      const rawName = candidate.symbol.split('/').pop().replace(/\.png$/i, '').replace(/^symbol_/i, '');
      const symbolName = rawName
        .replace(/([A-Z])/g, ' $1')   // camelCase → spaces
        .replace(/_/g, ' ')            // underscores → spaces
        .trim()
        .replace(/\b\w/g, (c) => c.toUpperCase()); // Title Case
      symbolHTML = `
        <div class="candidate-symbol-wrap">
          <div class="candidate-symbol-text">
            <span class="symbol-label">Symbol</span>
            <span class="symbol-name">${symbolName}</span>
          </div>
          <div class="candidate-symbol-badge">
            <img src="${symbolSrc}" alt="${candidate.name} symbol" loading="lazy">
          </div>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="check-badge">✓</div>
      ${mediaHTML}
      <div class="candidate-details">
        <div class="candidate-info">
          <div class="candidate-name">${candidate.name}</div>
        </div>
        ${symbolHTML}
      </div>
    `;

    if (voted && voted.id === candidate.id) {
      card.classList.add('selected');
    }

    card.addEventListener('click', async () => {
      try {
        await saveSelection(section.id, candidate.id);
        grid.querySelectorAll('.candidate-card').forEach((node) => node.classList.remove('selected'));
        card.classList.add('selected');
        state.votes[section.id] = { id: candidate.id, name: candidate.name };

        const badge = document.getElementById('badge-single');
        badge.textContent = `✓ ${candidate.name}`;
        badge.className = 'position-badge voted';

        const btnNext = document.getElementById('btn-next');
        const btnSubmit = document.getElementById('btn-submit');
        if (btnNext) btnNext.disabled = false;
        if (btnSubmit) btnSubmit.disabled = countVotes() < total;

        updateProgress();
      } catch (error) {
        alert(error.message);
      }
    });

    grid.appendChild(card);
  });

  const isLast = index === total - 1;
  const nav = document.createElement('div');
  nav.className = 'nav-controls';

  nav.innerHTML = `
    <button id="btn-back" class="btn-nav" ${index === 0 ? 'disabled' : ''}>◀ Back</button>
    <p class="submit-status" id="submit-status"></p>
    ${isLast
      ? `<button id="btn-submit" class="btn-submit" ${countVotes() === total ? '' : 'disabled'}>🗳️ Review &amp; Submit Ballot</button>`
      : `<button id="btn-next" class="btn-nav primary" ${voted ? '' : 'disabled'}>Next ▶</button>`
    }
  `;

  container.appendChild(posEl);
  container.appendChild(nav);

  document.getElementById('btn-back').addEventListener('click', () => {
    if (state.currentSectionIndex > 0) {
      state.currentSectionIndex -= 1;
      renderSection(state.currentSectionIndex);
    }
  });

  const btnNext = document.getElementById('btn-next');
  if (btnNext) {
    btnNext.addEventListener('click', () => {
      if (!state.votes[section.id]) return;
      state.currentSectionIndex += 1;
      renderSection(state.currentSectionIndex);
    });
  }

  const btnSubmit = document.getElementById('btn-submit');
  if (btnSubmit) {
    btnSubmit.addEventListener('click', openModal);
  }

  updateProgress();
}

function openModal() {
  const summaryEl = document.getElementById('modal-summary');
  summaryEl.innerHTML = '';

  state.election.positions.forEach((position) => {
    const vote = state.votes[position.id];
    const item = document.createElement('div');
    item.className = 'summary-item';
    item.innerHTML = `
      <span class="summary-position">${position.icon || '🗳️'} ${position.position}</span>
      <span class="summary-candidate">${vote ? vote.name : '-'}</span>
    `;
    summaryEl.appendChild(item);
  });

  document.getElementById('modal-overlay').classList.add('active');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
}

async function submitBallot() {
  try {
    const payload = await api('/api/kiosk/submit/', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({ ballot_id: state.ballotId }),
    });

    closeModal();
    document.getElementById('voting-content').classList.add('hidden');
    document.getElementById('success-screen').classList.add('active');
    document.getElementById('receipt-token').textContent = payload.receipt_token;

    state.ballotId = null;
    state.sessionToken = null;
    state.votes = {};

    setTimeout(() => {
      setWaitingMode();
    }, 5000);
  } catch (error) {
    alert(error.message);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setWaitingMode();
  blockBackNavigation();

  document.getElementById('btn-start-session').addEventListener('click', startSession);
  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-confirm-submit').addEventListener('click', submitBallot);
});
