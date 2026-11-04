-- NiveauObjet : niveau d'objet (ilvl) dans les infobulles, moyenne du personnage et de la cible inspectée
local NIV = {}
for _, bloc in ipairs(NiveauObjet_Donnees) do
	for id, niv in string.gfind(bloc, "(%d+):(%d+)") do
		NIV[tonumber(id)] = tonumber(niv)
	end
end
NiveauObjet_Donnees = nil

local function NiveauDuLien(lien)
	if not lien then return nil end
	local _, _, id = string.find(lien, "item:(%d+)")
	if id then return NIV[tonumber(id)] end
end

-- ---------------------------------------------------------------- infobulles
local function Ajouter(tip, lien)
	local n = NiveauDuLien(lien)
	if n then
		tip:AddLine("Niveau d'objet " .. n, 1, 0.82, 0)
		tip:Show()
	end
end

local function Accrocher(tip, methode, quelLien)
	local orig = tip[methode]
	if not orig then return end
	tip[methode] = function(self, a1, a2, a3, a4)
		local r1, r2, r3 = orig(self, a1, a2, a3, a4)
		local ok, lien = pcall(quelLien, a1, a2, a3, a4)
		if ok then Ajouter(self, lien) end
		return r1, r2, r3
	end
end

local function AccrocherTout(tip)
	Accrocher(tip, "SetBagItem", function(b, s) return GetContainerItemLink(b, s) end)
	Accrocher(tip, "SetInventoryItem", function(u, s) return GetInventoryItemLink(u, s) end)
	Accrocher(tip, "SetHyperlink", function(l) return l end)
	Accrocher(tip, "SetLootItem", function(s) return GetLootSlotLink(s) end)
	Accrocher(tip, "SetLootRollItem", function(i) return GetLootRollItemLink(i) end)
	Accrocher(tip, "SetMerchantItem", function(i) return GetMerchantItemLink(i) end)
	Accrocher(tip, "SetBuybackItem", function(i) return GetBuybackItemLink and GetBuybackItemLink(i) end)
	Accrocher(tip, "SetQuestItem", function(t, i) return GetQuestItemLink(t, i) end)
	Accrocher(tip, "SetQuestLogItem", function(t, i) return GetQuestLogItemLink(t, i) end)
	Accrocher(tip, "SetAuctionItem", function(t, i) return GetAuctionItemLink(t, i) end)
	Accrocher(tip, "SetTradePlayerItem", function(i) return GetTradePlayerItemLink(i) end)
	Accrocher(tip, "SetTradeTargetItem", function(i) return GetTradeTargetItemLink(i) end)
	Accrocher(tip, "SetTradeSkillItem", function(i, r)
		if r then return GetTradeSkillReagentItemLink(i, r) end
		return GetTradeSkillItemLink(i)
	end)
	Accrocher(tip, "SetCraftItem", function(i, r)
		if r then return GetCraftReagentItemLink(i, r) end
		return GetCraftItemLink(i)
	end)
end
AccrocherTout(GameTooltip)
if ItemRefTooltip then AccrocherTout(ItemRefTooltip) end
if ShoppingTooltip1 then AccrocherTout(ShoppingTooltip1) end
if ShoppingTooltip2 then AccrocherTout(ShoppingTooltip2) end

-- ---------------------------------------------------------------- moyenne d'équipement
-- emplacements comptés : tout sauf chemise (4) et tabard (19) ; une arme à deux mains compte double
local EMPL = { 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 }
local function Moyenne(unite)
	local total, nb = 0, 0
	for _, s in ipairs(EMPL) do
		local lien = GetInventoryItemLink(unite, s)
		local n = NiveauDuLien(lien)
		if s == 17 and not lien then
			-- main gauche vide : l'arme principale (deux mains) compte pour les deux
			local n16 = NiveauDuLien(GetInventoryItemLink(unite, 16))
			if n16 then total = total + n16 end
			nb = nb + 1
		else
			if n then total = total + n end
			nb = nb + 1
		end
	end
	if nb == 0 or total == 0 then return nil end
	return math.floor(total / nb * 10 + 0.5) / 10
end

NiveauObjet_Moyenne = Moyenne     -- utilisé par FicheStats

local function Couleur(n)
	if n >= 120 then return "|cffff8000" elseif n >= 70 then return "|cffa335ee" elseif n >= 50 then return "|cff0070dd" end
	return "|cff1eff00"
end

local function Texte(fs, unite)
	local m = Moyenne(unite)
	if m then fs:SetText("Niveau d'objet : " .. Couleur(m) .. m .. "|r") else fs:SetText("") end
end

-- fiche du personnage
local perso = CharacterModelFrame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
perso:SetPoint("TOP", CharacterModelFrame, "TOP", 0, -4)
local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_ENTERING_WORLD")
f:RegisterEvent("UNIT_INVENTORY_CHANGED")
f:RegisterEvent("ADDON_LOADED")
f:SetScript("OnEvent", function()
	if event == "ADDON_LOADED" or event == "PLAYER_ENTERING_WORLD" then
		if InspectModelFrame and not NiveauObjet_Inspect then
			NiveauObjet_Inspect = InspectModelFrame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
			NiveauObjet_Inspect:SetPoint("TOP", InspectModelFrame, "TOP", 0, -4)
		end
		if event == "ADDON_LOADED" then return end
	end
	if event == "UNIT_INVENTORY_CHANGED" and arg1 ~= "player" then return end
	Texte(perso, "player")
end)
local ancienOnShow = PaperDollFrame:GetScript("OnShow")
PaperDollFrame:SetScript("OnShow", function()
	if ancienOnShow then ancienOnShow() end
	Texte(perso, "player")
end)

-- inspection : rafraîchi tant que la fenêtre est ouverte (les objets arrivent avec un délai)
local t = 0
f:SetScript("OnUpdate", function()
	t = t + arg1
	if t < 0.5 then return end
	t = 0
	if NiveauObjet_Inspect and InspectFrame and InspectFrame:IsVisible() then
		Texte(NiveauObjet_Inspect, "target")
	end
end)
