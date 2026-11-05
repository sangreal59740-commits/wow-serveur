-- CadresPlus : valeurs sur les barres (joueur, cible, groupe) et cadres deplacables
-- Deplacer un cadre : Maj + clic gauche maintenu, puis glisser.
-- /cadres reset : remet les cadres a leur place d'origine.

CadresPlus_Pos = CadresPlus_Pos or {}

local BARRES = {
	{ "PlayerFrameHealthBar", "player", "vie" },
	{ "PlayerFrameManaBar", "player", "mana" },
	{ "TargetFrameHealthBar", "target", "vie" },
	{ "TargetFrameManaBar", "target", "mana" },
	{ "PetFrameHealthBar", "pet", "vie" },
	{ "PetFrameManaBar", "pet", "mana" },
}
for i = 1, 4 do
	table.insert(BARRES, { "PartyMemberFrame" .. i .. "HealthBar", "party" .. i, "vie" })
	table.insert(BARRES, { "PartyMemberFrame" .. i .. "ManaBar", "party" .. i, "mana" })
end

local CADRES = { "PlayerFrame", "TargetFrame", "PartyMemberFrame1", "PetFrame" }

local textes = {}

local function Abrege(v)
	if v >= 100000 then
		return string.format("%.0fk", v / 1000)
	elseif v >= 10000 then
		return string.format("%.1fk", v / 1000)
	end
	return tostring(v)
end

-- texte du jeu (affiché quand la fiche du personnage est ouverte) : masqué, il se superposait aux valeurs permanentes
local function MasquerTexteJeu(nom)
	local bt = getglobal(nom .. "Text")
	if bt then
		bt:Hide()
		bt.Show = function() end
	end
end

local function CreerTexte(barre)
	local t = barre:CreateFontString(nil, "OVERLAY")
	t:SetFont("Fonts\\FRIZQT__.TTF", 10, "OUTLINE")
	t:SetPoint("CENTER", barre, "CENTER", 0, 0)
	t:SetTextColor(1, 1, 1)
	return t
end

local function MettreAJour()
	for i = 1, table.getn(BARRES) do
		local def = BARRES[i]
		local barre = getglobal(def[1])
		if barre then
			local t = textes[def[1]]
			if not t then
				MasquerTexteJeu(def[1])
				t = CreerTexte(barre)
				textes[def[1]] = t
			end
			local unite = def[2]
			if barre:IsVisible() and UnitExists(unite) then
				local v, m
				if def[3] == "vie" then
					v, m = UnitHealth(unite), UnitHealthMax(unite)
				else
					v, m = UnitMana(unite), UnitManaMax(unite)
				end
				if not m or m == 0 or UnitIsDeadOrGhost(unite) then
					t:SetText("")
				elseif def[3] == "vie" and m == 100 and not UnitIsUnit(unite, "player")
					and not UnitInParty(unite) and not UnitIsUnit(unite, "pet") then
					-- en 1.12 le jeu ne donne que le pourcentage pour les monstres et les inconnus
					t:SetText(v .. " %")
				else
					t:SetText(Abrege(v) .. " / " .. Abrege(m))
				end
			else
				t:SetText("")
			end
		end
	end
end

-- Cadres deplacables -------------------------------------------------------
local function Sauver(cadre)
	local point, _, relPoint, x, y = cadre:GetPoint(1)
	CadresPlus_Pos[cadre:GetName()] = { point, relPoint, x, y }
end

local function Restaurer(cadre)
	local p = CadresPlus_Pos[cadre:GetName()]
	if p then
		cadre:ClearAllPoints()
		cadre:SetPoint(p[1], UIParent, p[2], p[3], p[4])
	end
end

local function Deplacable(nom)
	local cadre = getglobal(nom)
	if not cadre then return end
	cadre:SetMovable(true)
	cadre:SetClampedToScreen(true)
	cadre:RegisterForDrag("LeftButton")
	cadre:SetScript("OnDragStart", function()
		if IsShiftKeyDown() then
			this:StartMoving()
			this.cpDeplace = 1
		end
	end)
	cadre:SetScript("OnDragStop", function()
		if this.cpDeplace then
			this:StopMovingOrSizing()
			this.cpDeplace = nil
			Sauver(this)
		end
	end)
	Restaurer(cadre)
end

local f = CreateFrame("Frame")
f:RegisterEvent("VARIABLES_LOADED")
f:RegisterEvent("PLAYER_ENTERING_WORLD")
f:SetScript("OnEvent", function()
	if event == "VARIABLES_LOADED" then
		for i = 1, table.getn(CADRES) do Deplacable(CADRES[i]) end
	else
		for i = 1, table.getn(CADRES) do
			local c = getglobal(CADRES[i])
			if c then Restaurer(c) end
		end
	end
end)

local attente = 0
f:SetScript("OnUpdate", function()
	attente = attente + (arg1 or 0)
	if attente < 0.1 then return end
	attente = 0
	MettreAJour()
end)

SLASH_CADRESPLUS1 = "/cadres"
SlashCmdList["CADRESPLUS"] = function(msg)
	if msg == "reset" then
		CadresPlus_Pos = {}
		DEFAULT_CHAT_FRAME:AddMessage("CadresPlus : positions effacees, fais /console reloadui.")
	else
		DEFAULT_CHAT_FRAME:AddMessage("CadresPlus : Maj + glisser pour deplacer un cadre. /cadres reset pour tout remettre en place.")
	end
end
