-- Compagnons : galerie des 32 compagnons, fiche (équipement modifiable, talents) et boutique en jeu.
-- Même thème que le launcher (fond nuit, filets dorés). Deux boutons ajoutés dans la barre du bas, après Talents.
-- Le serveur (module compagnons) répond aux commandes .cpg par des messages « ##CPG ... », lus puis masqués :
--   L <solde> <id:actif;...>        compagnons possédés par ce personnage
--   F <id>|<niv>|<points>|<rangs>A/M|<stats>   fiche
--   G <id>|<cou,anneau1,anneau2,bijou1,bijou2>|<orbe1,orbe2>|<artefact1,artefact2>|<actif>
--   S <solde>   A <id>|<catégorie>|<nom>|<prix>|<qualité>|<type>|<objet>|<description>   B (fin du catalogue)

local D = Compagnons_Donnees
local NB = 32
local POLICE_TITRE = "Fonts\\MORPHEUS.TTF"
local POLICE = "Fonts\\FRIZQT__.TTF"
local OR = { 0.85, 0.70, 0.42 }
local OR_CLAIR = { 0.95, 0.85, 0.64 }
local GRIS = { 0.60, 0.63, 0.71 }
local TEXTE = { 0.91, 0.89, 0.82 }
local VERT = { 0.35, 0.85, 0.45 }
local CYAN = { 0.35, 0.78, 0.86 }
local QUAL = { [0] = { 0.64, 0.64, 0.64 }, { 0.31, 0.82, 0.42 }, { 0.31, 0.64, 1 }, { 0.72, 0.49, 1 }, { 1, 0.62, 0.18 } }
local QUALNOM = { [0] = "Gris", "Vert", "Bleu", "Épique", "Légendaire" }
local QUALCAT = { commun = { 0.78, 0.78, 0.78 }, peu = { 0.25, 0.85, 0.29 }, rare = { 0.31, 0.64, 1 }, epique = { 0.70, 0.42, 1 }, legendaire = { 1, 0.62, 0.18 } }

-- icônes de classe (classes de base : planche des classes ; classes custom : icône de sort)
local CLASSES = "Interface\\Glues\\CharacterCreate\\UI-CharacterCreate-Classes"
local ICONE_CLASSE = {
	[1] = { 0, 0.25, 0, 0.25 }, [8] = { 0.25, 0.49609375, 0, 0.25 }, [4] = { 0.49609375, 0.7421875, 0, 0.25 },
	[11] = { 0.7421875, 0.98828125, 0, 0.25 }, [3] = { 0, 0.25, 0.25, 0.5 }, [7] = { 0.25, 0.49609375, 0.25, 0.5 },
	[5] = { 0.49609375, 0.7421875, 0.25, 0.5 }, [9] = { 0.7421875, 0.98828125, 0.25, 0.5 }, [2] = { 0, 0.25, 0.5, 0.75 },
}
local ICONE_CUSTOM = {
	[6] = "Interface\\Icons\\Spell_Shadow_RaiseDead", [10] = "Interface\\Icons\\INV_Weapon_Rifle_01",
	[12] = "Interface\\Icons\\Spell_Nature_Web", [13] = "Interface\\Icons\\INV_Misc_Bone_HumanSkull_01",
	[14] = "Interface\\Icons\\Spell_Shadow_LifeDrain02",
}
local function IconeClasse(tex, classe)
	if ICONE_CLASSE[classe] then
		local c = ICONE_CLASSE[classe]
		tex:SetTexture(CLASSES)
		tex:SetTexCoord(c[1], c[2], c[3], c[4])
	else
		tex:SetTexture(ICONE_CUSTOM[classe] or "Interface\\Icons\\INV_Misc_QuestionMark")
		tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
	end
end

-- ------------------------------------------------------------------ état
local etat = {
	solde = 0, possedes = {}, actifs = {}, nbPossedes = 0,
	rarete = -1, seulementPossedes = false,
	fiche = nil, page = 1,               -- compagnon affiché, page de la fiche (1 équipement, 2 talents)
	f = {}, g = {},                      -- dernières réponses F et G
	catalogue = {}, categories = {}, categorie = nil, catalogueNouveau = nil,
}

local function Commande(txt)
	SendChatMessage(txt, "SAY")
end

local function Couper(s, sep)
	local t, debut = {}, 1
	while true do
		local i = string.find(s, sep, debut, true)
		if not i then
			table.insert(t, string.sub(s, debut))
			return t
		end
		table.insert(t, string.sub(s, debut, i - 1))
		debut = i + string.len(sep)
	end
end

local function Milliers(n)
	local s = tostring(math.floor(n or 0))
	local r = ""
	while string.len(s) > 3 do
		r = " " .. string.sub(s, -3) .. r
		s = string.sub(s, 1, -4)
	end
	return s .. r
end

local function Majuscule(s)
	return string.upper(string.sub(s, 1, 1)) .. string.sub(s, 2)
end

local function Texture(id)
	if not id or id == 0 then return nil end
	local r = { GetItemInfo(id) }
	for i = 1, table.getn(r) do
		if type(r[i]) == "string" and string.find(r[i], "^Interface") then return r[i] end
	end
	return nil
end
local scan = CreateFrame("GameTooltip", "CompagnonsScan", nil, "GameTooltipTemplate")
local function Demander(id)
	if id and id ~= 0 and not GetItemInfo(id) then
		scan:SetOwner(WorldFrame, "ANCHOR_NONE")
		scan:SetHyperlink("item:" .. id .. ":0:0:0")
	end
end

-- ------------------------------------------------------------------ outils d'interface
local function Lumiere(b, r, g, bl, a)
	local h = b:CreateTexture(nil, "HIGHLIGHT")
	h:SetTexture("Interface\\Buttons\\UI-Listbox-Highlight2")
	h:SetBlendMode("ADD")
	h:SetPoint("TOPLEFT", b, "TOPLEFT", 3, -3)
	h:SetPoint("BOTTOMRIGHT", b, "BOTTOMRIGHT", -3, 3)
	h:SetVertexColor(r, g, bl, a)
end

local function Desature(t, oui)
	if t.SetDesaturated then t:SetDesaturated(oui) end
end

local function Fond(f, r, g, b, a, bord)
	f:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
		tile = false, edgeSize = 12, insets = { left = 3, right = 3, top = 3, bottom = 3 } })
	f:SetBackdropColor(r, g, b, a)
	local c = bord or OR
	f:SetBackdropBorderColor(c[1], c[2], c[3], c[4] or 0.55)
end

local function Texte(parent, taille, couleur, police, couche)
	local t = parent:CreateFontString(nil, couche or "OVERLAY")
	t:SetFont(police or POLICE, taille)
	local c = couleur or TEXTE
	t:SetTextColor(c[1], c[2], c[3])
	t:SetShadowColor(0, 0, 0, 1)
	t:SetShadowOffset(1, -1)
	return t
end

local function Bouton(parent, largeur, hauteur, texte, principal)
	local b = CreateFrame("Button", nil, parent)
	b:SetWidth(largeur)
	b:SetHeight(hauteur)
	if principal then
		Fond(b, 0.72, 0.55, 0.27, 0.95, OR_CLAIR)
	else
		Fond(b, 0, 0, 0, 0.35, OR)
	end
	b.t = Texte(b, principal and 13 or 11, principal and { 0.10, 0.08, 0.03 } or OR, principal and POLICE_TITRE or POLICE)
	b.t:SetPoint("CENTER", b, "CENTER", 0, 0)
	b.t:SetText(texte)
	Lumiere(b, OR[1], OR[2], OR[3], 0.25)
	return b
