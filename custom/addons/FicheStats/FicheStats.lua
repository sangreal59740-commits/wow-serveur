-- FicheStats
-- 1. Au-dessus de la fiche du personnage, en petit : dégâts d'arme, sorts, défense, régénération, niveau d'objet, et la cible
--    (réduction des dégâts dans les deux sens, chances de la rater). Chaque valeur s'explique au survol.
-- 2. Quand l'équipement, un buff ou une potion change les statistiques : gains (vert) et pertes (rouge) à côté du personnage,
--    effacés après 3 s (le survol les garde affichés).
-- 3. Infobulles d'objets : comparaison avec l'objet porté.
-- 4. Infobulles de sorts : dégâts et soins réels avec vos bonus (estimation).
-- Les valeurs que le client 1.12 ne connaît pas viennent du serveur : commande .fiche donnees, réponse « ##FICHE ... » lue puis masquée.

local SERVEUR = {}
local avant = nil
local demande, attente, tAttente, tDerniere = false, false, 0, 0
local afficher = false

local function Arrondi(v, d)
	local m = 10 ^ (d or 0)
	return math.floor(v * m + 0.5) / m
end
local function Nb(v, d)
	if not v then return "?" end
	return (string.gsub(tostring(Arrondi(v, d or 0)), "%.", ","))
end
local function Pct(v, d)
	if not v then return "?" end
	return Nb(v, d or 1) .. " %"
end
local function DPS(minD, maxD, vitesse)
	if not minD or not vitesse or vitesse <= 0 then return 0 end
	return (minD + maxD) / 2 / vitesse
end

-- ---------------------------------------------------------------- relevé des statistiques
local function Releve()
	local s = {}
	local noms = { "force", "agi", "endu", "intel", "esprit" }
	for i = 1, 5 do
		local _, v = UnitStat("player", i)
		s[noms[i]] = v or 0
	end
	local _, armure = UnitArmor("player")
	s.armure = armure or 0
	s.pv = UnitHealthMax("player")
	if UnitPowerType("player") == 0 then s.mana = UnitManaMax("player") end
	local b, p, n = UnitAttackPower("player")
	s.pa = (b or 0) + (p or 0) + (n or 0)
	b, p, n = UnitRangedAttackPower("player")
	s.pad = (b or 0) + (p or 0) + (n or 0)
	local minD, maxD, minG, maxG = UnitDamage("player")
	local vit, vitG = UnitAttackSpeed("player")
	s.minD, s.maxD, s.vit = minD, maxD, vit
	s.dps = DPS(minD, maxD, vit)
	if vitG and minG and maxG and maxG > 0 then
		s.minG, s.maxG = minG, maxG
		s.dpsg = DPS(minG, maxG, vitG)
	end
	if GetInventoryItemLink("player", 18) then
		local vitD, minR, maxR = UnitRangedDamage("player")
		if vitD and vitD > 0 and maxR and maxR > 0 then
			s.minR, s.maxR = minR, maxR
			s.dpsd = DPS(minR, maxR, vitD)
		end
	end
	local ecoles = { [2] = "rfeu", [3] = "rnat", [4] = "rgiv", [5] = "romb", [6] = "rarc" }
	for i, k in pairs(ecoles) do
		local _, r = UnitResistance("player", i)
		s[k] = r or 0
	end
	for k, v in pairs(SERVEUR) do s[k] = v end
	if NiveauObjet_Moyenne then s.ilvl = NiveauObjet_Moyenne("player") end
	return s
end

-- ---------------------------------------------------------------- panneau au-dessus de la fiche
local panneau = CreateFrame("Frame", "FicheStatsPanneau", PaperDollFrame)
panneau:SetWidth(334)
panneau:SetPoint("BOTTOMLEFT", CharacterFrame, "TOPLEFT", 14, -12)
panneau:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background", edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
	tile = true, tileSize = 16, edgeSize = 12, insets = { left = 3, right = 3, top = 3, bottom = 3 } })
panneau:SetBackdropColor(0, 0, 0, 0.75)
panneau:SetBackdropBorderColor(0.5, 0.5, 0.5, 1)

