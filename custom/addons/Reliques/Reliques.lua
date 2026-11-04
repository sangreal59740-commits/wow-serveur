-- Reliques : 4 cases d'artefacts (bleu, rouge, vert, jaune) et 1 case de mascotte sur la fiche du personnage.
-- Glisser un artefact ou une mascotte depuis les sacs sur une case (il va dans la case de sa couleur), clic droit pour le retirer.
-- Le serveur garde l'objet et applique ses statistiques (module reliques) : commandes .relique liste / equiper / retirer,
-- réponses « ##RELIQ ... » lues puis masquées.

local CASES = {
	{ ancre = "CharacterHeadSlot", couleur = { 0.25, 0.5, 1 }, nom = "Artefact bleu", aide = "Endurance" },
	{ ancre = "CharacterNeckSlot", couleur = { 1, 0.25, 0.25 }, nom = "Artefact rouge", aide = "Force ou Intelligence" },
	{ ancre = "CharacterShoulderSlot", couleur = { 0.3, 1, 0.3 }, nom = "Artefact vert", aide = "Critique ou toucher" },
	{ ancre = "CharacterBackSlot", couleur = { 1, 0.85, 0.2 }, nom = "Artefact jaune", aide = "Défense, puissance des sorts ou puissance d'attaque" },
	{ ancre = "CharacterFinger0Slot", couleur = { 0.8, 0.5, 1 }, nom = "Mascotte", aide = "Autant de statistiques qu'un casque", gauche = true },
}
local objets = { 0, 0, 0, 0, 0 }
local boutons = {}
local dernierSac, derniereCase = nil, nil

-- d'où vient l'objet pris par la souris
local origPickup = PickupContainerItem
PickupContainerItem = function(sac, case)
	if not CursorHasItem() then
		dernierSac, derniereCase = sac, case
	end
	origPickup(sac, case)
end

local function Texture(id)
	if not id or id == 0 then return nil end
	local r = { GetItemInfo(id) }
	for i = 1, table.getn(r) do
		if type(r[i]) == "string" and string.find(r[i], "^Interface") then return r[i] end
	end
	return nil
end

local attente = false
local scan = CreateFrame("GameTooltip", "ReliquesScan", nil, "GameTooltipTemplate")
local function MajCases()
	attente = false
	for i, b in ipairs(boutons) do
		local id = objets[i]
		local t = Texture(id)
		if id ~= 0 and not t then
			attente = true
			scan:SetOwner(WorldFrame, "ANCHOR_NONE")
			scan:SetHyperlink("item:" .. id .. ":0:0:0")               -- demande l'objet au serveur
		end
		if t then
			b.icone:SetTexture(t)
			b.icone:SetVertexColor(1, 1, 1)
			b.icone:SetAlpha(1)
		else
			b.icone:SetTexture("Interface\\Buttons\\WHITE8X8")
			b.icone:SetVertexColor(b.c[1], b.c[2], b.c[3])
			b.icone:SetAlpha(id ~= 0 and 0.6 or 0.18)
		end
	end
end

local function Commande(txt)
	SendChatMessage(txt, "SAY")
end

local function Deposer()
	if not CursorHasItem() then return false end
	if not dernierSac then
		ClearCursor()
		DEFAULT_CHAT_FRAME:AddMessage("Reliques : prenez l'objet depuis un sac.", 1, 0.5, 0.5)
		return true
	end
	local sac, case = dernierSac, derniereCase
	ClearCursor()
	Commande(".relique equiper " .. sac .. " " .. case .. " 1")
	return true
end

for i, d in ipairs(CASES) do
	local b = CreateFrame("Button", "ReliquesCase" .. i, PaperDollFrame)
	b:SetWidth(28)
	b:SetHeight(28)
	if d.gauche then
		b:SetPoint("RIGHT", d.ancre, "LEFT", -4, 0)
	else
		b:SetPoint("LEFT", d.ancre, "RIGHT", 4, 0)
	end
	b:SetFrameLevel(PaperDollFrame:GetFrameLevel() + 5)
	local fond = b:CreateTexture(nil, "BACKGROUND")
	fond:SetTexture("Interface\\Buttons\\UI-EmptySlot-White")
	fond:SetWidth(46)
	fond:SetHeight(46)
	fond:SetPoint("CENTER", b, "CENTER", 0, 0)
	b.icone = b:CreateTexture(nil, "ARTWORK")
	b.icone:SetAllPoints(b)
	local bord = b:CreateTexture(nil, "OVERLAY")
	bord:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
	bord:SetBlendMode("ADD")
	bord:SetWidth(50)
	bord:SetHeight(50)
	bord:SetPoint("CENTER", b, "CENTER", 0, 0)
	bord:SetVertexColor(d.couleur[1], d.couleur[2], d.couleur[3])
	bord:SetAlpha(0.8)
	b:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square")
	b.c, b.n, b.d = d.couleur, i, d
	b:RegisterForClicks("LeftButtonUp", "RightButtonUp")
	b:RegisterForDrag("LeftButton")
	b:SetScript("OnReceiveDrag", function() Deposer() end)
	b:SetScript("OnClick", function()
		if Deposer() then return end
		if arg1 == "RightButton" and objets[this.n] ~= 0 then
			Commande(".relique retirer " .. this.n)
		end
	end)
	b:SetScript("OnEnter", function()
		GameTooltip:SetOwner(this, "ANCHOR_RIGHT")
		local id = objets[this.n]
		if id ~= 0 then
			GameTooltip:SetHyperlink("item:" .. id .. ":0:0:0")
			GameTooltip:AddLine("Clic droit : retirer", 0.6, 0.6, 0.6)
		else
			GameTooltip:SetText(this.d.nom, this.c[1], this.c[2], this.c[3])
			GameTooltip:AddLine(this.d.aide, 1, 1, 1)
			GameTooltip:AddLine("Glissez un objet ici depuis vos sacs.", 0.6, 0.6, 0.6)
		end
		GameTooltip:Show()
	end)
	b:SetScript("OnLeave", function() GameTooltip:Hide() end)
	boutons[i] = b
end
MajCases()

-- réponses du serveur
local origChat = ChatFrame_OnEvent
ChatFrame_OnEvent = function(ev)
	if ev == "CHAT_MSG_SYSTEM" and arg1 and string.find(arg1, "^##RELIQ") then return end
	origChat(ev)
end

local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_ENTERING_WORLD")
f:RegisterEvent("CHAT_MSG_SYSTEM")
local tDemande, tMaj = 0, 0
f:SetScript("OnEvent", function()
	if event == "PLAYER_ENTERING_WORLD" then
		tDemande = GetTime() + 3
	elseif arg1 and string.find(arg1, "^##RELIQ") then
		for n, id in string.gfind(arg1, "(%d)=(%d+)") do
			objets[tonumber(n)] = tonumber(id)
		end
		MajCases()
	end
end)
f:SetScript("OnUpdate", function()
	local now = GetTime()
	if tDemande > 0 and now >= tDemande then
		tDemande = 0
		Commande(".relique liste")
	end
	if attente and now - tMaj > 1 then
		tMaj = now
		MajCases()
	end
end)
