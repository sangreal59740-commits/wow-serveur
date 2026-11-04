-- FicheStats
-- 1. Au-dessus de la fiche du personnage : dégâts d'arme, puissance d'attaque, dégâts et soins des sorts, critiques, toucher,
--    défense, mana / 5 s et niveau d'objet moyen.
-- 2. Quand l'équipement, un buff ou une potion change les statistiques, les gains (vert) et pertes (rouge) s'affichent à côté du personnage.
-- Les valeurs que le client 1.12 ne connaît pas (sorts, critiques, toucher, esquive...) viennent du serveur : commande .fiche donnees,
-- dont la réponse « ##FICHE ... » est lue puis masquée du chat.

local SERVEUR = {}          -- dernières valeurs reçues du serveur
local avant = nil           -- dernier relevé complet
local demande, attente, tAttente, tDerniere = false, false, 0, 0
local afficher = false      -- pas de différences au premier relevé (connexion)

-- ---------------------------------------------------------------- relevé des statistiques
local function Arrondi(v, d)
	local m = 10 ^ (d or 0)
	return math.floor(v * m + 0.5) / m
end

local function DPS(minD, maxD, vitesse)
	if not minD or not vitesse or vitesse <= 0 then return 0 end
	return (minD + maxD) / 2 / vitesse
end

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
		s.minG, s.maxG, s.vitG = minG, maxG, vitG
		s.dpsg = DPS(minG, maxG, vitG)
	end
	if GetInventoryItemLink("player", 18) then
		local vitD, minR, maxR = UnitRangedDamage("player")
		if vitD and vitD > 0 and maxR and maxR > 0 then
			s.minR, s.maxR, s.vitR = minR, maxR, vitD
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
panneau:SetWidth(330)
panneau:SetHeight(76)
panneau:SetPoint("BOTTOMLEFT", CharacterFrame, "TOPLEFT", 14, -12)
panneau:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background", edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
	tile = true, tileSize = 16, edgeSize = 14, insets = { left = 3, right = 3, top = 3, bottom = 3 } })
panneau:SetBackdropColor(0, 0, 0, 0.8)
panneau:SetBackdropBorderColor(0.6, 0.6, 0.6, 1)
local lignes = {}
for i = 1, 4 do
	local fs = panneau:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
	fs:SetPoint("TOPLEFT", panneau, "TOPLEFT", 8, -7 - (i - 1) * 16)
	fs:SetWidth(316)
	fs:SetJustifyH("LEFT")
	lignes[i] = fs
end

local J = "|cffffd100"     -- libellés en jaune
local F = "|r"
local function Nb(v, d)
	if not v then return "?" end
	local t = tostring(Arrondi(v, d or 0))
	return (string.gsub(t, "%.", ","))
end
local function Pct(v)
	if not v then return "?" end
	return Nb(v, 1) .. " %"
end

local function MajPanneau(s)
	local t = J .. "Arme" .. F .. " " .. Nb(s.minD) .. "-" .. Nb(s.maxD) .. " (" .. Nb(s.dps, 1) .. " DPS)"
	if s.dpsg then t = t .. "  " .. J .. "Main g." .. F .. " " .. Nb(s.minG) .. "-" .. Nb(s.maxG) .. " (" .. Nb(s.dpsg, 1) .. ")" end
	if s.dpsd then t = t .. "  " .. J .. "Distance" .. F .. " " .. Nb(s.minR) .. "-" .. Nb(s.maxR) .. " (" .. Nb(s.dpsd, 1) .. ")" end
	lignes[1]:SetText(t)
	lignes[2]:SetText(J .. "PA" .. F .. " " .. Nb(s.pa) .. "  " .. J .. "PA dist." .. F .. " " .. Nb(s.pad) .. "  " .. J .. "Crit." .. F .. " " .. Pct(s.cc)
		.. "  " .. J .. "Toucher" .. F .. " +" .. Pct(s.tm))
	lignes[3]:SetText(J .. "Sorts" .. F .. " +" .. Nb(s.sd) .. "  " .. J .. "Soins" .. F .. " +" .. Nb(s.so) .. "  " .. J .. "Crit. sorts" .. F .. " "
		.. Pct(s.cs) .. "  " .. J .. "Toucher" .. F .. " +" .. Pct(s.ts))
	lignes[4]:SetText(J .. "Esquive" .. F .. " " .. Pct(s.es) .. "  " .. J .. "Parade" .. F .. " " .. Pct(s.pa_) .. "  " .. J .. "Blocage" .. F .. " "
		.. Pct(s.bl) .. "  " .. J .. "Mana/5s" .. F .. " " .. Nb(s.mp) .. "  " .. J .. "iLvl" .. F .. " " .. Nb(s.ilvl, 1))
end

