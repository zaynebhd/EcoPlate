(async function () {
  const box = document.getElementById('priorites');
  try {
    const data = (await api('/api/food')).slice(0, 4);
    if (!data.length) {
      box.innerHTML = `<p class="vide">Votre frigo est vide pour l’instant. Ajoutez votre premier aliment pour le voir apparaître ici.</p><a href="food.html">Ajouter un aliment</a>`;
      return;
    }
    box.innerHTML = '<ul>' + data.map(a => {
      const j = joursRestants(a.date_peremption);
      const txt = j < 0 ? 'périmé' : j === 0 ? 'aujourd’hui' : j === 1 ? 'demain' : `dans ${j} jours`;
      return `<li class="${j <= 3 ? 'urgent' : ''}"><span>${esc(a.nom)} <small>× ${a.quantite}</small></span><small>${txt}</small></li>`;
    }).join('') + '</ul><a href="food.html">Voir tous mes aliments</a>';
  } catch (e) {
    box.innerHTML = '<p class="vide">Impossible de charger vos aliments pour le moment.</p>';
  }
})();
