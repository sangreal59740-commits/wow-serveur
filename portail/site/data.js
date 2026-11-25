// Contenu partagé par le site et le launcher
window.DATA = {
  accroche: "WoW Classic 1.12, réinventé entre amis",
  intro: "Un royaume privé construit pièce par pièce : de nouvelles classes, une quatrième spécialisation pour chacune, un monde peuplé de bots qui jouent comme des joueurs, et des addons faits maison. Tout le contenu d'origine est là, avec ce qu'on a toujours rêvé d'y ajouter.",
  atouts: [
    { titre: "6 nouvelles classes", texte: "Nécromancien, Sniper, Métamorphe, Tisserand de vie, Fossoyeur et Martyr, avec leurs sorts, leurs arbres de talents et leurs maîtres de classe.", icone: "classes" },
    { titre: "4 spécialisations", texte: "Chaque classe gagne une quatrième voie : Berserker, Soleil, Fantôme, Ruines, Transfuge… Tank, soin, DPS ou soutien.", icone: "specs" },
    { titre: "Un monde vivant", texte: "Des centaines de bots parcourent Azeroth, font leurs quêtes et leurs donjons. Invoque tes compagnons et garde leur progression.", icone: "bots" },
    { titre: "Addons maison", texte: "Damage meter, guide de quêtes, flèche de suivi, hôtel des ventes amélioré, chronos de DoT : livrés et à jour automatiquement.", icone: "addons" }
  ],
  classes: [
    { nom: "Nécromancien", couleur: "#7fd16b", ressource: "Mana", desc: "Relève les morts et maudit les vivants.", specs: ["Invocateur", "Malédiction", "Magicien"] },
    { nom: "Sniper", couleur: "#c9a66b", ressource: "Mana", desc: "Tireur d'élite, dresseur et ingénieur de précision.", specs: ["Tireur d'élite", "Bestial", "Mécanisme"] },
    { nom: "Métamorphe", couleur: "#6fb7e8", ressource: "Mana", desc: "Esprit animal et forme angélique.", specs: ["Totémique", "Druidique", "Angélique"] },
    { nom: "Tisserand de vie", couleur: "#9fe0ff", ressource: "Mana", desc: "Noue des fils de vie pour soigner, lier ou trancher.", specs: ["Trame", "Lien", "Fil tranchant", "Moire"] },
    { nom: "Fossoyeur", couleur: "#a58b6f", ressource: "Mana et énergie", desc: "Creuse les tombes, réveille les morts, guide les âmes.", specs: ["Profanateur", "Requiem", "Charnier", "Passeur"] },
    { nom: "Martyr", couleur: "#d0454c", ressource: "Énergie et sang", desc: "Paie ses plus grands sorts avec sa propre vie.", specs: ["Bastion", "Saignée", "Offrande", "Hémophage"] }
  ],
  quatriemes: [
    ["Guerrier", "Berserker"], ["Paladin", "Soleil"], ["Chasseur", "Infirmier"], ["Voleur", "Fantôme"],
    ["Prêtre", "Corrompu"], ["Chaman", "Ruines"], ["Mage", "Nature"], ["Démoniste", "Transfuge"]
  ],
  etapes: [
    { titre: "Crée ton compte", texte: "Ici ou directement dans le launcher. Un nom, un mot de passe, c'est tout." },
    { titre: "Télécharge le launcher", texte: "Il installe le jeu au premier lancement, puis récupère seul chaque mise à jour." },
    { titre: "Joue", texte: "Clique sur Jouer, entre ton mot de passe et choisis ton royaume." }
  ]
};

window.ICONES = {
  classes: '<svg viewBox="0 0 24 24"><path d="M12 2l3 6 6 1-4.5 4.3 1 6.2L12 16.6 6.5 19.5l1-6.2L3 9l6-1z"/></svg>',
  specs: '<svg viewBox="0 0 24 24"><path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/></svg>',
  bots: '<svg viewBox="0 0 24 24"><path d="M12 2a3 3 0 110 6 3 3 0 010-6zM5 7a2.5 2.5 0 110 5 2.5 2.5 0 010-5zm14 0a2.5 2.5 0 110 5 2.5 2.5 0 010-5zM12 9c3.3 0 6 2.2 6 5v6H6v-6c0-2.8 2.7-5 6-5zM2 21v-4c0-1.8 1.3-3.3 3-3.8V21zm20 0h-3v-7.8c1.7.5 3 2 3 3.8z"/></svg>',
  addons: '<svg viewBox="0 0 24 24"><path d="M20 13h-2V9a2 2 0 00-2-2h-4V5a3 3 0 10-6 0v2H4v5h2a3 3 0 010 6H4v4h12a2 2 0 002-2v-3h2a3 3 0 000-6z"/></svg>'
};

window.RACES = { 1: "Humain", 2: "Orc", 3: "Nain", 4: "Elfe de la nuit", 5: "Mort-vivant", 6: "Tauren", 7: "Gnome", 8: "Troll" };
window.CLASSES = { 1: "Guerrier", 2: "Paladin", 3: "Chasseur", 4: "Voleur", 5: "Prêtre", 6: "Nécromancien", 7: "Chaman", 8: "Mage", 9: "Démoniste", 10: "Sniper", 11: "Métamorphe", 12: "Tisserand", 13: "Fossoyeur", 14: "Martyr" };