end

local function Pastille(b, actif, c)
	if actif then
		b:SetBackdropColor(c[1], c[2], c[3], 0.9)
		b:SetBackdropBorderColor(c[1], c[2], c[3], 1)
		b.t:SetTextColor(0.04, 0.04, 0.06)
	else
		b:SetBackdropColor(0, 0, 0, 0.35)
		b:SetBackdropBorderColor(c[1], c[2], c[3], 0.45)
		b.t:SetTextColor(c[1], c[2], c[3])
	end
end

local function Cadre(nom, largeur, hauteur, titre)
	local f = CreateFrame("Frame", nom, UIParent)
	f:SetWidth(largeur)
	f:SetHeight(hauteur)
	f:SetPoint("CENTER", UIParent, "CENTER", 0, 40)
	f:SetFrameStrata("HIGH")
	f:SetToplevel(true)
	f:EnableMouse(true)
	f:SetMovable(true)
	f:SetClampedToScreen(true)
	Fond(f, 0.04, 0.05, 0.09, 0.96, { OR[1], OR[2], OR[3], 0.8 })
	-- dégradé discret : halo cyan en haut, or en bas
	local h = f:CreateTexture(nil, "BORDER")
	h:SetTexture("Interface\\Buttons\\WHITE8X8")
	h:SetPoint("TOPLEFT", f, "TOPLEFT", 4, -4)
	h:SetPoint("TOPRIGHT", f, "TOPRIGHT", -4, -4)
	h:SetHeight(hauteur * 0.45)
	h:SetGradientAlpha("VERTICAL", 0.06, 0.08, 0.16, 0, 0.20, 0.45, 0.55, 0.14)
	local b = f:CreateTexture(nil, "BORDER")
	b:SetTexture("Interface\\Buttons\\WHITE8X8")
	b:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", 4, 4)
	b:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -4, 4)
	b:SetHeight(hauteur * 0.4)
	b:SetGradientAlpha("VERTICAL", 0.55, 0.42, 0.22, 0.12, 0.06, 0.05, 0.09, 0)
	-- en-tête
	local tete = CreateFrame("Frame", nil, f)
	tete:SetPoint("TOPLEFT", f, "TOPLEFT", 4, -4)
	tete:SetPoint("TOPRIGHT", f, "TOPRIGHT", -4, -4)
	tete:SetHeight(40)
	tete:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8" })
	tete:SetBackdropColor(0, 0, 0, 0.4)
	tete:EnableMouse(true)
	tete:RegisterForDrag("LeftButton")
	tete:SetScript("OnDragStart", function() f:StartMoving() end)
	tete:SetScript("OnDragStop", function() f:StopMovingOrSizing() end)
	local filet = tete:CreateTexture(nil, "ARTWORK")
	filet:SetTexture("Interface\\Buttons\\WHITE8X8")
	filet:SetVertexColor(OR[1], OR[2], OR[3], 0.3)
	filet:SetHeight(1)
	filet:SetPoint("BOTTOMLEFT", tete, "BOTTOMLEFT", 0, 0)
	filet:SetPoint("BOTTOMRIGHT", tete, "BOTTOMRIGHT", 0, 0)
	f.titre = Texte(tete, 18, OR_CLAIR, POLICE_TITRE)
	f.titre:SetPoint("LEFT", tete, "LEFT", 16, 0)
	f.titre:SetText(titre)
	f.sous = Texte(tete, 11, GRIS)
	f.sous:SetPoint("LEFT", f.titre, "RIGHT", 12, -1)
	-- solde
	local s = CreateFrame("Frame", nil, tete)
	s:SetWidth(150)
	s:SetHeight(26)
	s:SetPoint("RIGHT", tete, "RIGHT", -40, 0)
	Fond(s, 0, 0, 0, 0.35, { OR[1], OR[2], OR[3], 0.35 })
	local sl = Texte(s, 9, GRIS)
	sl:SetPoint("LEFT", s, "LEFT", 10, 0)
	sl:SetText("SOLDE")
	f.solde = Texte(s, 14, OR_CLAIR, POLICE_TITRE)
	f.solde:SetPoint("RIGHT", s, "RIGHT", -10, 0)
	local x = CreateFrame("Button", nil, tete, "UIPanelCloseButton")
	x:SetPoint("RIGHT", tete, "RIGHT", 2, 0)
	x:SetScript("OnClick", function() f:Hide() end)
	f.tete = tete
	f:Hide()
	table.insert(UISpecialFrames, nom)
	return f
end

-- ------------------------------------------------------------------ galerie
local G = Cadre("CompagnonsFrame", 790, 590, "Compagnons")
G.galerie = CreateFrame("Frame", nil, G)
G.galerie:SetPoint("TOPLEFT", G, "TOPLEFT", 0, -44)
G.galerie:SetPoint("BOTTOMRIGHT", G, "BOTTOMRIGHT", 0, 0)

local FILTRES = { { -1, "Tous", OR }, { 0, "Gris", QUAL[0] }, { 1, "Vert", QUAL[1] }, { 2, "Bleu", QUAL[2] }, { 3, "Épique", QUAL[3] }, { 4, "Légendaire", QUAL[4] } }
G.filtres = {}
local precedent
for i = 1, table.getn(FILTRES) do
	local d = FILTRES[i]
	local b = Bouton(G.galerie, 78, 24, d[2])
	if precedent then
		b:SetPoint("LEFT", precedent, "RIGHT", 6, 0)
	else
		b:SetPoint("TOPLEFT", G.galerie, "TOPLEFT", 18, -10)
	end
	b.r, b.c = d[1], d[3]
	b:SetScript("OnClick", function()
		etat.rarete = this.r
		Compagnons_MajGalerie()
	end)
	G.filtres[i] = b
	precedent = b
end
G.possedes = Bouton(G.galerie, 140, 24, "Possédés seulement")
G.possedes:SetPoint("TOPRIGHT", G.galerie, "TOPRIGHT", -18, -10)
G.possedes:SetScript("OnClick", function()
	etat.seulementPossedes = not etat.seulementPossedes
	Compagnons_MajGalerie()
end)

