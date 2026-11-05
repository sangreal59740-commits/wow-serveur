-- VenteHV : dans l'onglet « Enchères » de l'hôtel des ventes du jeu, quand on pose un objet à vendre,
-- cherche les mêmes objets déjà en vente, affiche leurs prix (à l'unité) à droite de la fenêtre
-- et propose le prix le plus bas moins 1 pièce de cuivre. Clic sur une ligne : reprend ce prix.

local panneau, lignes, info
local recherche = nil        -- { nom, page, offres }
local MAXPAGES = 5
local NB = 12

local function Argent(c)
	c = math.floor(c + 0.5)
	local po, pa, pc = math.floor(c / 10000), math.floor(math.mod(c, 10000) / 100), math.mod(c, 100)
	local t = ""
	if po > 0 then t = t .. "|cffffd700" .. po .. "po|r " end
	if pa > 0 or po > 0 then t = t .. "|cffc7c7cf" .. pa .. "pa|r " end
	return t .. "|cffeda55f" .. pc .. "pc|r"
end

local function PrixVente(unitaire)
	local _, _, nombre = GetAuctionSellItemInfo()
	nombre = nombre or 1
	local achat = math.max(1, math.floor(unitaire * nombre))
	local depart = math.max(1, math.floor(achat * 0.9))
	MoneyInputFrame_SetCopper(StartPrice, depart)
	MoneyInputFrame_SetCopper(BuyoutPrice, achat)
end

local function Afficher()
	if not recherche then return end
	local o = recherche.offres
	table.sort(o, function(a, b) return a.unite < b.unite end)
	for i = 1, NB do
		local l = lignes[i]
		local x = o[i]
		if x then
			l.texte:SetText(x.nombre .. " x   " .. Argent(x.unite) .. "   |cff999999" .. (x.vendeur or "?") .. "|r")
			l.unite = x.unite
			l:Show()
		else
			l:Hide()
		end
	end
	if table.getn(o) == 0 then
		info:SetText(recherche.fini and "Aucun objet identique en vente." or "Recherche...")
	else
		info:SetText((recherche.fini and "" or "Recherche... ") .. table.getn(o) .. " offre(s), prix à l'unité")
		if recherche.fini and not recherche.applique then
			recherche.applique = true
			PrixVente(math.max(1, o[1].unite - 1))
		end
	end
end

local function Lancer(nom)
	recherche = { nom = nom, page = 0, offres = {}, attente = true }
	info:SetText("Recherche...")
	for i = 1, NB do lignes[i]:Hide() end
	panneau:Show()
end

local function Creer()
	if panneau then return end
	panneau = CreateFrame("Frame", "VenteHVPanneau", AuctionFrameAuctions)
	panneau:SetWidth(250)
	panneau:SetHeight(60 + NB * 16)
	panneau:SetPoint("TOPLEFT", AuctionFrame, "TOPRIGHT", -2, -12)
	panneau:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background", edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
		tile = true, tileSize = 16, edgeSize = 14, insets = { left = 4, right = 4, top = 4, bottom = 4 } })
	panneau:SetBackdropColor(0, 0, 0, 0.85)
	local titre = panneau:CreateFontString(nil, "OVERLAY", "GameFontNormal")
	titre:SetPoint("TOPLEFT", panneau, "TOPLEFT", 10, -10)
	titre:SetText("Mêmes objets en vente")
	info = panneau:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
	info:SetPoint("TOPLEFT", titre, "BOTTOMLEFT", 0, -4)
	lignes = {}
	for i = 1, NB do
		local b = CreateFrame("Button", nil, panneau)
		b:SetWidth(230)
		b:SetHeight(16)
		b:SetPoint("TOPLEFT", panneau, "TOPLEFT", 10, -44 - (i - 1) * 16)
		b.texte = b:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
		b.texte:SetPoint("LEFT", b, "LEFT", 0, 0)
		b:SetHighlightTexture("Interface\\QuestFrame\\UI-QuestTitleHighlight")
		b:SetScript("OnClick", function() if this.unite then PrixVente(math.max(1, this.unite - 1)) end end)
		b:SetScript("OnEnter", function()
			GameTooltip:SetOwner(this, "ANCHOR_RIGHT")
			GameTooltip:SetText("Clic : vendre 1 pc moins cher que cette offre")
			GameTooltip:Show()
		end)
		b:SetScript("OnLeave", function() GameTooltip:Hide() end)
		lignes[i] = b
	end
	panneau:Hide()
end

local f = CreateFrame("Frame")
f:RegisterEvent("ADDON_LOADED")
f:RegisterEvent("NEW_AUCTION_UPDATE")
f:RegisterEvent("AUCTION_ITEM_LIST_UPDATE")
f:RegisterEvent("AUCTION_HOUSE_CLOSED")
f:SetScript("OnEvent", function()
	if event == "ADDON_LOADED" then
		if arg1 == "Blizzard_AuctionUI" then Creer() end
	elseif event == "NEW_AUCTION_UPDATE" then
		Creer()
		local nom = GetAuctionSellItemInfo()
		if nom then Lancer(nom) else recherche = nil panneau:Hide() end
	elseif event == "AUCTION_ITEM_LIST_UPDATE" then
		if not recherche or recherche.attente or recherche.fini then return end
		local n, total = GetNumAuctionItems("list")
		for i = 1, n do
			local nom, _, nombre, _, _, _, _, _, achat, _, _, vendeur = GetAuctionItemInfo("list", i)
			if nom == recherche.nom and achat and achat > 0 and nombre and nombre > 0 then
				table.insert(recherche.offres, { nombre = nombre, unite = achat / nombre, vendeur = vendeur })
			end
		end
		recherche.page = recherche.page + 1
		if recherche.page * 50 >= (total or 0) or recherche.page >= MAXPAGES then
			recherche.fini = true
		else
			recherche.attente = true
		end
		Afficher()
	elseif event == "AUCTION_HOUSE_CLOSED" then
		recherche = nil
	end
end)
-- les recherches attendent que le serveur accepte une nouvelle requête
f:SetScript("OnUpdate", function()
	if recherche and recherche.attente and CanSendAuctionQuery() then
		recherche.attente = false
		QueryAuctionItems(recherche.nom, nil, nil, 0, 0, 0, recherche.page, 0, 0)
	end
end)
