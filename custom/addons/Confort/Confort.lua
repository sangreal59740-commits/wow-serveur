-- Confort : petites ameliorations de l'interface 1.12
-- 1. Fenetres deplacables : Maj + clic gauche maintenu sur la fenetre, puis glisser. /fenetres reset pour tout remettre.
-- 2. Barres d'action verrouillees : un sort ne se deplace qu'avec Maj + glisser. /verrou pour verrouiller ou deverrouiller.
-- 3. Infobulle des monstres : progression des objectifs de quete qui les concernent (ex. Troll : 3/10).

Confort_Pos = Confort_Pos or {}

local FENETRES = {
	"CharacterFrame", "SpellBookFrame", "QuestLogFrame", "FriendsFrame", "GossipFrame", "QuestFrame",
	"MerchantFrame", "BankFrame", "MailFrame", "OpenMailFrame", "TaxiFrame", "PetStableFrame", "TradeFrame",
	"LootFrame", "LFGParentFrame", "WorldStateScoreFrame", "ItemTextFrame", "DressUpFrame", "TabardFrame",
	"GuildRegistrarFrame", "PetitionFrame", "HelpFrame",
	"ContainerFrame1", "ContainerFrame2", "ContainerFrame3", "ContainerFrame4", "ContainerFrame5",
	"ContainerFrame6", "ContainerFrame7", "ContainerFrame8", "ContainerFrame9", "ContainerFrame10",
	-- chargees a la demande
	"TalentFrame", "ClassTrainerFrame", "TradeSkillFrame", "CraftFrame", "InspectFrame", "AuctionFrame",
	"MacroFrame", "KeyBindingFrame", "BattlefieldFrame",
}

local prepares = {}

local function Sauver(cadre)
	local point, _, relPoint, x, y = cadre:GetPoint(1)
	Confort_Pos[cadre:GetName()] = { point, relPoint, x, y }
end

local function Restaurer(cadre)
	if not cadre or not cadre.GetName then return end
	local p = Confort_Pos[cadre:GetName()]
	if p then
		cadre:ClearAllPoints()
		cadre:SetPoint(p[1], UIParent, p[2], p[3], p[4])
	end
end

local function Preparer(nom)
	if prepares[nom] then return end
	local cadre = getglobal(nom)
	if not cadre then return end
	prepares[nom] = 1
	cadre:SetMovable(true)
	cadre:EnableMouse(true)
	cadre:SetClampedToScreen(true)
	cadre:RegisterForDrag("LeftButton")
	local ancienDebut = cadre:GetScript("OnDragStart")
	local ancienFin = cadre:GetScript("OnDragStop")
	cadre:SetScript("OnDragStart", function()
		if IsShiftKeyDown() then
			this:StartMoving()
			this.cfDeplace = 1
		elseif ancienDebut then
			ancienDebut()
		end
	end)
	cadre:SetScript("OnDragStop", function()
		if this.cfDeplace then
			this:StopMovingOrSizing()
			this.cfDeplace = nil
			Sauver(this)
		elseif ancienFin then
			ancienFin()
		end
	end)
	-- le jeu replace la fenetre a chaque ouverture : on remet la position choisie
	local ancienShow = cadre:GetScript("OnShow")
	cadre:SetScript("OnShow", function()
		if ancienShow then ancienShow() end
		Restaurer(this)
	end)
end

local function PreparerTout()
	for i = 1, table.getn(FENETRES) do Preparer(FENETRES[i]) end
end

-- ShowUIPanel et l'empilement des sacs repositionnent les fenetres apres coup
local origShowUIPanel = ShowUIPanel
ShowUIPanel = function(cadre, force)
	origShowUIPanel(cadre, force)
	if cadre and cadre.GetName and prepares[cadre:GetName() or ""] then Restaurer(cadre) end
end
local origUpdateAnchors = updateContainerFrameAnchors
if origUpdateAnchors then
	updateContainerFrameAnchors = function()
		origUpdateAnchors()
		for i = 1, 10 do
			local c = getglobal("ContainerFrame" .. i)
			if c and c:IsShown() then Restaurer(c) end
		end
	end
end

-- Barres d'action ----------------------------------------------------------
local function AppliquerVerrou()
	if Confort_Verrou == nil then Confort_Verrou = 1 end
	if Confort_Verrou == 1 then
		LOCK_ACTIONBAR = "1"
	else
		LOCK_ACTIONBAR = "0"
	end
	if SetCVar then pcall(SetCVar, "lockActionBars", LOCK_ACTIONBAR) end