G.cartes = {}
local CL, CH, ESP = 89, 120, 6
for i = 1, NB do
	local c = CreateFrame("Button", nil, G.galerie)
	c:SetWidth(CL)
	c:SetHeight(CH)
	local col, lig = math.mod(i - 1, 8), math.floor((i - 1) / 8)
	c:SetPoint("TOPLEFT", G.galerie, "TOPLEFT", 18 + col * (CL + ESP), -44 - lig * (CH + ESP))
	Fond(c, 0.06, 0.07, 0.11, 0.8)
	c.halo = c:CreateTexture(nil, "BORDER")
	c.halo:SetTexture("Interface\\Buttons\\WHITE8X8")
	c.halo:SetPoint("TOPLEFT", c, "TOPLEFT", 4, -4)
	c.halo:SetPoint("TOPRIGHT", c, "TOPRIGHT", -4, -4)
	c.halo:SetHeight(50)
	c.ic = c:CreateTexture(nil, "ARTWORK")
	c.ic:SetWidth(36)
	c.ic:SetHeight(36)
	c.ic:SetPoint("TOP", c, "TOP", 0, -10)
	c.cadre = c:CreateTexture(nil, "OVERLAY")
	c.cadre:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
	c.cadre:SetBlendMode("ADD")
	c.cadre:SetWidth(66)
	c.cadre:SetHeight(66)
	c.cadre:SetPoint("CENTER", c.ic, "CENTER", 0, 0)
	c.nom = Texte(c, 10, TEXTE)
	c.nom:SetWidth(CL - 8)
	c.nom:SetHeight(24)
	c.nom:SetPoint("TOP", c.ic, "BOTTOM", 0, -3)
	c.spe = Texte(c, 8, { 0.71, 0.73, 0.78 })
	c.spe:SetWidth(CL - 6)
	c.spe:SetPoint("TOP", c.nom, "BOTTOM", 0, -1)
	c.role = Texte(c, 8, { 0.55, 0.58, 0.65 })
	c.role:SetPoint("TOP", c.spe, "BOTTOM", 0, -2)
	c.pied = Texte(c, 10, OR_CLAIR, POLICE_TITRE)
	c.pied:SetPoint("BOTTOM", c, "BOTTOM", 0, 7)
	local trait = c:CreateTexture(nil, "ARTWORK")
	trait:SetTexture("Interface\\Buttons\\WHITE8X8")
	trait:SetVertexColor(1, 1, 1, 0.07)
	trait:SetHeight(1)
	trait:SetPoint("BOTTOMLEFT", c, "BOTTOMLEFT", 6, 22)
	trait:SetPoint("BOTTOMRIGHT", c, "BOTTOMRIGHT", -6, 22)
	Lumiere(c, 1, 1, 1, 0.12)
	c:SetScript("OnClick", function()
		if not this.id then return end
		if etat.possedes[this.id] then
			Compagnons_OuvrirFiche(this.id)
		else
			Compagnons_ProposerAchat("cpg_" .. D[this.id].cle, D[this.id].nom, D[this.id].prix)
		end
	end)
	c:SetScript("OnEnter", function()
		if not this.id then return end
		local d = D[this.id]
		local q = QUAL[d.rarete]
		GameTooltip:SetOwner(this, "ANCHOR_RIGHT")
		GameTooltip:SetText(d.nomComplet, q[1], q[2], q[3])
		GameTooltip:AddLine(d.spe .. " · " .. Majuscule(d.role) .. " · " .. QUALNOM[d.rarete], 1, 1, 1)
		GameTooltip:AddLine("Sorts : " .. table.concat(d.sorts, ", "), 0.8, 0.8, 0.8, 1)
		GameTooltip:AddLine("Ultime : " .. d.ultime, OR_CLAIR[1], OR_CLAIR[2], OR_CLAIR[3], 1)
		GameTooltip:AddLine(d.ultimeTxt, 0.8, 0.8, 0.8, 1)
		if etat.possedes[this.id] then
			GameTooltip:AddLine("Clic : fiche, équipement et talents", VERT[1], VERT[2], VERT[3])
		else
			GameTooltip:AddLine("Clic : acheter pour " .. Milliers(d.prix) .. " Gen", OR[1], OR[2], OR[3])
		end
		GameTooltip:Show()
	end)
	c:SetScript("OnLeave", function() GameTooltip:Hide() end)
	G.cartes[i] = c
end

function Compagnons_MajGalerie()
	G.titre:SetText("Compagnons")
	G.sous:SetText(etat.nbPossedes .. " sur " .. NB .. " possédés · 4 au maximum avec toi")
	G.solde:SetText(Milliers(etat.solde) .. " |cffd9b36cGen|r")
	for i = 1, table.getn(G.filtres) do
		local b = G.filtres[i]
		Pastille(b, etat.rarete == b.r, b.c)
	end
	Pastille(G.possedes, etat.seulementPossedes, CYAN)
	local n = 0
	for id = 1, NB do
		local d = D[id]
		if d and (etat.rarete < 0 or d.rarete == etat.rarete) and (not etat.seulementPossedes or etat.possedes[id]) then
			n = n + 1
			local c = G.cartes[n]
			local q, a = QUAL[d.rarete], etat.possedes[id]
			c.id = id
			IconeClasse(c.ic, d.classe)
			c.nom:SetText(d.nom)
			c.spe:SetText(d.spe)
			c.role:SetText(string.upper(d.role == "tout familier" and "Familiers" or d.role))
			if a then
				c:SetBackdropColor(0.09, 0.10, 0.15, 0.9)
				c:SetBackdropBorderColor(q[1], q[2], q[3], 1)
				c.halo:SetGradientAlpha("VERTICAL", q[1], q[2], q[3], 0, q[1], q[2], q[3], 0.22)
				c.cadre:SetVertexColor(q[1], q[2], q[3])
				c.cadre:SetAlpha(0.9)
				Desature(c.ic, nil)
				c.ic:SetVertexColor(1, 1, 1)
				c.nom:SetTextColor(q[1], q[2], q[3])
				if etat.actifs[id] then
					c.pied:SetText("AVEC TOI")
					c.pied:SetTextColor(VERT[1], VERT[2], VERT[3])
				else
					c.pied:SetText("POSSÉDÉ")
					c.pied:SetTextColor(q[1], q[2], q[3])
				end
				c.pied:SetFont(POLICE, 9)
			else
				c:SetBackdropColor(0.06, 0.07, 0.11, 0.8)
				c:SetBackdropBorderColor(q[1], q[2], q[3], 0.35)
				c.halo:SetGradientAlpha("VERTICAL", 0, 0, 0, 0, 0, 0, 0, 0)
				c.cadre:SetVertexColor(0.3, 0.3, 0.33)
				c.cadre:SetAlpha(0.5)
				Desature(c.ic, 1)
				c.ic:SetVertexColor(0.55, 0.55, 0.6)
				c.nom:SetTextColor(0.54, 0.56, 0.62)
				c.pied:SetFont(POLICE_TITRE, 12)
				c.pied:SetText(Milliers(d.prix) .. " Gen")
				c.pied:SetTextColor(OR_CLAIR[1], OR_CLAIR[2], OR_CLAIR[3])
			end
			c:Show()
		end
	end
	for i = n + 1, NB do
		G.cartes[i].id = nil
		G.cartes[i]:Hide()
	end
end

-- ------------------------------------------------------------------ fiche
G.fiche = CreateFrame("Frame", nil, G)
G.fiche:SetPoint("TOPLEFT", G, "TOPLEFT", 0, -44)
G.fiche:SetPoint("BOTTOMRIGHT", G, "BOTTOMRIGHT", 0, 0)
G.fiche:Hide()
G.fiche:EnableMouseWheel(true)
G.fiche:SetScript("OnMouseWheel", function()
	Compagnons_Page(arg1 < 0 and 2 or 1)
end)

local F = G.fiche
F.retour = Bouton(F, 90, 24, "< Galerie")
F.retour:SetPoint("TOPLEFT", F, "TOPLEFT", 16, -10)
F.retour:SetScript("OnClick", function()
	etat.fiche = nil
	F:Hide()
	G.galerie:Show()
	Compagnons_MajGalerie()
end)
F.ic = F:CreateTexture(nil, "ARTWORK")
F.ic:SetWidth(34)
F.ic:SetHeight(34)
F.ic:SetPoint("LEFT", F.retour, "RIGHT", 14, 0)
F.nom = Texte(F, 17, OR_CLAIR, POLICE_TITRE)
F.nom:SetPoint("TOPLEFT", F.ic, "TOPRIGHT", 10, 2)
F.info = Texte(F, 10, GRIS)
F.info:SetPoint("TOPLEFT", F.nom, "BOTTOMLEFT", 0, -3)
F.onglets = {}
for i, nom in ipairs({ "Équipement", "Talents" }) do
	local b = Bouton(F, 100, 24, nom)
	b:SetPoint("TOPRIGHT", F, "TOPRIGHT", -16 - (2 - i) * 106, -10)
	b.p = i
	b:SetScript("OnClick", function() Compagnons_Page(this.p) end)
	F.onglets[i] = b
