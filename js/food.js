const list = document.getElementById('list');
const msg = document.getElementById('msg');
const resume = document.getElementById('resume');

function statut(j) {
  if (j < 0) return ['Périmé', 'exp'];
  if (j <= 3) return ['À surveiller', 'warn'];
  return ['OK', 'ok'];
}
function quand(j) {
  if (j < 0) return `périmé depuis ${-j} jour${j < -1 ? 's' : ''}`;
  if (j === 0) return 'expire aujourd’hui';
  if (j === 1) return 'expire demain';
  return `expire dans ${j} jours`;
}

async function charger() {
  let data;
  try { data = await api('/api/food'); }
  catch (e) { list.innerHTML = `<li class="empty">${esc(e.message)}</li>`; return; }

  if (!data.length) {
    resume.textContent = '';
    list.innerHTML = '<li class="empty">Aucun aliment pour le moment. Ajoutez le premier avec le formulaire ci-dessus 🥕</li>';
    return;
  }
  const urgents = data.filter(a => joursRestants(a.date_peremption) <= 3).length;
  resume.textContent = `${data.length} aliment${data.length > 1 ? 's' : ''}` + (urgents ? ` · ${urgents} à surveiller` : '');
  list.innerHTML = data.map(a => {
    const j = joursRestants(a.date_peremption);
    const [txt, cls] = statut(j);
    return `<li class="item" data-id="${a.id_aliment}">
      <div><strong>${esc(a.nom)}</strong><span class="qty">Quantité : ${a.quantite}</span></div>
      <div class="when"><span class="badge ${cls}">${txt}</span><small>${quand(j)} (${formatDate(a.date_peremption)})</small></div>
      <div class="actions">
        <button class="btn small" data-act="consumed">Consommé</button>
        <button class="btn small ghost" data-act="wasted">Jeté</button>
        <button class="link-del" data-act="delete">Supprimer</button>
      </div></li>`;
  }).join('');
}

document.getElementById('form').addEventListener('submit', async e => {
  e.preventDefault();
  msg.className = 'msg';
  try {
    await post('/api/food', {
      nom: document.getElementById('nom').value,
      quantite: document.getElementById('quantite').value,
      date_peremption: document.getElementById('date').value
    });
    e.target.reset();
    msg.textContent = 'Aliment ajouté ✔'; msg.className = 'msg ok';
    document.getElementById('nom').focus();
    charger();
  } catch (err) { msg.textContent = err.message; msg.className = 'msg err'; }
});

list.addEventListener('click', async e => {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const id = btn.closest('.item').dataset.id;
  const act = btn.dataset.act;
  try {
    if (act === 'delete') {
      if (!confirm('Supprimer cet aliment ? (il ne comptera pas dans votre impact)')) return;
      await api('/api/food/' + id, { method: 'DELETE' });
    } else {
      await api('/api/food/' + id, { method: 'PATCH', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ statut: act, today: aujourdhui() }) });
    }
    charger();
  } catch (err) { msg.textContent = err.message; msg.className = 'msg err'; }
});

charger();