-- cellules : clé, libellé, ligne, colonne, explication
local CELLULES = {
	{ "arme", "Arme", 1, 1, "Dégâts de l'arme en main droite (minimum-maximum), bonus de puissance d'attaque compris." },
	{ "dps", "DPS", 1, 2, "Dégâts par seconde de l'arme en main droite." },
	{ "pa", "PA", 1, 3, "Puissance d'attaque en mêlée. 14 PA = +1 DPS." },
	{ "cc", "Crit.", 1, 4, "Chances de coup critique en mêlée." },
	{ "tm", "Toucher", 2, 1, "Bonus de toucher en mêlée et à distance (équipement et talents)." },
	{ "dpsg", "Main g.", 2, 2, "Dégâts par seconde de l'arme en main gauche." },
	{ "dpsd", "Dist.", 2, 3, "Dégâts par seconde de l'arme à distance." },
	{ "cd", "Crit. dist.", 2, 4, "Chances de coup critique à distance." },
	{ "sd", "Sorts", 3, 1, "Bonus aux dégâts des sorts (meilleure école de magie)." },
	{ "so", "Soins", 3, 2, "Bonus aux soins." },
	{ "cs", "Crit.", 3, 3, "Chances de critique des sorts (meilleure école)." },
	{ "ts", "Toucher", 3, 4, "Bonus de toucher des sorts." },
	{ "es", "Esquive", 4, 1, "Chances d'esquiver une attaque." },
	{ "par", "Parade", 4, 2, "Chances de parer une attaque (de face)." },
	{ "bl", "Blocage", 4, 3, "Chances de bloquer une attaque avec un bouclier (de face)." },
	{ "ra", "Armure", 4, 4, "Réduction des dégâts physiques par votre armure, contre un ennemi de votre niveau." },
	{ "rmc", "Mana", 5, 1, "Mana récupéré toutes les 5 s quand vous n'avez pas lancé de sort depuis 5 s." },
	{ "rmi", "En sort", 5, 2, "Mana récupéré toutes les 5 s dans les 5 s qui suivent un sort (règle des 5 secondes)." },
	{ "rv", "Vie", 5, 3, "Points de vie récupérés par seconde hors combat (x1,5 assis)." },
	{ "ilvl", "iLvl", 5, 4, "Niveau d'objet moyen de votre équipement." },
	{ "cn", "Cible", 6, 1, "Niveau de votre cible." },
	{ "ctr", "Vos coups", 6, 2, "Réduction de vos dégâts physiques par l'armure de la cible." },
	{ "car", "Ses coups", 6, 3, "Réduction des dégâts physiques de la cible par votre armure (dépend de son niveau)." },
	{ "crm", "Raté", 6, 4, "Chances de rater la cible : en mêlée / avec les sorts (selon l'écart de niveau et votre toucher)." },
}
local cell = {}
local LARG = 81
for _, c in ipairs(CELLULES) do
	local b = CreateFrame("Button", nil, panneau)
	b:SetWidth(LARG)
	b:SetHeight(12)
	b:SetPoint("TOPLEFT", panneau, "TOPLEFT", 6 + (c[4] - 1) * LARG, -6 - (c[3] - 1) * 12)
	local fs = b:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
	fs:SetAllPoints(b)
	fs:SetJustifyH("LEFT")
	local f = fs:GetFont()
	fs:SetFont(f, 9)
	b.fs, b.titre, b.aide = fs, c[2], c[5]
	b:SetScript("OnEnter", function()
		GameTooltip:SetOwner(this, "ANCHOR_TOPLEFT")
		GameTooltip:SetText(this.titre, 1, 0.82, 0)
		GameTooltip:AddLine(this.aide, 1, 1, 1, 1)
		GameTooltip:Show()
	end)
	b:SetScript("OnLeave", function() GameTooltip:Hide() end)
	cell[c[1]] = b
end

local J, F = "|cffffd100", "|r"
local function Cel(k, v)
	local b = cell[k]
	if v then b.fs:SetText(J .. b.titre .. F .. " " .. v) b:Show() else b:Hide() end
end

