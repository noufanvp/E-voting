/**
 * ============================================================
 *  E-VOTING SYSTEM — MAIN LOGIC
 *  Single-page no-scroll layout: one position visible at a time
 *  with a unified bottom navigation / submit bar.
 * ============================================================
 */

// ── 1. State ──────────────────────────────────────────────
// votes[position] = { id, name, position }
const votes = {};

// Current position index (0 … ELECTION_DATA.length - 1)
let currentSectionIndex = 0;

// ── 2. Helpers ────────────────────────────────────────────

/** Returns the first two initials of a name. */
function getInitials(name) {
  return name.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
}

/** Picks a CSS avatar colour class based on candidate id. */
function getAvatarColor(id) {
  return `av-${id % 8}`;
}

/** Returns how many positions have been voted on. */
function countVotes() {
  return Object.keys(votes).length;
}

/** Generates a short random token (like a receipt). */
function generateToken() {
  return Math.random().toString(36).substring(2, 8).toUpperCase();
}

/**
 * Derives the number of candidate columns from the count.
 * Kept to a sensible max so cards never become too narrow.
 */
function cardColumns(count) {
  if (count <= 2) return 2;
  if (count <= 3) return 3;
  return 4; // 4 candidates (including NOTA) → 4 cols
}

// ── 3. Page Render ────────────────────────────────────────

/**
 * Bootstraps the page from ELECTION_DATA.
 * Called once on DOMContentLoaded.
 */
function renderPage() {
  document.getElementById('school-name').textContent   = SCHOOL_NAME;
  document.getElementById('election-title').textContent = ELECTION_TITLE;
  document.title = `${ELECTION_TITLE} | ${SCHOOL_NAME}`;

  currentSectionIndex = 0;
  renderSection(currentSectionIndex);
}

// ── 4. Section Render (single-position view) ─────────────

/**
 * Renders a single voting position (step) and injects:
 *   • position header with badge
 *   • candidate card grid (fills all available height)
 *   • bottom nav bar (Back | status | Next / Submit)
 *
 * Layout never triggers a scrollbar because the grid and cards
 * use flex/grid with flex:1 to fit exactly the remaining height.
 */
function renderSection(index) {
  const container = document.getElementById('voting-container');
  const section   = ELECTION_DATA[index];
  const total     = ELECTION_DATA.length;

  container.innerHTML = '';

  // ── Position header ──────────────────────────────────
  const posEl = document.createElement('div');
  posEl.className = 'position-section';
  posEl.dataset.position = section.position;

  const voted     = votes[section.position];
  const badgeText = voted ? `✓ ${voted.name}` : 'Not voted';
  const badgeCls  = voted ? 'position-badge voted' : 'position-badge';

  posEl.innerHTML = `
    <div class="position-header">
      <span class="position-icon">${section.icon}</span>
      <div>
        <div class="position-title">${section.position}</div>
        <div class="position-subtitle">Step ${index + 1} of ${total} — Choose one candidate</div>
      </div>
      <span class="${badgeCls}" id="badge-single">${badgeText}</span>
    </div>
    <div class="candidates-grid" id="grid-single"
         style="--card-cols:${cardColumns(section.candidates.length)}">
    </div>
  `;

  // ── Candidate cards ──────────────────────────────────
  const grid = posEl.querySelector('#grid-single');

  section.candidates.forEach(candidate => {
    const card = document.createElement('div');
    card.className = 'candidate-card';
    card.dataset.candidateId = candidate.id;

    const avatarHTML = candidate.photo
      ? `<img src="${candidate.photo}" alt="${candidate.name}" loading="lazy">`
      : `<div class="initials-avatar ${getAvatarColor(candidate.id)}">${getInitials(candidate.name)}</div>`;

    card.innerHTML = `
      <div class="check-badge">✓</div>
      <div class="candidate-avatar">${avatarHTML}</div>
      <div class="candidate-details">
        <div class="candidate-name">${candidate.name}</div>
        <div class="candidate-class">${candidate.class}</div>

      </div>
    `;

    // Restore selection state
    if (voted && voted.id === candidate.id) card.classList.add('selected');

    card.addEventListener('click', () => handleVoteSingle(card, candidate, section.position));
    grid.appendChild(card);
  });

  // ── Bottom navigation bar ────────────────────────────
  const isLast    = index === ELECTION_DATA.length - 1;
  const allVoted  = countVotes() === total;

  const nav = document.createElement('div');
  nav.className = 'nav-controls';
  nav.id = 'nav-controls';

  nav.innerHTML = `
    <button id="btn-back" class="btn-nav" aria-label="Previous position"
      ${index === 0 ? 'disabled' : ''}>◀ Back</button>

    <p class="submit-status" id="submit-status"></p>

    ${isLast
      ? `<button id="btn-submit" class="btn-submit"
           ${allVoted ? '' : 'disabled'} onclick="openModal()">
           🗳️ Review &amp; Submit Ballot
         </button>`
      : `<button id="btn-next" class="btn-nav primary" aria-label="Next position"
           ${voted ? '' : 'disabled'}>Next ▶</button>`
    }
  `;

  container.appendChild(posEl);
  container.appendChild(nav);

  // ── Wire up navigation buttons ───────────────────────
  const btnBack = document.getElementById('btn-back');

  btnBack.addEventListener('click', () => {
    if (currentSectionIndex > 0) {
      currentSectionIndex -= 1;
      renderSection(currentSectionIndex);
    }
  });

  if (!isLast) {
    const btnNext = document.getElementById('btn-next');
    btnNext.addEventListener('click', () => {
      if (!votes[section.position]) return;
      currentSectionIndex += 1;
      renderSection(currentSectionIndex);
    });
  }

  // Update progress + status text
  updateProgress();
}