end

-- page 1 : équipement
F.p1 = CreateFrame("Frame", nil, F)
F.p1:SetPoint("TOPLEFT", F, "TOPLEFT", 0, -50)
F.p1:SetPoint("BOTTOMRIGHT", F, "BOTTOMRIGHT", 0, 40)

local function Panneau(parent, largeur, hauteur, titre)
	local p = CreateFrame("Frame", nil, parent)
	p:SetWidth(largeur)
	p:SetHeight(hauteur)
	Fond(p, 0.05, 0.06, 0.10, 0.85, { OR[1], OR[2], OR[3], 0.3 })
	if titre then
		p.titre = Texte(p, 12, OR_CLAIR, POLICE_TITRE)
		p.titre:SetPoint("TOPLEFT", p, "TOPLEFT", 12, -10)
		p.titre:SetText(titre)
	end
	return p
end

-- stuff de base (non modifiable)
F.base = Panneau(F.p1, 200, 420, "Stuff de base")
F.base:SetPoint("TOPLEFT", F.p1, "TOPLEFT", 16, 0)
local BASE = { "Tête", "Épaules", "Dos", "Torse", "Poignets", "Mains", "Taille", "Jambes", "Pieds", "Arme" }
F.baseLignes = {}
for i = 1, table.getn(BASE) do
	local l = Texte(F.base, 11, { 0.75, 0.75, 0.78 })
	l:SetPoint("TOPLEFT", F.base, "TOPLEFT", 30, -14 - i * 30)
	l:SetText(BASE[i])
	local v = F.base:CreateTexture(nil, "ARTWORK")
	v:SetTexture("Interface\\PetitionFrame\\GuildCharter-Icon")
	v:SetWidth(12)
	v:SetHeight(12)
	v:SetPoint("RIGHT", l, "LEFT", -6, 0)
	v:SetVertexColor(0.5, 0.5, 0.55)
	local r = Texte(F.base, 10, GRIS)
	r:SetPoint("RIGHT", F.base, "RIGHT", -12, 0)
	r:SetPoint("TOP", l, "TOP", 0, 0)
	F.baseLignes[i] = r
end
F.baseAide = Texte(F.base, 9, GRIS)
F.baseAide:SetWidth(176)
F.baseAide:SetPoint("BOTTOM", F.base, "BOTTOM", 0, 12)
F.baseAide:SetText("Apparence et stuff du compagnon. Il suit ton niveau, sa force dépend de la rareté.")

-- emplacements modifiables
F.modif = Panneau(F.p1, 300, 420, "Ce que tu peux lui donner")
F.modif:SetPoint("TOPLEFT", F.base, "TOPRIGHT", 10, 0)
local EMPL = { { "Cou" }, { "Anneau 1" }, { "Anneau 2" }, { "Bijou 1" }, { "Bijou 2" }, { "Orbe 1" }, { "Orbe 2" }, { "Artefact 1" }, { "Artefact 2" } }
F.cases = {}
local dernierSac, derniereCase = nil, nil

local function Poser(empl)
	if not CursorHasItem() then return false end
	if not dernierSac or not etat.fiche then
		ClearCursor()
		return true
	end
	local sac, case = dernierSac, derniereCase
	ClearCursor()
	Commande(".cpg equiper " .. etat.fiche .. " " .. sac .. " " .. case .. " " .. empl)
	return true
end

for i = 1, 9 do
	local b = CreateFrame("Button", nil, F.modif)
	b:SetWidth(36)
	b:SetHeight(36)
	local col, lig = (i <= 5) and 0 or 1, (i <= 5) and (i - 1) or (i - 6)
	b:SetPoint("TOPLEFT", F.modif, "TOPLEFT", 14 + col * 146, -38 - lig * 52)
	local fond = b:CreateTexture(nil, "BACKGROUND")
	fond:SetTexture("Interface\\Buttons\\UI-EmptySlot-White")
	fond:SetWidth(60)
	fond:SetHeight(60)
	fond:SetPoint("CENTER", b, "CENTER", 0, 0)
	b.ic = b:CreateTexture(nil, "ARTWORK")
	b.ic:SetAllPoints(b)
	b.bord = b:CreateTexture(nil, "OVERLAY")
	b.bord:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
	b.bord:SetBlendMode("ADD")
	b.bord:SetWidth(64)
	b.bord:SetHeight(64)
	b.bord:SetPoint("CENTER", b, "CENTER", 0, 0)
	b.bord:SetVertexColor(OR[1], OR[2], OR[3])
	b.bord:SetAlpha(0.5)
	b.lib = Texte(F.modif, 9, GRIS)
	b.lib:SetPoint("TOPLEFT", b, "TOPRIGHT", 8, -2)
	b.lib:SetText(EMPL[i][1])
	b.nom = Texte(F.modif, 10, TEXTE)
	b.nom:SetWidth(92)
	b.nom:SetHeight(24)
	b.nom:SetJustifyH("LEFT")
	b.nom:SetJustifyV("TOP")
	b.nom:SetPoint("TOPLEFT", b.lib, "BOTTOMLEFT", 0, -2)
	b:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square")
	b.n = i
	b:RegisterForClicks("LeftButtonUp", "RightButtonUp")
	b:RegisterForDrag("LeftButton")
	b:SetScript("OnReceiveDrag", function() Poser(this.n) end)
	b:SetScript("OnClick", function()
		if Poser(this.n) then return end
		if arg1 == "RightButton" and this.id and this.id ~= 0 then
			Commande(".cpg retirer " .. etat.fiche .. " " .. this.n)
		end
	end)
	b:SetScript("OnEnter", function()
		GameTooltip:SetOwner(this, "ANCHOR_RIGHT")
		if this.id and this.id ~= 0 then
			GameTooltip:SetHyperlink("item:" .. this.id .. ":0:0:0")
			GameTooltip:AddLine("Clic droit : retirer", 0.6, 0.6, 0.6)
		else
			GameTooltip:SetText(EMPL[this.n][1], OR_CLAIR[1], OR_CLAIR[2], OR_CLAIR[3])
			if this.n >= 6 and this.n <= 7 then
				GameTooltip:AddLine("Orbe du compagnon : trouvée sur les élites rares et les derniers boss de donjon. Deux couleurs différentes.", 1, 1, 1, 1)
			elseif this.n >= 8 then
				GameTooltip:AddLine("Artefact : deux couleurs différentes. Les améliorations de la machine restent sur ton personnage.", 1, 1, 1, 1)
			else
				GameTooltip:AddLine("Le compagnon doit être avec toi pour changer cet objet.", 1, 1, 1, 1)
			end
			GameTooltip:AddLine("Glisse un objet ici, ou clic droit dessus dans tes sacs.", 0.6, 0.6, 0.6, 1)
		end
		GameTooltip:Show()
	end)
	b:SetScript("OnLeave", function() GameTooltip:Hide() end)
	F.cases[i] = b
end
F.modifAide = Texte(F.modif, 9, GRIS)
F.modifAide:SetWidth(270)
F.modifAide:SetPoint("BOTTOM", F.modif, "BOTTOM", 0, 50)
F.modifAide:SetText("Cou, anneaux et bijoux passent sur le compagnon (il doit être invoqué). Orbes et artefacts sont gardés par le serveur.")
F.sorts = Texte(F.modif, 9, { 0.75, 0.75, 0.78 })
F.sorts:SetWidth(270)
F.sorts:SetPoint("BOTTOM", F.modif, "BOTTOM", 0, 12)