local function MajPanneau(s)
	Cel("arme", Nb(s.minD) .. "-" .. Nb(s.maxD))
	Cel("dps", Nb(s.dps, 1))
	Cel("pa", Nb(s.pa))
	Cel("cc", Pct(s.cc))
	Cel("tm", "+" .. Pct(s.tm))
	Cel("dpsg", s.dpsg and Nb(s.dpsg, 1) or nil)
	Cel("dpsd", s.dpsd and Nb(s.dpsd, 1) or nil)
	Cel("cd", s.dpsd and Pct(s.cd) or nil)
	Cel("sd", "+" .. Nb(s.sd))
	Cel("so", "+" .. Nb(s.so))
	Cel("cs", Pct(s.cs))
	Cel("ts", "+" .. Pct(s.ts))
	Cel("es", Pct(s.es))
	Cel("par", Pct(s.par))
	Cel("bl", Pct(s.bl))
	Cel("ra", "-" .. Pct(s.ra))
	Cel("rmc", s.mana and (Nb(s.rmc) .. "/5s") or nil)
	Cel("rmi", s.mana and (Nb(s.rmi) .. "/5s") or nil)
	Cel("rv", Nb(s.rv, 1) .. "/s")
	Cel("ilvl", Nb(s.ilvl, 1))
	local cible = s.cn and s.cn > 0
	Cel("cn", cible and ("niv. " .. s.cn) or nil)
	Cel("ctr", cible and ("-" .. Pct(s.ctr)) or nil)
	Cel("car", cible and ("-" .. Pct(s.car)) or nil)
	Cel("crm", cible and (Nb(s.crm, 1) .. " / " .. Pct(s.crs)) or nil)
	panneau:SetHeight(cible and 84 or 72)
end

-- ---------------------------------------------------------------- gains et pertes à côté du personnage
local STATS = {
	{ "force", "Force", 0, 0.5 }, { "agi", "Agilité", 0, 0.5 }, { "endu", "Endurance", 0, 0.5 }, { "intel", "Intelligence", 0, 0.5 },
	{ "esprit", "Esprit", 0, 0.5 }, { "armure", "Armure", 0, 0.5 }, { "pv", "Points de vie", 0, 0.5 }, { "mana", "Mana", 0, 0.5 },
	{ "pa", "Puissance d'attaque", 0, 0.5 }, { "pad", "Puissance d'attaque à distance", 0, 0.5 },
	{ "dps", "DPS de l'arme", 1, 0.05 }, { "dpsg", "DPS main gauche", 1, 0.05 }, { "dpsd", "DPS à distance", 1, 0.05 },
	{ "sd", "Dégâts des sorts", 0, 0.5 }, { "so", "Soins", 0, 0.5 },
	{ "cc", "Critique", 2, 0.01, true }, { "cd", "Critique à distance", 2, 0.01, true }, { "cs", "Critique des sorts", 2, 0.01, true },
	{ "tm", "Toucher", 2, 0.01, true }, { "ts", "Toucher des sorts", 2, 0.01, true },
	{ "es", "Esquive", 2, 0.01, true }, { "par", "Parade", 2, 0.01, true }, { "bl", "Blocage", 2, 0.01, true },
	{ "rmc", "Mana toutes les 5 s", 0, 0.5 }, { "rv", "Vie par seconde", 1, 0.05 },
	{ "rfeu", "Résistance au Feu", 0, 0.5 }, { "rnat", "Résistance à la Nature", 0, 0.5 }, { "rgiv", "Résistance au Givre", 0, 0.5 },
	{ "romb", "Résistance à l'Ombre", 0, 0.5 }, { "rarc", "Résistance aux Arcanes", 0, 0.5 },
	{ "ilvl", "Niveau d'objet moyen", 1, 0.05 },
}
local MAXL = 16
local diff = CreateFrame("Frame", "FicheStatsDiff", UIParent)
diff:SetWidth(240)
diff:SetHeight(20)
diff:SetPoint("TOPRIGHT", UIParent, "CENTER", -90, 140)
diff:SetFrameStrata("HIGH")
diff:EnableMouse(true)
diff:Hide()
local textes = {}
for i = 1, MAXL do
	local fs = diff:CreateFontString(nil, "OVERLAY", "GameFontNormal")
	fs:SetPoint("TOPRIGHT", diff, "TOPRIGHT", 0, -(i - 1) * 15)
	fs:SetJustifyH("RIGHT")
	textes[i] = fs
