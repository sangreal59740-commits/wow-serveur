// Boutique : rendu commun au site et au launcher
window.Boutique = (function () {
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const jeton = {
    lire() { try { return localStorage.getItem('jeton') || ''; } catch { return ''; } },
    ecrire(v) { try { v ? localStorage.setItem('jeton', v) : localStorage.removeItem('jeton'); } catch { } }
  };
  async function api(url, corps) {
    const h = { 'Content-Type': 'application/json' };
    const j = jeton.lire(); if (j) h.Authorization = 'Bearer ' + j;
    const r = await fetch(url, corps === undefined ? { headers: h } : { method: 'POST', headers: h, body: JSON.stringify(corps) });
    return r.json();
  }
  const ICONES = {
    'Montures': '<svg viewBox="0 0 24 24"><path d="M19 5l-3 1-2-2-1 3-5 1-4 5 2 1 2-2v8h2v-5h4v5h2V9l3-1 1 2 2-1-2-5z"/></svg>',
    'Compagnons': '<svg viewBox="0 0 24 24"><path d="M12 2l2.5 5 5.5.8-4 3.9 1 5.5L12 14.6 7 17.2l1-5.5-4-3.9L9.5 7zM5 19h14v2H5z"/></svg>',
    'Cosmétiques': '<svg viewBox="0 0 24 24"><path d="M12 2l3 7h7l-5.5 4.5 2 7.5L12 16.5 5.5 21l2-7.5L2 9h7z"/></svg>',
    'Confort': '<svg viewBox="0 0 24 24"><path d="M6 7V6a6 6 0 0112 0v1h3l-1 15H4L3 7zm2 0h8V6a4 4 0 00-8 0z"/></svg>'
  };
  const icone = c => ICONES[c] || ICONES['Cosmétiques'];

  // grille d'articles avec onglets de catégories
  function rendre(el, cat, opts) {
    const cats = cat.categories.length ? cat.categories : [...new Set(cat.articles.map(a => a.categorie))];
    let actif = opts.categorie || cats[0];
    function dessiner() {
      const liste = cat.articles.filter(a => a.categorie === actif);
      el.innerHTML = `
        <div class="bq-cats">${cats.map(c => `<button class="${c === actif ? 'on' : ''}" data-c="${esc(c)}">${icone(c)}<span>${esc(c)}</span></button>`).join('')}</div>
        <div class="bq-grille">${liste.map(a => `
          <div class="bq-article q-${esc(a.qualite || 'rare')}${a.bientot ? ' bientot' : ''}">
            <div class="bq-ico">${icone(a.categorie)}</div>
            <h4>${esc(a.nom)}</h4>
            <p>${esc(a.desc || '')}</p>
            <div class="bq-pied">
              ${a.bientot ? '<span class="bq-prix">Bientôt</span>' : `<span class="bq-prix">${a.prix.toLocaleString('fr-FR')} <i>Gen</i></span>
              <button class="btn petit-btn" data-a="${esc(a.id)}">Acheter</button>`}
            </div>
          </div>`).join('')}</div>`;
      el.querySelectorAll('.bq-cats button').forEach(b => b.onclick = () => { actif = b.dataset.c; dessiner(); });
      el.querySelectorAll('[data-a]').forEach(b => b.onclick = () => opts.acheter(cat.articles.find(a => a.id === b.dataset.a)));
    }
    dessiner();
  }

  // fenêtre de confirmation : choix du personnage
  function confirmer(article, moi, apres) {
    const fond = document.createElement('div');
    fond.className = 'bq-modal';
    const persos = (moi && moi.persos) || [];
    fond.innerHTML = `<div class="bq-boite">
      <h3>${esc(article.nom)}</h3>
      <p class="bq-cout">${article.prix.toLocaleString('fr-FR')} Gen · ton solde : ${(moi.solde || 0).toLocaleString('fr-FR')} Gen</p>
      ${persos.length ? `<label>Personnage qui le reçoit par courrier</label>
      <select id="bqPerso">${persos.map(p => `<option value="${p.guid}">${esc(p.nom)} (niv. ${p.niveau})</option>`).join('')}</select>`
        : '<p class="msg err">Crée d\'abord un personnage dans le jeu.</p>'}
      <div class="msg" id="bqMsg"></div>
      <div class="bq-actions"><button class="btn" id="bqNon">Annuler</button><button class="btn plein" id="bqOui" ${persos.length && moi.solde >= article.prix ? '' : 'disabled'}>Confirmer</button></div>
      ${moi.solde < article.prix ? '<p class="msg err">Pas assez de Gen.</p>' : ''}
    </div>`;
    document.body.appendChild(fond);
    const fermer = () => fond.remove();
    fond.onclick = e => { if (e.target === fond) fermer(); };
    fond.querySelector('#bqNon').onclick = fermer;
    const oui = fond.querySelector('#bqOui');
    oui.onclick = async () => {
      oui.disabled = true;
      const m = fond.querySelector('#bqMsg'); m.className = 'msg'; m.textContent = 'Achat en cours…';
      try {
        const r = await api('/api/acheter', { article: article.id, perso: fond.querySelector('#bqPerso').value });
        m.className = 'msg ' + (r.ok ? 'ok' : 'err'); m.textContent = r.message;
        if (r.ok) { apres && apres(r); oui.remove(); fond.querySelector('#bqNon').textContent = 'Fermer'; }
        else oui.disabled = false;
      } catch { m.className = 'msg err'; m.textContent = 'Le portail ne répond pas.'; oui.disabled = false; }
    };
  }

  return { api, jeton, rendre, confirmer, esc };
})();