-- ---------------------------------------------------------------- gains et pertes à côté du personnage
-- clé, libellé, décimales, seuil, pourcentage
local STATS = {
	{ "force", "Force", 0, 0.5 }, { "agi", "Agilité", 0, 0.5 }, { "endu", "Endurance", 0, 0.5 }, { "intel", "Intelligence", 0, 0.5 },
	{ "esprit", "Esprit", 0, 0.5 }, { "armure", "Armure", 0, 0.5 }, { "pv", "Points de vie", 0, 0.5 }, { "mana", "Mana", 0, 0.5 },
	{ "pa", "Puissance d'attaque", 0, 0.5 }, { "pad", "Puissance d'attaque à distance", 0, 0.5 },
	{ "dps", "DPS de l'arme", 1, 0.05 }, { "dpsg", "DPS main gauche", 1, 0.05 }, { "dpsd", "DPS à distance", 1, 0.05 },
	{ "sd", "Dégâts des sorts", 0, 0.5 }, { "so", "Soins", 0, 0.5 },
	{ "cc", "Critique", 2, 0.01, true }, { "cd", "Critique à distance", 2, 0.01, true }, { "cs", "Critique des sorts", 2, 0.01, true },
	{ "tm", "Toucher", 2, 0.01, true }, { "ts", "Toucher des sorts", 2, 0.01, true },
	{ "es", "Esquive", 2, 0.01, true }, { "pa_", "Parade", 2, 0.01, true }, { "bl", "Blocage", 2, 0.01, true },
	{ "mp", "Mana toutes les 5 s", 0, 0.5 }, { "rfeu", "Résistance au Feu", 0, 0.5 }, { "rnat", "Résistance à la Nature", 0, 0.5 },
	{ "rgiv", "Résistance au Givre", 0, 0.5 }, { "romb", "Résistance à l'Ombre", 0, 0.5 }, { "rarc", "Résistance aux Arcanes", 0, 0.5 },
	{ "ilvl", "Niveau d'objet moyen", 1, 0.05 },
}

local diff = CreateFrame("Frame", "FicheStatsDiff", UIParent)
diff:SetWidth(300)
diff:SetHeight(400)
diff:SetPoint("RIGHT", UIParent, "CENTER", -90, 40)
diff:SetFrameStrata("HIGH")
local textes = {}
for i = 1, 16 do
	local fs = diff:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
	fs:SetPoint("TOPRIGHT", diff, "TOPRIGHT", 0, -(i - 1) * 22)
	fs:SetJustifyH("RIGHT")
	textes[i] = fs
end
local tAffiche = 0

local function MontrerDifferences(a, b)
	local n = 0
	for _, d in ipairs(STATS) do
		local k, nom, dec, seuil, pct = d[1], d[2], d[3], d[4], d[5]
		local v1, v2 = a[k], b[k]
		if v1 and v2 and math.abs(v2 - v1) >= seuil and n < 16 then
			n = n + 1
			local delta = v2 - v1
			local txt = (delta > 0 and "+" or "") .. Nb(delta, dec) .. (pct and " %" or "") .. " " .. nom
			textes[n]:SetText(txt)
			if delta > 0 then textes[n]:SetTextColor(0.2, 1, 0.2) else textes[n]:SetTextColor(1, 0.25, 0.25) end
		end
	end
	if n == 0 then return end
	for i = n + 1, 16 do textes[i]:SetText("") end
	tAffiche = 5
	diff:SetAlpha(1)
	diff:Show()
end

-- ---------------------------------------------------------------- calcul et échanges avec le serveur
local function Calculer()
	local s = Releve()
	MajPanneau(s)
	if avant and afficher then MontrerDifferences(avant, s) end
	avant = s
	afficher = true
end

local function Lire(msg)
	for k, v in string.gfind(msg, "(%a+)=([%-%d%.]+)") do
		if k == "pa" then k = "pa_" end       -- parade (pa est la puissance d'attaque)
		SERVEUR[k] = tonumber(v)
	end
end

-- masque la réponse du serveur dans le chat
local origChat = ChatFrame_OnEvent
ChatFrame_OnEvent = function(ev)
	if ev == "CHAT_MSG_SYSTEM" and arg1 and string.find(arg1, "^##FICHE") then return end
	origChat(ev)
end

local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_ENTERING_WORLD")
f:RegisterEvent("UNIT_INVENTORY_CHANGED")
f:RegisterEvent("UNIT_AURA")
f:RegisterEvent("UNIT_STATS")
f:RegisterEvent("UNIT_RESISTANCES")
f:RegisterEvent("UNIT_ATTACK_POWER")
f:RegisterEvent("UNIT_RANGED_ATTACK_POWER")
f:RegisterEvent("UNIT_DAMAGE")
f:RegisterEvent("UNIT_MAXHEALTH")
f:RegisterEvent("UNIT_MAXMANA")
f:RegisterEvent("PLAYER_LEVEL_UP")
f:RegisterEvent("CHAT_MSG_SYSTEM")
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
		tDerniere = GetTime() + 2          -- laisse le temps au personnage de se charger
	elseif arg1 and arg1 ~= "player" then
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
		attente = false                     -- pas de réponse (serveur ancien) : calcul sans les valeurs du serveur
		Calculer()
	end
	if tAffiche > 0 then
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