end
local tAffiche, survol = 0, false
diff:SetScript("OnEnter", function() survol = true diff:SetAlpha(1) end)
diff:SetScript("OnLeave", function() survol = false tAffiche = 3 end)

local function MontrerDifferences(a, b)
	local n = 0
	for _, d in ipairs(STATS) do
		local k, nom, dec, seuil, pct = d[1], d[2], d[3], d[4], d[5]
		local v1, v2 = a[k], b[k]
		if v1 and v2 and math.abs(v2 - v1) >= seuil and n < MAXL then
			n = n + 1
			local delta = v2 - v1
			textes[n]:SetText((delta > 0 and "+" or "") .. Nb(delta, dec) .. (pct and " %" or "") .. " " .. nom)
			if delta > 0 then textes[n]:SetTextColor(0.2, 1, 0.2) else textes[n]:SetTextColor(1, 0.3, 0.3) end
		end
	end
	if n == 0 then return end
	for i = n + 1, MAXL do textes[i]:SetText("") end
	diff:SetHeight(n * 15)
	tAffiche = 3
	diff:SetAlpha(1)
	diff:Show()
end

-- ---------------------------------------------------------------- comparaison d'objets
local OBJ = {}
if FicheStats_Objets then
	for _, bloc in ipairs(FicheStats_Objets) do
		for id, data in string.gfind(bloc, "(%d+)=([^|]+)") do OBJ[tonumber(id)] = data end
	end
	FicheStats_Objets = nil
end
local cacheObj = {}
local function Stats(id)
	if not id then return nil end
	if cacheObj[id] then return cacheObj[id] end
	local data = OBJ[id]
	if not data then return nil end
	local _, _, inv, reste = string.find(data, "^(%d+);(.*)$")
	local t = { inv = tonumber(inv), v = {} }
	for k, v in string.gfind(reste or "", "(%a+):([%-%d%.]+)") do t.v[k] = tonumber(v) end
	cacheObj[id] = t
	return t
end
local function IdDuLien(lien)
	if not lien then return nil end
	local _, _, id = string.find(lien, "item:(%d+)")
	return id and tonumber(id)
end
-- emplacements remplacés selon le type d'objet
local EMPL = { [1] = { 1 }, [2] = { 2 }, [3] = { 3 }, [5] = { 5 }, [20] = { 5 }, [6] = { 6 }, [7] = { 7 }, [8] = { 8 }, [9] = { 9 },
	[10] = { 10 }, [11] = { 11, 12 }, [12] = { 13, 14 }, [13] = { 16, 17 }, [14] = { 17 }, [15] = { 18 }, [16] = { 15 }, [17] = { 16 },
	[21] = { 16 }, [22] = { 17 }, [23] = { 17 }, [25] = { 18 }, [26] = { 18 } }
local NOMS = { s = "Force", a = "Agilité", e = "Endurance", i = "Intelligence", p = "Esprit", v = "Vie", m = "Mana", ar = "Armure",
	dps = "DPS", sd = "Sorts", so = "Soins", cc = "Crit.", cs = "Crit. sorts", tm = "Toucher", ts = "Toucher sorts", mp = "Mana/5s",
	pa = "PA", pad = "PA dist.", es = "Esquive", par = "Parade", bl = "Blocage", vb = "Valeur de blocage", rv = "Vie/5s", def = "Défense",
	rsa = "Rés. Sacré", rfeu = "Rés. Feu", rnat = "Rés. Nature", rgiv = "Rés. Givre", romb = "Rés. Ombre", rarc = "Rés. Arcanes" }
local ORDRE = { "s", "a", "e", "i", "p", "dps", "pa", "pad", "sd", "so", "cc", "cs", "tm", "ts", "mp", "ar", "def", "es", "par", "bl", "vb",
	"v", "m", "rv", "rsa", "rfeu", "rnat", "rgiv", "romb", "rarc" }
local PCT = { cc = true, cs = true, tm = true, ts = true, es = true, par = true, bl = true }

