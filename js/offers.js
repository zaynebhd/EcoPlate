const offerFilters = document.getElementById('offerFilters');
const offerList = document.getElementById('offerList');
const offerMessage = document.getElementById('offerMessage');
let isOrganization = false;

const offerStatusLabels = {active: 'Active', sold_out: 'Épuisée', expired: 'Expirée'};
const offerOrganizationLabels = {association: 'Association', hotel: 'Hôtel', restaurant: 'Restaurant'};

function renderOffer(item) {
  const canReserve = item.status === 'active' && item.quantity_available > 0;
  return `<article class="announcement-card">
    <div class="announcement-heading">
      <div><h3>${esc(item.food_name)}</h3><span class="announcement-org">${esc(offerOrganizationLabels[item.organization_type] || item.organization_type)} · ${esc(item.organization_name)}</span></div>
      <span class="badge status-${esc(item.status)}">${esc(offerStatusLabels[item.status] || item.status)}</span>
    </div>
    <p class="announcement-description">${esc(item.description || 'Aucune description.')}</p>
    <div class="announcement-details">
      <span>Disponible : <strong>${item.quantity_available}</strong></span>
      <span>Prix : <s>${Number(item.normal_price).toFixed(2)} €</s> <strong>${Number(item.reduced_price).toFixed(2)} €</strong></span>
      <span>Date limite : <strong>${formatDate(item.deadline)}</strong></span>
      <span>Lieu : <strong>${esc(item.organization_address)}</strong></span>
    </div>
    ${canReserve ? `<form class="reserve-form" data-id="${item.id}">
      <label for="reserve-${item.id}">Quantité à réserver</label>
      <input id="reserve-${item.id}" name="quantity" type="number" min="1" max="${item.quantity_available}" step="1" value="1" required>
      <button class="btn small" type="submit">Réserver</button>
    </form>` : ''}
  </article>`;
}

async function loadOffers() {
  offerList.innerHTML = '<p class="empty">Chargement des offres…</p>';
  try {
    const {user} = await api('/api/session');
    isOrganization = user && user.role === 'organization';
    if (isOrganization) {
      document.getElementById('offersTitle').textContent = 'Offres des autres organisations';
      document.getElementById('offersDescription').textContent =
        'Consultez et réservez les annonces publiées par les autres associations, hôtels et restaurants.';
    }
    const params = new URLSearchParams(new FormData(offerFilters));
    const offers = await api('/api/announcements?' + params.toString());
    offerList.innerHTML = offers.length
      ? offers.map(renderOffer).join('')
      : '<p class="empty">Aucune offre ne correspond à ces filtres.</p>';
  } catch (error) {
    offerList.innerHTML = `<p class="empty">${esc(error.message)}</p>`;
  }
}

offerFilters.addEventListener('submit', event => {
  event.preventDefault();
  loadOffers();
});

offerList.addEventListener('submit', async event => {
  const form = event.target.closest('form.reserve-form');
  if (!form) return;
  event.preventDefault();
  offerMessage.textContent = '';
  offerMessage.className = 'msg';
  const quantity = Number(new FormData(form).get('quantity'));
  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  try {
    await post(`/api/announcements/${form.dataset.id}/reservations`, {quantity});
    offerMessage.textContent = 'Réservation confirmée. La quantité disponible a été mise à jour.';
    offerMessage.className = 'msg ok';
    await loadOffers();
  } catch (error) {
    offerMessage.textContent = error.message;
    offerMessage.className = 'msg err';
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
});

loadOffers();