// ── 5. Vote Handler ───────────────────────────────────────

/**
 * Called when a voter clicks a candidate card.
 * Deselects any previously chosen card, selects the new one,
 * saves the vote, and refreshes the badge + nav buttons.
 */
function handleVoteSingle(clickedCard, candidate, position) {
  const grid = document.getElementById('grid-single');

  // Deselect all cards
  grid.querySelectorAll('.candidate-card').forEach(c => c.classList.remove('selected'));

  // Select clicked card
  clickedCard.classList.add('selected');

  // Persist vote
  votes[position] = { id: candidate.id, name: candidate.name, position };

  // Update header badge
  const badge = document.getElementById('badge-single');
  badge.textContent = `✓ ${candidate.name}`;
  badge.className = 'position-badge voted';

  // Enable Next / Submit button
  const btnNext   = document.getElementById('btn-next');
  const btnSubmit = document.getElementById('btn-submit');
  if (btnNext)   btnNext.disabled   = false;
  if (btnSubmit) btnSubmit.disabled = (countVotes() < ELECTION_DATA.length);

  // Refresh progress bar
  updateProgress();
}

// ── 6. Progress Bar ───────────────────────────────────────

function updateProgress() {
  const total   = ELECTION_DATA.length;
  const done    = countVotes();
  const percent = Math.round((done / total) * 100);

  document.getElementById('progress-fill').style.width    = `${percent}%`;
  document.getElementById('progress-text').textContent    = `${done} of ${total} positions voted`;
  document.getElementById('progress-percent').textContent = `${percent}%`;

  // Status text inside the nav bar
  const statusEl = document.getElementById('submit-status');
  if (statusEl) {
    statusEl.innerHTML = done < total
      ? `<strong>${done}</strong> / <strong>${total}</strong> positions voted`
      : `✅ All <strong>${total}</strong> positions voted!`;
  }
}

// ── 7. Confirmation Modal ─────────────────────────────────

function openModal() {
  const summaryEl = document.getElementById('modal-summary');
  summaryEl.innerHTML = '';

  ELECTION_DATA.forEach(section => {
    const vote = votes[section.position];
    const item = document.createElement('div');
    item.className = 'summary-item';
    item.innerHTML = `
      <span class="summary-position">${section.icon} ${section.position}</span>
      <span class="summary-candidate">${vote ? vote.name : '—'}</span>
    `;
    summaryEl.appendChild(item);
  });

  document.getElementById('modal-overlay').classList.add('active');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
}

function confirmVote() {
  closeModal();
  showSuccessScreen();
}

// ── 8. Success Screen ─────────────────────────────────────

function showSuccessScreen() {
  // Hide voting content
  document.getElementById('voting-content').style.display = 'none';

  // Show success screen (it's a flex sibling of voting-content)
  const screen = document.getElementById('success-screen');
  screen.classList.add('active');

  // Random receipt token
  document.getElementById('receipt-token').textContent = generateToken();
}

// ── 9. Initialise ─────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  renderPage();
});