local function Ecart(nouv, anciens)
	local morceaux = {}
	for _, k in ipairs(ORDRE) do
		local a = 0
		for _, o in ipairs(anciens) do a = a + (o.v[k] or 0) end
		local d = (nouv.v[k] or 0) - a
		if math.abs(d) >= 0.05 then
			local c = d > 0 and "|cff33ff33+" or "|cffff4444"
			table.insert(morceaux, c .. Nb(d, 1) .. (PCT[k] and " %" or "") .. " " .. NOMS[k] .. "|r")
		end
	end
	return morceaux
end

local function Comparer(tip, lien)
	local id = IdDuLien(lien)
	local nouv = Stats(id)
	if not nouv or not EMPL[nouv.inv] then return end
	local lignes = {}
	for _, slot in ipairs(EMPL[nouv.inv]) do
		local porteId = IdDuLien(GetInventoryItemLink("player", slot))
		if porteId == id then return end            -- c'est l'objet porté
		local anciens = {}
		local o = Stats(porteId)
		if o then table.insert(anciens, o) end
		if nouv.inv == 17 then                       -- deux mains : remplace aussi la main gauche
			local g = Stats(IdDuLien(GetInventoryItemLink("player", 17)))
			if g then table.insert(anciens, g) end
		end
		local m = Ecart(nouv, anciens)
		if table.getn(m) > 0 then
			local titre = table.getn(EMPL[nouv.inv]) > 1 and ("Par rapport à l'emplacement " .. ((slot == 11 or slot == 13 or slot == 16) and 1 or 2) .. " :")
				or "Par rapport à l'objet porté :"
			table.insert(lignes, { titre, m })
		end
		if nouv.inv == 13 and not porteId then break end
	end
	if table.getn(lignes) == 0 then return end
	for _, l in ipairs(lignes) do
		tip:AddLine(l[1], 0.6, 0.6, 0.6)
		local ligne = ""
		for i, t in ipairs(l[2]) do
			ligne = ligne .. (ligne == "" and "" or ", ") .. t
			if math.mod(i, 3) == 0 then tip:AddLine(ligne) ligne = "" end
		end
		if ligne ~= "" then tip:AddLine(ligne) end
	end
	tip:Show()
end

local function Accrocher(tip, methode, quelLien)
	local orig = tip[methode]
	if not orig then return end
	tip[methode] = function(self, a1, a2, a3, a4)
		local r1, r2, r3 = orig(self, a1, a2, a3, a4)
		local ok, lien = pcall(quelLien, a1, a2, a3, a4)
		if ok and lien then pcall(Comparer, self, lien) end
		return r1, r2, r3
	end
end
local function AccrocherObjets(tip)
	Accrocher(tip, "SetBagItem", function(b, s) return GetContainerItemLink(b, s) end)
	Accrocher(tip, "SetHyperlink", function(l) return l end)
	Accrocher(tip, "SetLootItem", function(s) return GetLootSlotLink(s) end)
	Accrocher(tip, "SetLootRollItem", function(i) return GetLootRollItemLink(i) end)
	Accrocher(tip, "SetMerchantItem", function(i) return GetMerchantItemLink(i) end)
	Accrocher(tip, "SetQuestItem", function(t, i) return GetQuestItemLink(t, i) end)
	Accrocher(tip, "SetQuestLogItem", function(t, i) return GetQuestLogItemLink(t, i) end)
	Accrocher(tip, "SetAuctionItem", function(t, i) return GetAuctionItemLink(t, i) end)
	Accrocher(tip, "SetTradeTargetItem", function(i) return GetTradeTargetItemLink(i) end)
end
AccrocherObjets(GameTooltip)
if ItemRefTooltip then AccrocherObjets(ItemRefTooltip) end

-- ---------------------------------------------------------------- vrais dégâts des sorts dans les infobulles
local function Borne(v, a, b)
	if v < a then return a elseif v > b then return b end
	return v