-- caractéristiques
F.stats = Panneau(F.p1, 246, 360, "Caractéristiques")
F.stats:SetPoint("TOPLEFT", F.modif, "TOPRIGHT", 10, 0)
F.statLignes = {}
for i = 1, 13 do
	local n = Texte(F.stats, 11, GRIS)
	n:SetPoint("TOPLEFT", F.stats, "TOPLEFT", 14, -12 - i * 24)
	local v = Texte(F.stats, 11, TEXTE)
	v:SetPoint("TOPRIGHT", F.stats, "TOPRIGHT", -14, -12 - i * 24)
	F.statLignes[i] = { n, v }
end
F.invoquer = Bouton(F.p1, 246, 44, "INVOQUER", true)
F.invoquer:SetPoint("TOPLEFT", F.stats, "BOTTOMLEFT", 0, -16)
F.invoquer:SetScript("OnClick", function()
	if etat.fiche then Commande(".cpg invoquer " .. etat.fiche) end
end)

-- page 2 : talents
F.p2 = CreateFrame("Frame", nil, F)
F.p2:SetPoint("TOPLEFT", F, "TOPLEFT", 0, -50)
F.p2:SetPoint("BOTTOMRIGHT", F, "BOTTOMRIGHT", 0, 40)
F.p2:Hide()
F.points = Texte(F.p2, 13, OR_CLAIR, POLICE_TITRE)
F.points:SetPoint("TOPLEFT", F.p2, "TOPLEFT", 18, -2)
F.mode = Texte(F.p2, 10, GRIS)
F.mode:SetPoint("LEFT", F.points, "RIGHT", 12, 0)
F.reset = Bouton(F.p2, 130, 24, "Réinitialiser")
F.reset:SetPoint("TOPRIGHT", F.p2, "TOPRIGHT", -16, 2)
F.reset:SetScript("OnClick", function()
	if etat.fiche then Commande(".cpg reset " .. etat.fiche) end
end)
F.talents = {}
local function BoutonTalent(i, x, y, largeur)
	local b = CreateFrame("Button", nil, F.p2)
	b:SetWidth(largeur)
	b:SetHeight(58)
	b:SetPoint("TOPLEFT", F.p2, "TOPLEFT", x, y)
	Fond(b, 0.06, 0.07, 0.11, 0.85, { OR[1], OR[2], OR[3], 0.3 })
	b.nom = Texte(b, 12, TEXTE, POLICE_TITRE)
	b.nom:SetPoint("TOPLEFT", b, "TOPLEFT", 12, -8)
	b.rang = Texte(b, 11, OR_CLAIR)
	b.rang:SetPoint("TOPRIGHT", b, "TOPRIGHT", -12, -9)
	b.txt = Texte(b, 9, { 0.75, 0.75, 0.78 })
	b.txt:SetWidth(largeur - 24)
	b.txt:SetHeight(26)
	b.txt:SetJustifyH("LEFT")
	b.txt:SetJustifyV("TOP")
	b.txt:SetPoint("TOPLEFT", b.nom, "BOTTOMLEFT", 0, -4)
	Lumiere(b, OR[1], OR[2], OR[3], 0.2)
	b.idx = i
	b:SetScript("OnClick", function()
		if etat.fiche then Commande(".cpg talent " .. etat.fiche .. " " .. this.idx) end
	end)
	b:SetScript("OnEnter", function()
		if not etat.fiche then return end
		local d = D[etat.fiche]
		GameTooltip:SetOwner(this, "ANCHOR_RIGHT")
		if this.idx == 10 then
			GameTooltip:SetText("Ultime : " .. d.ultime, OR_CLAIR[1], OR_CLAIR[2], OR_CLAIR[3])
			GameTooltip:AddLine(d.ultimeTxt, 1, 1, 1, 1)
			GameTooltip:AddLine("Lancé tout seul par le compagnon en combat, recharge 3 min. 1 point, 20 points dans les paliers 1 à 4.", 0.7, 0.7, 0.7, 1)
		else
			local t = d.talents[this.idx + 1]
			GameTooltip:SetText(t[2], OR_CLAIR[1], OR_CLAIR[2], OR_CLAIR[3])
			GameTooltip:AddLine(t[3] .. " par rang (5 rangs)", 1, 1, 1, 1)
			if t[1] > 1 then
				GameTooltip:AddLine("Palier " .. t[1] .. " : " .. ((t[1] - 1) * 5) .. " points dans les paliers précédents.", 0.7, 0.7, 0.7, 1)
			end
		end
		GameTooltip:AddLine("Clic : ajouter un point", VERT[1], VERT[2], VERT[3])
		GameTooltip:Show()
	end)
	b:SetScript("OnLeave", function() GameTooltip:Hide() end)
	F.talents[i] = b
	return b
end
F.paliers = {}
for p = 1, 5 do
	local y = -30 - (p - 1) * 66
	local l = Texte(F.p2, 11, GRIS, POLICE_TITRE)
	l:SetPoint("TOPLEFT", F.p2, "TOPLEFT", 18, y - 20)
	l:SetText("Palier " .. p)
	F.paliers[p] = l
	BoutonTalent((p - 1) * 2, 90, y, 330)
	BoutonTalent((p - 1) * 2 + 1, 430, y, 330)
end
local u = BoutonTalent(10, 90, -30 - 5 * 66, 670)
u:SetHeight(48)
u:SetBackdropBorderColor(OR_CLAIR[1], OR_CLAIR[2], OR_CLAIR[3], 0.9)
local ul = Texte(F.p2, 11, OR_CLAIR, POLICE_TITRE)
ul:SetPoint("TOPLEFT", F.p2, "TOPLEFT", 18, -30 - 5 * 66 - 16)
ul:SetText("Ultime")

-- points de la glissière (comme le mockup)
F.points1 = F:CreateTexture(nil, "ARTWORK")
F.points2 = F:CreateTexture(nil, "ARTWORK")
for _, t in ipairs({ F.points1, F.points2 }) do
	t:SetTexture("Interface\\Buttons\\WHITE8X8")
	t:SetHeight(5)
end
F.points1:SetPoint("BOTTOM", F, "BOTTOM", -12, 18)
F.points2:SetPoint("LEFT", F.points1, "RIGHT", 6, 0)
F.glisse = Texte(F, 9, GRIS)
F.glisse:SetPoint("LEFT", F.points2, "RIGHT", 10, 0)

function Compagnons_Page(p)
	etat.page = p
	F.p1:Hide()
	F.p2:Hide()
	if p == 1 then F.p1:Show() else F.p2:Show() end
	for i = 1, 2 do Pastille(F.onglets[i], i == p, OR) end
	F.points1:SetWidth(p == 1 and 22 or 8)
	F.points2:SetWidth(p == 2 and 22 or 8)
	F.points1:SetVertexColor(OR[1], OR[2], OR[3], p == 1 and 1 or 0.25)
	F.points2:SetVertexColor(OR[1], OR[2], OR[3], p == 2 and 1 or 0.25)
	F.glisse:SetText(p == 1 and "Molette : talents" or "Molette : équipement")
end

local NOMS_STATS = {
	{ "pv", "Points de vie" }, { "endu", "Endurance" }, { "for", "Force" }, { "agi", "Agilité" }, { "int", "Intelligence" },
	{ "armure", "Armure" }, { "pa", "Puissance d'attaque" }, { "ps", "Puissance des sorts" }, { "soins", "Bonus aux soins" },
	{ "crit", "Critique", " %" }, { "toucher", "Toucher", " %" }, { "def", "Défense" },
}

