(function () {
  const D = window.DATA, $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const wv = window.chrome && window.chrome.webview;
  const envoyer = o => wv && wv.postMessage(o);
  const NOM = document.title;
  const taille = o => o >= 1073741824 ? (o / 1073741824).toFixed(2) + ' Go' : o >= 1048576 ? (o / 1048576).toFixed(1) + ' Mo' : Math.max(1, Math.round(o / 1024)) + ' Ko';

  // ---------------------------------------------------------------- contenu
  $('#accroche').textContent = D.accroche;
  $('#atouts').innerHTML = D.atouts.map(a => `<div class="atout">${ICONES[a.icone]}<h3>${esc(a.titre)}</h3><p>${esc(a.texte)}</p></div>`).join('');
  $('#listeClasses').innerHTML = D.classes.map(c => `<div class="classe" style="--c:${c.couleur}"><h3>${esc(c.nom)}</h3><p>${esc(c.desc)}</p><div class="specs">${c.specs.map(s => `<span>${esc(s)}</span>`).join('')}</div></div>`).join('');
  $('#quatriemes').innerHTML = D.quatriemes.map(q => `<div><span>${esc(q[0])}</span><b>${esc(q[1])}</b></div>`).join('');
  fetch('/news.json').then(r => r.json()).then(l => {
    $('#listeActus').innerHTML = l.map(a => `<article class="actu"><time>${esc(a.date)}</time><h3>${esc(a.titre)}</h3><p>${esc(a.texte)}</p></article>`).join('');
  }).catch(() => { });
  document.querySelectorAll('#onglets button').forEach(b => b.onclick = () => {
    document.querySelectorAll('#onglets button').forEach(x => x.classList.toggle('on', x === b));
    document.querySelectorAll('.panneau').forEach(p => p.classList.toggle('on', p.id === 'p-' + b.dataset.o));
  });
  const br = $('#braises');
  for (let i = 0; i < 26; i++) {
    const e = document.createElement('i'); if (i % 3 === 0) e.className = 'bleu';
    e.style.left = Math.random() * 100 + '%'; e.style.animationDuration = (10 + Math.random() * 12) + 's';
    e.style.animationDelay = (-Math.random() * 20) + 's'; e.style.setProperty('--dx', (Math.random() * 100 - 50) + 'px');
    br.appendChild(e);
  }

  // ---------------------------------------------------------------- fenêtre
  $('#titre').addEventListener('mousedown', e => { if (!e.target.closest('button') && e.button === 0) envoyer({ cmd: 'fenetre', action: 'deplacer' }); });
  document.querySelectorAll('.fen').forEach(b => b.onclick = () => envoyer({ cmd: 'fenetre', action: b.dataset.a }));
  $('#ouvrirSite').onclick = () => envoyer({ cmd: 'ouvrir', url: location.origin + '/' });

  // ---------------------------------------------------------------- statut
  async function statut() {
    try {
      const s = await (await fetch('/api/statut')).json();
      $('#statut').innerHTML = `<span class="pastille ${s.enLigne ? 'on' : 'off'}"></span>${s.enLigne ? 'Royaume en ligne' : 'Royaume hors ligne'}`;
      $('#nJoueurs').textContent = s.joueurs; $('#nBots').textContent = s.bots;
    } catch { $('#statut').innerHTML = '<span class="pastille off"></span>Portail injoignable'; }
  }
  statut(); setInterval(statut, 30000);

  // ---------------------------------------------------------------- compte
  let compte = '';
  document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => {
    document.querySelectorAll('.tabs button').forEach(x => x.classList.toggle('on', x === b));
    $('#formConnexion').hidden = b.dataset.t !== 'connexion';
    $('#formInscription').hidden = b.dataset.t !== 'inscription';
  });
  function afficherCompte(nom, persos) {
    compte = nom || '';
    $('#vueConnexion').hidden = !!compte;
    $('#vueCompte').hidden = !compte;
    if (!compte) return;
    $('#nomCompte').textContent = compte;
    $('#avatar').textContent = compte[0];
    const p = $('#persos');
    if (persos && persos.length)
      p.innerHTML = persos.map(x => `<div class="perso"><b>${esc(x.nom)}</b><span>${esc(CLASSES[x.classe] || '')} niv. ${x.niveau}</span></div>`).join('');
    else if (persos) p.innerHTML = '<div class="doux petit">Aucun personnage pour l\'instant : crée-le dans le jeu.</div>';
    else p.innerHTML = '';
    majBouton();
  }
  async function api(url, corps) {
    return (await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) })).json();
  }
  $('#formConnexion').onsubmit = async e => {
    e.preventDefault();
    const m = $('#cMsg'); m.className = 'msg'; m.textContent = 'Connexion…';
    try {
      const r = await api('/api/connexion', { nom: $('#cNom').value.trim(), motdepasse: $('#cMdp').value });
      if (!r.ok) { m.className = 'msg err'; m.textContent = r.message; return; }
      m.textContent = ''; $('#cMdp').value = '';
      envoyer({ cmd: 'compte', nom: r.nom });
      afficherCompte(r.nom, r.persos);
    } catch { m.className = 'msg err'; m.textContent = 'Le portail ne répond pas.'; }
  };
  $('#formInscription').onsubmit = async e => {
    e.preventDefault();
    const m = $('#iMsg'); m.className = 'msg';
    if ($('#iMdp').value !== $('#iMdp2').value) { m.className = 'msg err'; m.textContent = 'Les mots de passe ne correspondent pas.'; return; }
    m.textContent = 'Création…';
    try {
      const r = await api('/api/inscription', { nom: $('#iNom').value.trim(), motdepasse: $('#iMdp').value });
      if (!r.ok) { m.className = 'msg err'; m.textContent = r.message; return; }
      m.textContent = '';
      envoyer({ cmd: 'compte', nom: r.nom });
      afficherCompte(r.nom, []);
      statut();
    } catch { m.className = 'msg err'; m.textContent = 'Le portail ne répond pas.'; }
  };
  $('#deconnexion').onclick = () => { envoyer({ cmd: 'compte', nom: '' }); afficherCompte(''); };

  // ---------------------------------------------------------------- jeu
  let etat = { installe: false, dossier: '' }, aTelecharger = null, occupe = false;
  const bouton = $('#action');
  function progres(etape, fait, total, detail) {
    $('#etape').textContent = etape;
    $('#barre').style.width = total > 0 ? Math.min(100, fait * 100 / total).toFixed(1) + '%' : '0';
    $('#detail').textContent = detail || '';
  }
  function majBouton() {
    bouton.classList.remove('annuler');
    if (occupe) { bouton.textContent = 'Annuler'; bouton.classList.add('annuler'); bouton.disabled = false; return; }
    if (aTelecharger === null) { bouton.textContent = '…'; bouton.disabled = true; return; }
    bouton.disabled = false;
    if (aTelecharger.fichiers > 0) bouton.textContent = etat.installe ? 'Mettre à jour' : 'Installer';
    else bouton.textContent = 'Jouer';
  }
  bouton.onclick = () => {
    if (occupe) { envoyer({ cmd: 'annuler' }); return; }
    if (!aTelecharger) return;
    if (aTelecharger.fichiers > 0) { occupe = true; majBouton(); envoyer({ cmd: 'installer' }); return; }
    if (!compte) { progres('Connecte-toi ou crée un compte à droite pour jouer.', 0, 0); $('#cNom').focus(); return; }
    envoyer({ cmd: 'jouer', compte });
  };
  $('#changerDossier').onclick = () => { if (!occupe) envoyer({ cmd: 'dossier' }); };

  if (!wv) { progres('Ouvre cette page depuis le launcher pour installer et jouer.', 0, 0); return; }
  wv.addEventListener('message', ev => {
    const m = ev.data;
    switch (m.type) {
      case 'etat':
        const change = etat.dossier && etat.dossier !== m.dossier;
        etat = m;
        $('#dossier').textContent = m.dossier;
        if (m.compte && !compte) afficherCompte(m.compte, null);
        if (change || aTelecharger === null) { occupe = true; majBouton(); envoyer({ cmd: 'verifier' }); }
        break;
      case 'progres':
        progres(m.etape, m.fait, m.total, m.total ? taille(m.fait) + ' / ' + taille(m.total) + (m.debit ? ' · ' + taille(m.debit) + '/s' : '') : '');
        break;
      case 'verif':
        aTelecharger = m; occupe = false;
        if (m.fichiers > 0) progres(etat.installe ? `Mise à jour disponible : ${m.fichiers} fichier(s), ${taille(m.octets)}` : `Le jeu n'est pas encore installé : ${taille(m.octets)} à télécharger`, 0, 0);
        majBouton();
        break;
      case 'fini':
        occupe = false; aTelecharger = { fichiers: 0, octets: 0 };
        progres('Le jeu est à jour. Bon jeu !', 1, 1);
        majBouton();
        break;
      case 'annule':
        occupe = false; progres('Téléchargement en pause. Il reprendra où il s\'est arrêté.', 0, 0); majBouton();
        break;
      case 'erreur':
        occupe = false; progres(m.message, 0, 0); majBouton();
        break;
      case 'lance':
        progres('Le jeu démarre… entre ton mot de passe sur l\'écran de connexion.', 1, 1);
        break;
    }
  });
  envoyer({ cmd: 'etat', nom: NOM });
})();