end

-- en 1.12, une barre verrouillee bloque tout : Maj + glisser reprend le sort
local BARRES = { "ActionButton", "MultiBarBottomLeftButton", "MultiBarBottomRightButton", "MultiBarRightButton",
	"MultiBarLeftButton", "BonusActionButton" }
local function PreparerBoutons()
	for b = 1, table.getn(BARRES) do
		for i = 1, 12 do
			local bouton = getglobal(BARRES[b] .. i)
			if bouton and not bouton.cfVerrou then
				bouton.cfVerrou = 1
				local orig = bouton:GetScript("OnDragStart")
				bouton:SetScript("OnDragStart", function()
					if LOCK_ACTIONBAR == "1" then
						if IsShiftKeyDown() then
							PickupAction(ActionButton_GetPagedID(this))
							if ActionButton_UpdateState then ActionButton_UpdateState() end
							if ActionButton_UpdateFlash then ActionButton_UpdateFlash() end
						end
					elseif orig then
						orig()
					end
				end)
			end
		end
	end
end

-- Infobulle des monstres -----------------------------------------------------
local function ObjectifsPour(nom)
	local lignes = {}
	if not nom or nom == "" then return lignes end
	local n = GetNumQuestLogEntries()
	for i = 1, n do
		local titre, _, _, entete = GetQuestLogTitle(i)
		if not entete then
			local nb = GetNumQuestLeaderBoards(i) or 0
			for j = 1, nb do
				local texte, genre, fini = GetQuestLogLeaderBoard(j, i)
				if texte and genre == "monster" and string.find(texte, nom, 1, true) then
					table.insert(lignes, { titre, texte, fini })
				end
			end
		end
	end
	return lignes
end

local function DejaPresent(tip, texte)
	local nom = tip:GetName()
	for i = 1, tip:NumLines() do
		local l = getglobal(nom .. "TextLeft" .. i)
		if l then
			local t = l:GetText()
			if t and string.find(t, texte, 1, true) then return true end
		end
	end
	return false
end

local origSetUnit = GameTooltip.SetUnit
GameTooltip.SetUnit = function(self, unite)
	origSetUnit(self, unite)
	if not unite or not UnitExists(unite) or UnitIsPlayer(unite) then return end
	local lignes = ObjectifsPour(UnitName(unite))
	local ajoute = false
	for k = 1, table.getn(lignes) do
		local l = lignes[k]
		if not DejaPresent(self, l[2]) then
			if l[3] then
				self:AddLine(l[2], 0.5, 0.5, 0.5)
			else
				self:AddLine(l[2], 1, 0.82, 0)
			end
			ajoute = true
		end
	end
	if ajoute then self:Show() end
end

-- Evenements ---------------------------------------------------------------
local f = CreateFrame("Frame")
f:RegisterEvent("VARIABLES_LOADED")
f:RegisterEvent("ADDON_LOADED")
f:RegisterEvent("PLAYER_ENTERING_WORLD")
f:SetScript("OnEvent", function()
	if event == "VARIABLES_LOADED" then
		PreparerTout()
		PreparerBoutons()
		AppliquerVerrou()
	elseif event == "ADDON_LOADED" then
		PreparerTout()
	else
		PreparerBoutons()
		AppliquerVerrou()
	end
end)

SLASH_CONFORTFEN1 = "/fenetres"
SlashCmdList["CONFORTFEN"] = function(msg)
	if msg == "reset" then
		Confort_Pos = {}
		DEFAULT_CHAT_FRAME:AddMessage("Confort : positions des fenetres effacees, fais /console reloadui.")
	else
		DEFAULT_CHAT_FRAME:AddMessage("Confort : Maj + glisser pour deplacer une fenetre. /fenetres reset pour tout remettre en place.")
	end
end

SLASH_CONFORTVERROU1 = "/verrou"
SlashCmdList["CONFORTVERROU"] = function()
	if Confort_Verrou == 1 then Confort_Verrou = 0 else Confort_Verrou = 1 end
	AppliquerVerrou()
	if Confort_Verrou == 1 then
		DEFAULT_CHAT_FRAME:AddMessage("Confort : barres d'action verrouillees (Maj + glisser pour bouger un sort).")
	else
		DEFAULT_CHAT_FRAME:AddMessage("Confort : barres d'action deverrouillees.")
	end
end