function Compagnons_MajFiche()
	local id = etat.fiche
	if not id then return end
	local d = D[id]
	local q = QUAL[d.rarete]
	local f, g = etat.f, etat.g
	G.titre:SetText("Compagnons")
	G.sous:SetText("")
	G.solde:SetText(Milliers(etat.solde) .. " |cffd9b36cGen|r")
	IconeClasse(F.ic, d.classe)
	F.nom:SetText(d.nomComplet)
	F.nom:SetTextColor(q[1], q[2], q[3])
	F.info:SetText(d.spe .. " · " .. Majuscule(d.role) .. " · " .. QUALNOM[d.rarete] .. (f.niveau and (" · niveau " .. f.niveau) or ""))
	F.sorts:SetText("Sorts : " .. table.concat(d.sorts, ", "))
	-- stuff de base
	local pct = f.stats and f.stats.stuff or 100
	for i = 1, table.getn(F.baseLignes) do
		F.baseLignes[i]:SetText(pct .. " %")
	end
	-- emplacements
	local ids = {}
	if g.equip then
		for i = 1, 5 do ids[i] = g.equip[i] end
		ids[6], ids[7], ids[8], ids[9] = g.orbes[1], g.orbes[2], g.artefacts[1], g.artefacts[2]
	end
	for i = 1, 9 do
		local b = F.cases[i]
		local e = ids[i] or 0
		b.id = e
		if e ~= 0 then
			Demander(e)
			local nom, _, qual = GetItemInfo(e)
			local t = Texture(e)
			b.ic:SetTexture(t or "Interface\\Icons\\INV_Misc_QuestionMark")
			b.ic:SetAlpha(1)
			b.nom:SetText(nom or "...")
			local r, gg, bb = GetItemQualityColor(qual or 1)
			b.nom:SetTextColor(r, gg, bb)
			b.bord:SetVertexColor(r, gg, bb)
			b.bord:SetAlpha(0.9)
		else
			b.ic:SetTexture(nil)
			b.nom:SetText("Libre")
			b.nom:SetTextColor(0.5, 0.52, 0.58)
			b.bord:SetVertexColor(OR[1], OR[2], OR[3])
			b.bord:SetAlpha(0.45)
		end
	end
	-- caractéristiques
	local n = 1
	local function Ligne(nom, val)
		if n > table.getn(F.statLignes) then return end
		F.statLignes[n][1]:SetText(nom)
		F.statLignes[n][2]:SetText(val)
		n = n + 1
	end
	Ligne("Puissance des sorts", (f.stats and f.stats.puissance or "?") .. " %")
	for i = 1, table.getn(NOMS_STATS) do
		local s = NOMS_STATS[i]
		local v = f.stats and f.stats[s[1]]
		if v and (v ~= 0 or s[1] == "endu") then
			Ligne(s[2], (s[3] and "" or "+") .. Milliers(v) .. (s[3] or ""))
		end
	end
	for i = n, table.getn(F.statLignes) do
		F.statLignes[i][1]:SetText("")
		F.statLignes[i][2]:SetText("")
	end
	local actif = g.actif or etat.actifs[id]
	F.invoquer.t:SetText(actif and "RENVOYER" or "INVOQUER")
	-- talents
	local rangs = f.rangs or {}
	local total = 0
	for i = 0, 10 do total = total + (rangs[i] or 0) end
	F.points:SetText("Points : " .. total .. " / " .. (f.points or 0))
	F.mode:SetText(f.auto and "Répartition automatique tant que tu n'as rien choisi" or "")
	local parPalier = {}
	for i = 0, 9 do
		local p = d.talents[i + 1][1]
		parPalier[p] = (parPalier[p] or 0) + (rangs[i] or 0)
	end
	for i = 0, 10 do
		local b = F.talents[i]
		local r = rangs[i] or 0
		local max = i == 10 and 1 or 5
		local palier = i == 10 and 5 or d.talents[i + 1][1]
		local avant = 0
		for p = 1, palier - 1 do avant = avant + (parPalier[p] or 0) end
		if i == 10 then
			avant = 0
			for p = 1, 4 do avant = avant + (parPalier[p] or 0) end
			b.nom:SetText(d.ultime)
			b.txt:SetText(d.ultimeTxt)
		else
			b.nom:SetText(d.talents[i + 1][2])
			b.txt:SetText(d.talents[i + 1][3] .. " par rang")
		end
		b.rang:SetText(r .. " / " .. max)
		local ouvert = avant >= 5 * (palier - 1)
		if r > 0 then
			b:SetBackdropBorderColor(q[1], q[2], q[3], 1)
			b.nom:SetTextColor(q[1], q[2], q[3])
			b.rang:SetTextColor(VERT[1], VERT[2], VERT[3])
		elseif ouvert then
			b:SetBackdropBorderColor(OR[1], OR[2], OR[3], 0.5)
			b.nom:SetTextColor(TEXTE[1], TEXTE[2], TEXTE[3])
			b.rang:SetTextColor(OR_CLAIR[1], OR_CLAIR[2], OR_CLAIR[3])
		else
			b:SetBackdropBorderColor(0.3, 0.3, 0.33, 0.5)
			b.nom:SetTextColor(0.45, 0.46, 0.5)
			b.rang:SetTextColor(0.45, 0.46, 0.5)
		end
	end
	Compagnons_Page(etat.page)
end

function Compagnons_OuvrirFiche(id)
	etat.fiche = id
	etat.f, etat.g = {}, {}
	G.galerie:Hide()
	F:Show()
	G:Show()
	Compagnons_MajFiche()
	Commande(".cpg fiche " .. id)
end

-- ------------------------------------------------------------------ boutique
local B = Cadre("CompagnonsBoutique", 790, 540, "Boutique")
B.sous:SetText("Même boutique et même solde que le site et le launcher")
B.cats = {}
B.lignes = {}
B.vide = Texte(B, 12, GRIS)
B.vide:SetPoint("CENTER", B, "CENTER", 0, 0)
B.aide = Texte(B, 9, GRIS)
B.aide:SetPoint("BOTTOM", B, "BOTTOM", 0, 12)
B.aide:SetText("Les achats arrivent par courrier sur ce personnage. Recharger des Gen : sur le site ou dans le launcher.")
for i = 1, 18 do
	local l = CreateFrame("Button", nil, B)
	l:SetWidth(246)
	l:SetHeight(64)
	local col, lig = math.mod(i - 1, 3), math.floor((i - 1) / 3)
	l:SetPoint("TOPLEFT", B, "TOPLEFT", 16 + col * 254, -86 - lig * 70)
	Fond(l, 0.06, 0.07, 0.11, 0.85, { OR[1], OR[2], OR[3], 0.3 })
	l.ic = l:CreateTexture(nil, "ARTWORK")
	l.ic:SetWidth(40)
	l.ic:SetHeight(40)
	l.ic:SetPoint("LEFT", l, "LEFT", 10, 0)
	l.nom = Texte(l, 11, TEXTE)
	l.nom:SetWidth(180)
	l.nom:SetJustifyH("LEFT")
	l.nom:SetPoint("TOPLEFT", l.ic, "TOPRIGHT", 10, 0)
	l.prix = Texte(l, 13, OR_CLAIR, POLICE_TITRE)
	l.prix:SetPoint("BOTTOMLEFT", l.ic, "BOTTOMRIGHT", 10, 0)
	l.etat = Texte(l, 9, VERT)
	l.etat:SetPoint("BOTTOMRIGHT", l, "BOTTOMRIGHT", -10, 10)
	Lumiere(l, OR[1], OR[2], OR[3], 0.2)
	l:SetScript("OnClick", function()
		local a = this.a
		if not a then return end
		if a.type == 2 and etat.possedes[a.item] then return end
		Compagnons_ProposerAchat(a.id, a.nom, a.prix)
	end)
	l:SetScript("OnEnter", function()
		local a = this.a
		if not a then return end
		GameTooltip:SetOwner(this, "ANCHOR_RIGHT")
		if a.type == 0 and a.item > 0 then
			GameTooltip:SetHyperlink("item:" .. a.item .. ":0:0:0")
		else
			local c = QUALCAT[a.qualite] or TEXTE
			GameTooltip:SetText(a.nom, c[1], c[2], c[3])
		end
		if a.desc ~= "" then GameTooltip:AddLine(a.desc, 1, 1, 1, 1) end
		GameTooltip:AddLine("Clic : acheter pour " .. Milliers(a.prix) .. " Gen", OR[1], OR[2], OR[3])
		GameTooltip:Show()
	end)
	l:SetScript("OnLeave", function() GameTooltip:Hide() end)
	B.lignes[i] = l
