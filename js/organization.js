const announcementForm = document.getElementById('announcementForm');
const announcementList = document.getElementById('announcementList');
const announcementMessage = document.getElementById('announcementMessage');
const announcementCount = document.getElementById('announcementCount');
const submitAnnouncement = document.getElementById('submitAnnouncement');
const cancelEdit = document.getElementById('cancelEdit');
const deadlineInput = document.getElementById('deadline');
let editingId = null;
deadlineInput.min = aujourdhui();

const statusLabels = {active: 'Active', sold_out: 'Épuisée', expired: 'Expirée'};
const organizationLabels = {association: 'Association', hotel: 'Hôtel', restaurant: 'Restaurant'};

function showAnnouncementMessage(text, type) {
  announcementMessage.textContent = text;
  announcementMessage.className = `msg ${type || ''}`;
}

function renderAnnouncement(item) {
  const reserved = item.quantity_total - item.quantity_available;
  const reservations = item.reservations || [];
  return `<article class="announcement-card">
    <div class="announcement-heading">
      <div><h3>${esc(item.food_name)}</h3><span class="announcement-org">${esc(organizationLabels[item.organization_type] || item.organization_type)} · ${esc(item.organization_name)}</span></div>
      <span class="badge status-${esc(item.status)}">${esc(statusLabels[item.status] || item.status)}</span>
    </div>
    <p class="announcement-description">${esc(item.description || 'Aucune description.')}</p>
    <div class="announcement-details">
      <span>Disponible : <strong>${item.quantity_available}</strong> / ${item.quantity_total}</span>
      <span>Réservé : <strong>${reserved}</strong></span>
      <span>Prix : <s>${Number(item.normal_price).toFixed(2)} €</s> <strong>${Number(item.reduced_price).toFixed(2)} €</strong></span>
      <span>Date limite : <strong>${formatDate(item.deadline)}</strong></span>
    </div>
    <section class="reservation-section" aria-label="Réservations">
      <h4>Réservations</h4>
      ${reservations.length ? `<ul class="reservation-list">${reservations.map(reservation => `
        <li><strong>${esc(reservation.reserver_name)}</strong>
          <span>Quantité : ${reservation.quantity} · ${new Date(reservation.created_at).toLocaleString('fr-FR')}</span>
        </li>`).join('')}</ul>` : '<p class="empty">Aucune réservation pour cette annonce.</p>'}
    </section>
    <div class="announcement-actions">
      <button class="btn small" type="button" data-action="edit" data-id="${item.id}">Modifier</button>
      <button class="btn danger-ghost small" type="button" data-action="delete" data-id="${item.id}">Supprimer</button>
    </div>
  </article>`;
}

async function loadAnnouncements() {
  announcementList.innerHTML = '<p class="empty">Chargement des annonces…</p>';
  try {
    const items = await api('/api/organization/announcements');
    announcementCount.textContent = `${items.length} annonce${items.length === 1 ? '' : 's'}`;
    announcementList.innerHTML = items.length
      ? items.map(renderAnnouncement).join('')
      : '<p class="empty">Vous n’avez pas encore publié d’annonce.</p>';
  } catch (error) {
    announcementList.innerHTML = `<p class="empty">${esc(error.message)}</p>`;
  }
}

function resetAnnouncementForm() {
  announcementForm.reset();
  deadlineInput.min = aujourdhui();
  editingId = null;
  submitAnnouncement.textContent = 'Publier l’annonce';
  document.getElementById('announcementFormTitle').textContent = 'Publier une annonce';
  cancelEdit.hidden = true;
}

announcementForm.addEventListener('submit', async event => {
  event.preventDefault();
  showAnnouncementMessage('', '');
  const data = {
    food_name: document.getElementById('foodName').value,
    quantity_total: Number(document.getElementById('quantityTotal').value),
    normal_price: Number(document.getElementById('normalPrice').value),
    reduced_price: Number(document.getElementById('reducedPrice').value),
    deadline: document.getElementById('deadline').value,
    description: document.getElementById('description').value
  };
  try {
    if (editingId) {
      await api(`/api/organization/announcements/${editingId}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
      });
      showAnnouncementMessage('Annonce modifiée ✔', 'ok');
    } else {
      await post('/api/organization/announcements', data);
      showAnnouncementMessage('Annonce publiée ✔', 'ok');
    }
    resetAnnouncementForm();
    loadAnnouncements();
  } catch (error) {
    showAnnouncementMessage(error.message, 'err');
  }
});

cancelEdit.addEventListener('click', () => {
  resetAnnouncementForm();
  showAnnouncementMessage('', '');
});

announcementList.addEventListener('click', async event => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const itemId = button.dataset.id;
  const action = button.dataset.action;
  try {
    if (action === 'delete') {
      if (!confirm('Supprimer cette annonce et ses réservations ?')) return;
      await api(`/api/organization/announcements/${itemId}`, {method: 'DELETE'});
      showAnnouncementMessage('Annonce supprimée.', 'ok');
      loadAnnouncements();
      return;
    }
    const item = (await api('/api/organization/announcements')).find(row => String(row.id) === itemId);
    if (!item) throw new Error('Annonce introuvable.');
    editingId = item.id;
    document.getElementById('foodName').value = item.food_name;
    document.getElementById('quantityTotal').value = item.quantity_total;
    document.getElementById('normalPrice').value = item.normal_price;
    document.getElementById('reducedPrice').value = item.reduced_price;
    deadlineInput.min = item.deadline;
    deadlineInput.value = item.deadline;
    document.getElementById('description').value = item.description;
    submitAnnouncement.textContent = 'Enregistrer les modifications';
    document.getElementById('announcementFormTitle').textContent = 'Modifier une annonce';
    cancelEdit.hidden = false;
    document.getElementById('foodName').focus();
  } catch (error) {
    showAnnouncementMessage(error.message, 'err');
  }
});

loadAnnouncements();
