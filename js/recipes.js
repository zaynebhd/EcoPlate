const grid = document.getElementById('grid');
const info = document.getElementById('info');
const btnMatch = document.getElementById('match');
const btnAll = document.getElementById('all');
let recipes = [];
let mode = 'all';

// Petit emoji illustratif selon les ingrédients (🍽️ par défaut)
const EMOJIS = [['tomate','🍅'],['oeuf','🥚'],['œuf','🥚'],['pate','🍝'],['pâte','🍝'],['riz','🍚'],['pain','🍞'],['lait','🥛'],['fromage','🧀'],
  ['carotte','🥕'],['pomme de terre','🥔'],['patate','🥔'],['poulet','🍗'],['viande','🥩'],['poisson','🐟'],['pomme','🍎'],['banane','🍌'],
  ['salade','🥬'],['oignon','🧅'],['courgette','🥒'],['concombre','🥒'],['poivron','🫑'],['champignon','🍄'],['citron','🍋'],['fraise','🍓']];
function emojiDe(r) {
  const texte = (r.nom + ' ' + r.ingredients.join(' ')).toLowerCase();
  for (const [mot, e] of EMOJIS) if (texte.includes(mot)) return e;
  return '🍽️';
}

function render() {
  const list = mode === 'feasible' ? recipes.filter(r => r.feasible) : recipes;
  info.textContent = `${list.length} recette${list.length > 1 ? 's' : ''}`;
  if (!list.length) {
    grid.innerHTML = `<p class="empty" style="grid-column:1/-1">${
      mode === 'feasible'
        ? 'Aucune recette ne peut encore être préparée avec tous vos aliments.'
        : 'Aucune recette de la plateforme n’est disponible pour le moment.'}</p>`;
    return;
  }
  grid.innerHTML = list.map(r => {
    const chips = r.ingredients.map(ingredient => {
      const available = r.have.includes(ingredient);
      const urgent = r.urgent.includes(ingredient);
      const className = available ? `have${urgent ? ' urgent' : ''}` : 'missing';
      return `<span class="chip ${className}">${esc(ingredient)}</span>`;
    }).join('');
    const score = `<p class="score ${r.feasible ? 'full' : ''}">${r.percentage}% · ${r.have.length}/${r.ingredients.length} ingrédients disponibles</p>`;
    const missing = r.missing.length
      ? `<p class="missing-list"><strong>Il vous manque :</strong> ${r.missing.map(esc).join(', ')}</p>`
      : '<p class="missing-list available-all">Vous avez tous les ingrédients ✔</p>';
    const urgent = r.urgent.length
      ? `<p class="urgent-note">À utiliser bientôt : ${r.urgent.map(esc).join(', ')}</p>`
      : '';
    return `<div class="card recipe" data-id="${r.id_recette}">
      <div class="pic">${emojiDe(r)}</div>
      <h3>${esc(r.nom)}</h3>${score}
      <div class="chips">${chips}</div>
      ${missing}${urgent}
      <p class="desc" hidden>${esc(r.description || 'Aucune préparation renseignée.')}</p>
      <div class="actions">
        <button class="btn small" data-act="toggle">Voir la préparation</button>
      </div></div>`;
  }).join('');
}

async function charger() {
  try { recipes = await api('/api/recipes'); render(); }
  catch (error) {
    info.textContent = '';
    grid.innerHTML = `<p class="empty" style="grid-column:1/-1">${esc(error.message)}</p>`;
  }
}

grid.addEventListener('click', async e => {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const card = btn.closest('.recipe');
  if (btn.dataset.act === 'toggle') {
    const d = card.querySelector('.desc');
    d.hidden = !d.hidden;
    btn.textContent = d.hidden ? 'Voir la préparation' : 'Masquer la préparation';
  }
});

btnMatch.onclick = () => { mode = 'feasible'; btnMatch.hidden = true; btnAll.hidden = false; render(); };
btnAll.onclick = () => { mode = 'all'; btnAll.hidden = true; btnMatch.hidden = false; render(); };

charger();