end
local function DegatsReels(tip)
	local n = tip:NumLines()
	if not n or n < 2 then return end
	local nomTip = tip:GetName()
	local incant, canal, desc = nil, false, nil
	for i = 1, n do
		local fs = getglobal(nomTip .. "TextLeft" .. i)
		local t = fs and fs:GetText()
		if t then
			local _, _, sec = string.find(t, "([%d%.]+) sec d'incantation")
			if sec then incant = tonumber(sec) end
			if string.find(t, "Incantation instantanée") or t == "Instantané" then incant = 0 end
			if string.find(t, "Canalis") then canal = true end
			local r = getglobal(nomTip .. "TextRight" .. i)
			local tr = r and r:IsShown() and r:GetText()
			if tr then
				local _, _, sec2 = string.find(tr, "([%d%.]+) sec d'incantation")
				if sec2 then incant = tonumber(sec2) end
				if string.find(tr, "Incantation instantanée") or tr == "Instantané" then incant = 0 end
				if string.find(tr, "Canalis") then canal = true end
			end
			if i == n then desc = t end
		end
	end
	if not desc then return end
	local soin = string.find(desc, "points de vie") and (string.find(desc, "[Rr]end") or string.find(desc, "[Ss]oign")) and not string.find(desc, "dégâts")
	local bonus = soin and SERVEUR.so or SERVEUR.sd
	if not bonus or bonus <= 0 then return end
	local _, _, minV, maxV = string.find(desc, "(%d+) à (%d+)")
	local _, _, dot, duree = string.find(desc, "(%d+) points de [^%.]-en (%d+) sec")
	if not dot then _, _, dot, duree = string.find(desc, "(%d+) points de [^%.]-sur (%d+) sec") end
	local crit = soin and 1.5 or 1.5
	local ligne
	if minV then
		minV, maxV = tonumber(minV), tonumber(maxV)
		local c
		if canal then
			c = Borne((tonumber(duree) or 3.5) / 3.5, 0, 1)
		else
			c = Borne((incant and incant > 0 and incant or 1.5) / 3.5, 1.5 / 3.5, 1)
		end
		local a, b = minV + bonus * c, maxV + bonus * c
		ligne = "Avec vos bonus : " .. Nb(a) .. " à " .. Nb(b) .. " (critique " .. Nb(a * crit) .. " à " .. Nb(b * crit) .. ")"
	elseif dot then
		local d = tonumber(duree)
		local v = tonumber(dot) + bonus * Borne(d / 15, 0, 1)
		ligne = "Avec vos bonus : " .. Nb(v) .. " en " .. d .. " sec"
	end
	if ligne then
		tip:AddLine(ligne, 0.4, 0.8, 1)
		tip:Show()
	end
end
local origSetSpell = GameTooltip.SetSpell
GameTooltip.SetSpell = function(self, a1, a2)
	local r1, r2 = origSetSpell(self, a1, a2)
	pcall(DegatsReels, self)
	return r1, r2
end
local origSetAction = GameTooltip.SetAction
GameTooltip.SetAction = function(self, a1)
	local r1, r2 = origSetAction(self, a1)
	if not GetActionText(a1) then pcall(DegatsReels, self) end
	return r1, r2
end

-- ---------------------------------------------------------------- calcul et échanges avec le serveur
-- réduction des dégâts dans une bulle au-dessus des portraits : la mienne (mon armure contre la cible, ou contre mon niveau)
-- et celle de la cible (son armure contre mes coups)
local function Bulle(cadre, portrait, aide)
	local f = CreateFrame("Frame", nil, cadre)
	f:SetWidth(62)
	f:SetHeight(20)
	f:SetPoint("BOTTOM", portrait, "TOP", 0, 1)
	f:SetFrameLevel(cadre:GetFrameLevel() + 6)
	f:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background", edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
		tile = true, tileSize = 8, edgeSize = 10, insets = { left = 2, right = 2, top = 2, bottom = 2 } })
	f:SetBackdropColor(0.05, 0.08, 0.15, 0.9)
	f:SetBackdropBorderColor(0.45, 0.6, 0.9, 1)
	local ic = f:CreateTexture(nil, "ARTWORK")
	ic:SetTexture("Interface\\Icons\\INV_Shield_06")
	ic:SetTexCoord(0.08, 0.92, 0.08, 0.92)
	ic:SetWidth(12)
	ic:SetHeight(12)
	ic:SetPoint("LEFT", f, "LEFT", 5, 0)
	local t = f:CreateFontString(nil, "OVERLAY")
	t:SetFont("Fonts\\FRIZQT__.TTF", 9, "OUTLINE")
	t:SetPoint("LEFT", ic, "RIGHT", 3, 0)
	t:SetTextColor(0.8, 0.9, 1)
	f.texte = t
	f.aide = aide
	f:EnableMouse(true)
	f:SetScript("OnEnter", function()
		GameTooltip:SetOwner(this, "ANCHOR_TOP")
		GameTooltip:SetText("Réduction des dégâts physiques", 1, 0.82, 0)
		GameTooltip:AddLine(this.aide, 1, 1, 1, 1)
		GameTooltip:Show()
	end)
	f:SetScript("OnLeave", function() GameTooltip:Hide() end)
	f:Hide()
	return f