end

function Compagnons_MajBoutique()
	B.solde:SetText(Milliers(etat.solde) .. " |cffd9b36cGen|r")
	-- onglets des catégories
	local x = 16
	for i = 1, table.getn(etat.categories) do
		local nom = etat.categories[i]
		local b = B.cats[i]
		if not b then
			b = Bouton(B, 100, 24, "")
			b:SetScript("OnClick", function()
				etat.categorie = this.nom
				etat.pageBoutique = 1
				Compagnons_MajBoutique()
			end)
			B.cats[i] = b
		end
		b.nom = nom
		b.t:SetText(nom)
		b:SetWidth(b.t:GetStringWidth() + 30)
		b:ClearAllPoints()
		b:SetPoint("TOPLEFT", B, "TOPLEFT", x, -52)
		x = x + b:GetWidth() + 6
		Pastille(b, etat.categorie == nom, OR)
		b:Show()
	end
	for i = table.getn(etat.categories) + 1, table.getn(B.cats) do B.cats[i]:Hide() end
	local liste = {}
	for i = 1, table.getn(etat.catalogue) do
		local a = etat.catalogue[i]
		if a.categorie == etat.categorie then table.insert(liste, a) end
	end
	B.vide:SetText(table.getn(etat.catalogue) == 0 and "Chargement de la boutique..." or (table.getn(liste) == 0 and "Rien dans cette catégorie pour l'instant." or ""))
	for i = 1, table.getn(B.lignes) do
		local l, a = B.lignes[i], liste[i]
		l.a = a
		if a then
			local c = QUALCAT[a.qualite] or TEXTE
			l.nom:SetText(a.nom)
			l.nom:SetTextColor(c[1], c[2], c[3])
			l:SetBackdropBorderColor(c[1], c[2], c[3], 0.5)
			l.prix:SetText(Milliers(a.prix) .. " Gen")
			l.ic:SetTexCoord(0, 1, 0, 1)
			if a.type == 2 and D[a.item] then
				IconeClasse(l.ic, D[a.item].classe)
			elseif a.type == 1 then
				l.ic:SetTexture("Interface\\Icons\\INV_Scroll_03")
			else
				Demander(a.item)
				l.ic:SetTexture(Texture(a.item) or "Interface\\Icons\\INV_Misc_Bag_10")
			end
			l.etat:SetText(a.type == 2 and etat.possedes[a.item] and "Possédé" or "")
			l:Show()
		else
			l:Hide()
		end
	end
end

-- confirmation d'achat (galerie et boutique)
local achat = nil
StaticPopupDialogs["COMPAGNONS_ACHAT"] = {
	text = "Acheter %s pour %s Gen ?\nIl arrive par courrier sur ce personnage.",
	button1 = "Acheter", button2 = "Annuler",
	OnAccept = function()
		if achat then Commande(".cpg acheter " .. achat) end
		achat = nil
	end,
	OnCancel = function() achat = nil end,
	timeout = 0, whileDead = 1, hideOnEscape = 1,
}
function Compagnons_ProposerAchat(id, nom, prix)
	achat = id
	StaticPopup_Show("COMPAGNONS_ACHAT", nom, Milliers(prix))
end

-- ------------------------------------------------------------------ ouverture
function Compagnons_Basculer()
	if G:IsVisible() then
		G:Hide()
		return
	end
	if not etat.fiche then
		F:Hide()
		G.galerie:Show()
		Compagnons_MajGalerie()
	else
		Compagnons_MajFiche()
		Commande(".cpg fiche " .. etat.fiche)
	end
	G:Show()
	Commande(".cpg liste")
end

function Compagnons_BasculerBoutique()
	if B:IsVisible() then
		B:Hide()
		return
	end
	B:Show()
	Compagnons_MajBoutique()
	Commande(".cpg boutique")
end
SLASH_COMPAGNONS1 = "/compagnons"
SLASH_COMPAGNONS2 = "/cpg"
SlashCmdList["COMPAGNONS"] = function() Compagnons_Basculer() end
SLASH_COMPBOUTIQUE1 = "/boutique"
SlashCmdList["COMPBOUTIQUE"] = function() Compagnons_BasculerBoutique() end

-- ------------------------------------------------------------------ boutons de la barre du bas (après Talents)
local function MicroBouton(nom, icone, info, clic)
	local b = CreateFrame("Button", nom, MainMenuBarArtFrame, "MainMenuBarMicroButton")
	b:RegisterForClicks("LeftButtonUp", "RightButtonUp")
	b:SetNormalTexture("Interface\\Buttons\\UI-MicroButtonCharacter-Up")
	b:SetPushedTexture("Interface\\Buttons\\UI-MicroButtonCharacter-Down")
	b:SetHighlightTexture("Interface\\Buttons\\UI-MicroButton-Hilight")
	local t = b:CreateTexture(nil, "OVERLAY")
	t:SetWidth(18)
	t:SetHeight(25)
	t:SetPoint("TOP", b, "TOP", 0, -28)
	t:SetTexture(icone)
	t:SetTexCoord(0.2, 0.8, 0.0666, 0.9)
	b.icone = t
	b.tooltipText = info
	b:SetScript("OnClick", clic)
	b:SetScript("OnMouseDown", function() this.icone:SetPoint("TOP", this, "TOP", -1, -29) end)
	b:SetScript("OnMouseUp", function() this.icone:SetPoint("TOP", this, "TOP", 0, -28) end)
	return b
end
local mbCompagnons = MicroBouton("CompagnonsMicroButton", "Interface\\Icons\\Ability_Hunter_BeastCall", "Compagnons", function() Compagnons_Basculer() end)
local mbBoutique = MicroBouton("CompagnonsBoutiqueMicroButton", "Interface\\Icons\\INV_Misc_Coin_02", "Boutique", function() Compagnons_BasculerBoutique() end)

-- 10 boutons au lieu de 8 : un peu plus serrés pour ne pas toucher les sacs
local function Placer()
	local ordre = { CharacterMicroButton, SpellbookMicroButton, TalentMicroButton, mbCompagnons, mbBoutique, QuestLogMicroButton,
		SocialsMicroButton, WorldMapMicroButton, MainMenuMicroButton, HelpMicroButton }
	local prec = nil
	for i = 1, table.getn(ordre) do
		local b = ordre[i]
		if b then
			if prec then
				b:ClearAllPoints()
				if prec == TalentMicroButton and not TalentMicroButton:IsShown() then
					b:SetPoint("BOTTOMLEFT", prec, "BOTTOMLEFT", 0, 0)
				else
					b:SetPoint("BOTTOMLEFT", prec, "BOTTOMRIGHT", -3, 0)
				end
			end
			prec = b
		end
	end
