// Éléments partagés : navigation, pied de page, utilitaires
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// Date locale du jour au format AAAA-MM-JJ (évite les décalages de fuseau horaire)
function aujourdhui() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function parseDate(str) {            // 'AAAA-MM-JJ' -> Date locale à minuit
  const [y, m, j] = str.split('-').map(Number);
  return new Date(y, m - 1, j);
}
function joursRestants(str) {
  const t = parseDate(aujourdhui());
  return Math.round((parseDate(str) - t) / 86400000);
}
function formatDate(str) { return parseDate(str).toLocaleDateString('fr-FR'); }

async function api(url, options) {
  const res = await fetch(url, options);
  let data = {};
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error(data.error || 'Une erreur est survenue.');
  return data;
}
const post = (url, body) => api(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });

(function () {
  const nav = document.getElementById('nav');
  const foot = document.getElementById('footer');
  if (foot) foot.innerHTML = 'EcoPlate – Moins de gaspillage, plus d’avenir.';

  if (!nav) return;
  (async () => {
    try {
      const {user} = await api('/api/session');
      const page = location.pathname.split('/').pop() || 'index.html';
      const pages = user && user.role === 'organization'
        ? [['organization-dashboard.html', 'Espace organisation']]
        : user
          ? [['index.html', 'Accueil'], ['food.html', 'Mes aliments'], ['offers.html', 'Offres'], ['recipes.html', 'Recettes'], ['impact.html', 'Mon impact']]
          : [['account-type.html', 'Choisir un compte']];
      const links = pages.map(([href, label]) =>
        `<a href="${href}"${href === page ? ' aria-current="page"' : ''}>${label}</a>`).join('');
      const home = user
        ? (user.role === 'organization' ? 'organization-dashboard.html' : 'index.html')
        : 'account-type.html';
      const account = user
        ? `<span class="nav-user">${esc(user.email)}</span><button class="nav-logout" id="logout" type="button">Déconnexion</button>`
        : '<a href="account-type.html">Connexion / inscription</a>';
      nav.innerHTML = `<nav aria-label="Navigation principale">
        <a class="logo" href="${home}"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 27C5 14 12 6 27 5c0 14-7 21-19 21" fill="#a9c8a3"/><path d="M5 27C11 19 16 14 23 9" stroke="#24523a" stroke-width="2" fill="none" stroke-linecap="round"/></svg>EcoPlate</a>
        <div class="links">${links}${account}</div></nav>`;

      const logout = document.getElementById('logout');
      if (logout) logout.addEventListener('click', async () => {
        try {
          await api('/logout', {method: 'POST'});
          location.assign('account-type.html');
        } catch (error) {
          alert(error.message);
        }
      });
    } catch (error) {
      console.error('Impossible de charger la navigation EcoPlate.', error);
      nav.innerHTML = '<nav aria-label="Navigation principale"><a class="logo" href="account-type.html">EcoPlate</a><span role="alert">Navigation indisponible.</span></nav>';
    }
  })();
})();
