-- Bouton « Pull » : le tank bot du groupe va chercher ta cible (ou le monstre le plus proche si tu n'as rien en cible).
-- Clic gauche : pull. Clic droit : pull automatique du tank activé / coupé. Maj + glisser : déplacer le bouton.
-- Commandes : /pull et /pull auto
local b = CreateFrame("Button", "BotsPullButton", UIParent)
b:SetWidth(40); b:SetHeight(40)
b:SetPoint("CENTER", UIParent, "CENTER", 0, -180)
b:SetMovable(true); b:EnableMouse(true)
b:RegisterForDrag("LeftButton")
b:RegisterForClicks("LeftButtonUp", "RightButtonUp")
b:SetNormalTexture("Interface\\Icons\\INV_Shield_06")
b:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square")
b:GetHighlightTexture():SetBlendMode("ADD")
local t = b:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
t:SetPoint("TOP", b, "BOTTOM", 0, -2)
t:SetText("Pull")
local etat = b:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
etat:SetPoint("BOTTOMRIGHT", b, "BOTTOMRIGHT", -2, 2)

local function MajEtat()
	if BotsPullAuto == false then
		etat:SetText("|cffff5555M|r")
	else
		etat:SetText("|cff55ff55A|r")
	end
end

local function Pull()
	SendChatMessage(".bots pull", "SAY")
end

local function BasculerAuto()
	if BotsPullAuto == false then
		BotsPullAuto = true
		SendChatMessage(".bots pull auto on", "SAY")
	else
		BotsPullAuto = false
		SendChatMessage(".bots pull auto off", "SAY")
	end
	MajEtat()
end

b:SetScript("OnClick", function()
	if arg1 == "RightButton" then BasculerAuto() else Pull() end
end)
b:SetScript("OnDragStart", function() if IsShiftKeyDown() then this:StartMoving() end end)
b:SetScript("OnDragStop", function() this:StopMovingOrSizing() end)
b:SetScript("OnEnter", function()
	GameTooltip:SetOwner(this, "ANCHOR_TOP")
	GameTooltip:AddLine("Pull du tank")
	GameTooltip:AddLine("Clic gauche : le tank pull ta cible (ou le monstre le plus proche).", 1, 1, 1, 1)
	GameTooltip:AddLine("Clic droit : pull automatique on/off (A = auto, M = manuel).", 1, 1, 1, 1)
	GameTooltip:AddLine("Maj + glisser : déplacer.", 0.7, 0.7, 0.7, 1)
	GameTooltip:Show()
end)
b:SetScript("OnLeave", function() GameTooltip:Hide() end)
b:RegisterEvent("VARIABLES_LOADED")
b:RegisterEvent("PLAYER_ENTERING_WORLD")
b:SetScript("OnEvent", function()
	MajEtat()
	-- le serveur oublie le réglage à chaque redémarrage : on le lui redonne
	if event == "PLAYER_ENTERING_WORLD" and BotsPullAuto == false then
		SendChatMessage(".bots pull auto off", "SAY")
	end
end)

SLASH_BOTSPULL1 = "/pull"
SlashCmdList["BOTSPULL"] = function(msg)
	if msg and string.find(msg, "auto") then BasculerAuto() else Pull() end
end