end
local origUpdateTalent = UpdateTalentButton
UpdateTalentButton = function()
	if origUpdateTalent then origUpdateTalent() end
	Placer()
end
Placer()

-- ------------------------------------------------------------------ objets des sacs
local origPickup = PickupContainerItem
PickupContainerItem = function(sac, case)
	if not CursorHasItem() then
		dernierSac, derniereCase = sac, case
	end
	origPickup(sac, case)
end

-- clic droit sur un objet dans les sacs quand la fiche (équipement) est ouverte : il va sur le compagnon
local function EmplacementPour(id)
	if id >= 1001000 and id <= 1001254 then
		return (etat.g.orbes and etat.g.orbes[1] ~= 0 and etat.g.orbes[2] == 0) and 7 or 6
	end
	local _, _, _, _, _, _, _, equip = GetItemInfo(id)
	local libre = function(a, b)
		if etat.g.equip and (etat.g.equip[a] or 0) ~= 0 and (etat.g.equip[b] or 0) == 0 then return b end
		return a
	end
	if equip == "INVTYPE_NECK" then return 1 end
	if equip == "INVTYPE_FINGER" then return libre(2, 3) end
	if equip == "INVTYPE_TRINKET" then return libre(4, 5) end
	if not equip or equip == "" then
		return (etat.g.artefacts and etat.g.artefacts[1] ~= 0 and etat.g.artefacts[2] == 0) and 9 or 8
	end
	return nil
end
local function AccrocherSacs()
	local origUse = UseContainerItem
	UseContainerItem = function(sac, case, a3)
		if G:IsVisible() and F:IsVisible() and etat.page == 1 and etat.fiche and not (MerchantFrame and MerchantFrame:IsVisible())
			and not (BankFrame and BankFrame:IsVisible()) and not (TradeFrame and TradeFrame:IsVisible())
			and not (SendMailFrame and SendMailFrame:IsVisible()) then
			local lien = GetContainerItemLink(sac, case)
			local _, _, id = string.find(lien or "", "item:(%d+)")
			id = tonumber(id)
			local e = id and EmplacementPour(id)
			if e then
				Commande(".cpg equiper " .. etat.fiche .. " " .. sac .. " " .. case .. " " .. e)
				return
			end
		end
		origUse(sac, case, a3)
	end
end

-- ------------------------------------------------------------------ réponses du serveur
local origChat = ChatFrame_OnEvent
ChatFrame_OnEvent = function(ev)
	if ev == "CHAT_MSG_SYSTEM" and arg1 and string.find(arg1, "^##CPG") then return end
	origChat(ev)
end

local function Liste(s)
	local t = {}
	for v in string.gfind(s or "", "(%d+)") do table.insert(t, tonumber(v)) end
	return t
end

local function Recevoir(msg)
	local typ, reste = string.sub(msg, 7, 7), string.sub(msg, 9)
	if typ == "L" then
		local _, _, solde, liste = string.find(reste, "^(%-?%d+) ?(.*)$")
		etat.solde = tonumber(solde) or 0
		etat.possedes, etat.actifs, etat.nbPossedes = {}, {}, 0
		for id, actif in string.gfind(liste or "", "(%d+):(%d)") do
			id = tonumber(id)
			etat.possedes[id] = true
			etat.nbPossedes = etat.nbPossedes + 1
			if actif == "1" then etat.actifs[id] = true end
		end
		if G:IsVisible() then
			if etat.fiche then Compagnons_MajFiche() else Compagnons_MajGalerie() end
		end
		if B:IsVisible() then Compagnons_MajBoutique() end
	elseif typ == "F" then
		local p = Couper(reste, "|")
		local id = tonumber(p[1])
		if id ~= etat.fiche then return end
		local f = { niveau = tonumber(p[2]), points = tonumber(p[3]), rangs = {}, stats = {} }
		local r = p[4] or ""
		for i = 0, 10 do f.rangs[i] = tonumber(string.sub(r, i + 1, i + 1)) or 0 end
		f.auto = string.sub(r, 12, 12) == "A"
		for k, v in string.gfind(p[5] or "", "(%a+)=(%-?%d+)") do f.stats[k] = tonumber(v) end
		etat.f = f
		Compagnons_MajFiche()
	elseif typ == "G" then
		local p = Couper(reste, "|")
		local id = tonumber(p[1])
		if id ~= etat.fiche then return end
		etat.g = { equip = Liste(p[2]), orbes = Liste(p[3]), artefacts = Liste(p[4]), actif = p[5] == "1" }
		etat.actifs[id] = etat.g.actif or nil
		Compagnons_MajFiche()
	elseif typ == "S" then
		etat.solde = tonumber(reste) or etat.solde
		if B:IsVisible() then Compagnons_MajBoutique() end
		if G:IsVisible() then G.solde:SetText(Milliers(etat.solde) .. " |cffd9b36cGen|r") end
	elseif typ == "A" then
		if not etat.catalogueNouveau then etat.catalogueNouveau, etat.categoriesNouv = {}, {} end
		local p = Couper(reste, "|")
		local a = { id = p[1], categorie = p[2], nom = p[3], prix = tonumber(p[4]) or 0, qualite = p[5], type = tonumber(p[6]) or 0,
			item = tonumber(p[7]) or 0, desc = p[8] or "" }
		table.insert(etat.catalogueNouveau, a)
		local deja = false
		for i = 1, table.getn(etat.categoriesNouv) do
			if etat.categoriesNouv[i] == a.categorie then deja = true end
		end
		if not deja then table.insert(etat.categoriesNouv, a.categorie) end
	elseif typ == "B" then
		etat.catalogue = etat.catalogueNouveau or {}
		etat.categories = etat.categoriesNouv or {}
		etat.catalogueNouveau, etat.categoriesNouv = nil, nil
		local ok = false
		for i = 1, table.getn(etat.categories) do
			if etat.categories[i] == etat.categorie then ok = true end
		end
		if not ok then etat.categorie = etat.categories[1] end
		Compagnons_MajBoutique()
	end
end

local ev = CreateFrame("Frame")
ev:RegisterEvent("PLAYER_LOGIN")
ev:RegisterEvent("PLAYER_ENTERING_WORLD")
ev:RegisterEvent("CHAT_MSG_SYSTEM")
local tDemande, tMaj = 0, 0
ev:SetScript("OnEvent", function()
	if event == "PLAYER_LOGIN" then
		AccrocherSacs()          -- après les autres addons (Reliques) : la fiche passe en premier
		Placer()
	elseif event == "PLAYER_ENTERING_WORLD" then
		tDemande = GetTime() + 4
	elseif arg1 and string.find(arg1, "^##CPG ") then
		Recevoir(arg1)
	end
end)
ev:SetScript("OnUpdate", function()
	local now = GetTime()
	if tDemande > 0 and now >= tDemande then
		tDemande = 0
		Commande(".cpg liste")
	end
	-- noms et icônes des objets demandés au serveur
	if now - tMaj > 1 then
		tMaj = now
		if G:IsVisible() and etat.fiche and F.p1:IsVisible() then
			for i = 1, 9 do
				local b = F.cases[i]
				if b.id and b.id ~= 0 and not Texture(b.id) then
					Compagnons_MajFiche()
					break
				end
			end
		end
	end
end)
