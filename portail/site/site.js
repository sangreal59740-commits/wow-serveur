(function () {
  const D = window.DATA, $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  $('#accroche').textContent = D.accroche;
  $('#intro').textContent = D.intro;
  $('#atouts').innerHTML = D.atouts.map(a => `<div class="atout apparait">${ICONES[a.icone]}<h3>${esc(a.titre)}</h3><p>${esc(a.texte)}</p></div>`).join('');
  $('#listeClasses').innerHTML = D.classes.map(c => `
    <div class="classe apparait" style="--c:${c.couleur}">
      <div class="lettre">${esc(c.nom[0])}</div>
      <h3>${esc(c.nom)}</h3><div class="res">${esc(c.ressource)}</div>
      <p>${esc(c.desc)}</p>
      <div class="specs">${c.specs.map(s => `<span>${esc(s)}</span>`).join('')}</div>
    </div>`).join('');
  $('#quatriemes').innerHTML = D.quatriemes.map(q => `<div class="apparait"><span>${esc(q[0])}</span><b>${esc(q[1])}</b></div>`).join('');
  $('#etapes').innerHTML = D.etapes.map(e => `<div class="etape apparait"><h3>${esc(e.titre)}</h3><p>${esc(e.texte)}</p></div>`).join('');

  // braises
  const b = $('#braises');
  for (let i = 0; i < 38; i++) {
    const e = document.createElement('i');
    if (i % 3 === 0) e.className = 'bleu';
    e.style.left = Math.random() * 100 + '%';
    e.style.animationDuration = (9 + Math.random() * 12) + 's';
    e.style.animationDelay = (-Math.random() * 20) + 's';
    e.style.setProperty('--dx', (Math.random() * 120 - 60) + 'px');
    const t = 2 + Math.random() * 3; e.style.width = e.style.height = t + 'px';
    b.appendChild(e);
  }

  // apparition au défilement
  const io = new IntersectionObserver(es => es.forEach(x => { if (x.isIntersecting) { x.target.classList.add('vu'); io.unobserve(x.target); } }), { threshold: .15 });
  document.querySelectorAll('.apparait').forEach((el, i) => { el.style.transitionDelay = (i % 4) * 90 + 'ms'; io.observe(el); });

  // état du serveur
  async function statut() {
    try {
      const s = await (await fetch('/api/statut')).json();
      $('#statut').innerHTML = `<span class="pastille ${s.enLigne ? 'on' : 'off'}"></span>${s.enLigne ? 'Royaume en ligne' : 'Royaume hors ligne'}`;
      $('#nJoueurs').textContent = s.joueurs; $('#nComptes').textContent = s.comptes;
    } catch { $('#statut').innerHTML = '<span class="pastille off"></span>Portail injoignable'; }
  }
  statut(); setInterval(statut, 30000);

  // actus
  fetch('/news.json').then(r => r.json()).then(l => {
    $('#listeActus').innerHTML = l.slice(0, 6).map(a => `<article class="actu apparait vu"><time>${esc(a.date)}</time><h3>${esc(a.titre)}</h3><p>${esc(a.texte)}</p></article>`).join('');
  }).catch(() => { });

  // inscription
  $('#formInscription').addEventListener('submit', async ev => {
    ev.preventDefault();
    const m = $('#iMsg'), nom = $('#iNom').value.trim(), mdp = $('#iMdp').value;
    m.className = 'msg';
    if (mdp !== $('#iMdp2').value) { m.className = 'msg err'; m.textContent = 'Les deux mots de passe ne correspondent pas.'; return; }
    m.textContent = 'Création du compte…';
    try {
      const r = await (await fetch('/api/inscription', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nom, motdepasse: mdp }) })).json();
      m.className = 'msg ' + (r.ok ? 'ok' : 'err');
      m.textContent = r.ok ? r.message + ' Télécharge le launcher pour jouer.' : r.message;
      if (r.ok) { ev.target.reset(); statut(); }
    } catch { m.className = 'msg err'; m.textContent = 'Le portail ne répond pas, réessaie plus tard.'; }
  });
})();