end
local bulleJoueur = Bulle(PlayerFrame, PlayerPortrait, "Votre armure réduit les coups de votre cible de ce pourcentage (sans cible : contre un ennemi de votre niveau).")
local bulleCible = Bulle(TargetFrame, TargetPortrait, "L'armure de la cible réduit vos coups physiques de ce pourcentage.")
local function MajCadres(s)
	local cible = s.cn and s.cn > 0 and UnitExists("target")
	local r = cible and s.car or s.ra
	if r then bulleJoueur.texte:SetText("-" .. Pct(r)) bulleJoueur:Show() else bulleJoueur:Hide() end
	if cible and s.ctr then bulleCible.texte:SetText("-" .. Pct(s.ctr)) bulleCible:Show() else bulleCible:Hide() end
end

local function Calculer()
	local s = Releve()
	MajPanneau(s)
	MajCadres(s)
	if avant and afficher then MontrerDifferences(avant, s) end
	avant = s
	afficher = true
end

local function Lire(msg)
	for k, v in string.gfind(msg, "(%a+)=([%-%d%.]+)") do
		if k == "pa" then k = "par" end         -- parade
		SERVEUR[k] = tonumber(v)
	end
end

local origChat = ChatFrame_OnEvent
ChatFrame_OnEvent = function(ev)
	if ev == "CHAT_MSG_SYSTEM" and arg1 and string.find(arg1, "^##FICHE") then return end
	origChat(ev)
end

local f = CreateFrame("Frame")
for _, e in ipairs({ "PLAYER_ENTERING_WORLD", "UNIT_INVENTORY_CHANGED", "UNIT_AURA", "UNIT_STATS", "UNIT_RESISTANCES", "UNIT_ATTACK_POWER",
	"UNIT_RANGED_ATTACK_POWER", "UNIT_DAMAGE", "UNIT_MAXHEALTH", "UNIT_MAXMANA", "PLAYER_LEVEL_UP", "PLAYER_TARGET_CHANGED", "CHAT_MSG_SYSTEM" }) do
	f:RegisterEvent(e)
end
f:SetScript("OnEvent", function()
	if event == "CHAT_MSG_SYSTEM" then
		if arg1 and string.find(arg1, "^##FICHE") then
			Lire(arg1)
			attente = false
			Calculer()
		end
		return
	end
	if event == "PLAYER_ENTERING_WORLD" then
		afficher = false
		avant = nil
		tDerniere = GetTime() + 2
	elseif event ~= "PLAYER_TARGET_CHANGED" and event ~= "PLAYER_LEVEL_UP" and arg1 and arg1 ~= "player" then
		return
	end
	demande = true
end)

f:SetScript("OnUpdate", function()
	local now = GetTime()
	if demande and not attente and now - tDerniere >= 1 then
		demande = false
		attente = true
		tAttente = now
		tDerniere = now
		SendChatMessage(".fiche donnees", "SAY")
	elseif attente and now - tAttente > 2 then
		attente = false
		Calculer()
	end
	if tAffiche > 0 and not survol then
		tAffiche = tAffiche - arg1
		if tAffiche < 1 then diff:SetAlpha(math.max(tAffiche, 0)) end
		if tAffiche <= 0 then diff:Hide() end
	end
end)

PaperDollFrame:SetScript("OnShow", (function(orig)
	return function()
		if orig then orig() end
		if avant then MajPanneau(avant) end
		demande = true
	end
end)(PaperDollFrame:GetScript("OnShow")))
