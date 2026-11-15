(async function () {
  const tiles = document.getElementById('tiles');
  const chart = document.getElementById('chart');
  let d;
  try { d = await api('/api/impact?today=' + aujourdhui()); }
  catch (e) { tiles.innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }

  const tile = (n, label, star) => `<div class="tile ${star ? 'star' : ''}"><strong>${n}</strong><span>${label}</span></div>`;
  tiles.innerHTML =
    tile(d.sauves, 'aliments sauvés du gaspillage', true) +
    tile(d.taux === null ? '–' : d.taux + ' %', 'taux de réussite') +
    tile(d.total, 'aliments enregistrés') +
    tile(d.consommes, 'aliments consommés') +
    tile(d.gaspilles, 'aliments jetés') +
    tile(d.a_surveiller, 'à consommer très vite');

  if (!d.consommes && !d.gaspilles) {
    chart.innerHTML = '<p class="empty">Pas encore de données. Marquez un aliment comme « Consommé » ou « Jeté » dans <a href="food.html">Mes aliments</a> pour voir votre progression.</p>';
    return;
  }

  // Graphique en barres (SVG) : consommés / jetés par semaine
  const W = 640, H = 260, L = 34, B = 34, T = 14;
  const max = Math.max(4, ...d.semaines.flatMap(s => [s.consommes, s.gaspilles]));
  const step = max <= 8 ? 1 : Math.ceil(max / 5);
  const top = Math.ceil(max / step) * step;
  const y = v => T + (H - T - B) * (1 - v / top);
  const slot = (W - L) / d.semaines.length;
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Aliments consommés et jetés par semaine sur les 6 dernières semaines">`;
  for (let v = 0; v <= top; v += step) svg += `<line x1="${L}" x2="${W}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${v}</text>`;
  d.semaines.forEach((s, i) => {
    const x = L + i * slot + slot / 2, bw = Math.min(26, slot / 3);
    const label = parseDate(s.debut).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
    svg += `<rect class="bar-c" x="${x - bw - 2}" y="${y(s.consommes)}" width="${bw}" height="${y(0) - y(s.consommes)}" rx="4"><title>${s.consommes} consommé(s)</title></rect>`;
    svg += `<rect class="bar-w" x="${x + 2}" y="${y(s.gaspilles)}" width="${bw}" height="${y(0) - y(s.gaspilles)}" rx="4"><title>${s.gaspilles} jeté(s)</title></rect>`;
    svg += `<text x="${x}" y="${H - 12}" text-anchor="middle">${label}</text>`;
  });
  chart.innerHTML = svg + '</svg>';
})();
