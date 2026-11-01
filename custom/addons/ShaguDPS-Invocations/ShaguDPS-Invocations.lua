-- Les invocations du serveur sont des gardiens : le jeu ne dit pas a qui elles appartiennent.
-- On les rattache au joueur (ou au membre du groupe) de la classe qui les invoque, en priorite au joueur lui-meme.
if not ShaguDPS or not ShaguDPS.parser then return end

local CLASSES = {
	["Squelette"] = { "Nécromancien" }, ["Goule"] = { "Nécromancien" }, ["Abomination"] = { "Nécromancien" },
	["Squelette de givre"] = { "Nécromancien" }, ["Chien squelettique"] = { "Nécromancien" },
	["Chevalier de la mort"] = { "Nécromancien" }, ["Wyrm de givre"] = { "Nécromancien" },
	["Sanglier"] = { "Sniper" }, ["Tigre blanc"] = { "Sniper" }, ["Ours brun"] = { "Sniper" }, ["Dinosaure"] = { "Sniper" },
	["Griffon"] = { "Sniper" }, ["Tourelle"] = { "Sniper" }, ["Canon à boulets"] = { "Sniper" }, ["Robot"] = { "Sniper" },
	["Compagnon de meute"] = { "Sniper" },
	["Totem de feu"] = { "Métamorphe" }, ["Totem de givre"] = { "Métamorphe" }, ["Totem d'eau"] = { "Métamorphe" },
	["Fantôme"] = { "Voleur", "Voleuse" },
	["Rat corrompu"] = { "Prêtre", "Prêtresse" },
}

local function ClasseOk(unit, liste)
	if not UnitExists(unit) or not UnitIsPlayer(unit) then return false end
	local c = UnitClass(unit)
	for i = 1, table.getn(liste) do
		if c == liste[i] then return true end
	end
	return false
end

local function Proprietaire(nom)
	local liste = CLASSES[nom]
	if not liste then return nil end
	if ClasseOk("player", liste) then return UnitName("player") end
	local raid = GetNumRaidMembers()
	if raid > 0 then
		for i = 1, raid do
			if ClasseOk("raid" .. i, liste) then return UnitName("raid" .. i) end
		end
	else
		for i = 1, GetNumPartyMembers() do
			if ClasseOk("party" .. i, liste) then return UnitName("party" .. i) end
		end
	end
	return nil
end

local parser = ShaguDPS.parser
local origScan = parser.ScanName
parser.ScanName = function(self, name)
	local r = origScan(self, name)
	if r == "PLAYER" or r == "PET" then return r end
	if name then
		local owner = Proprietaire(name)
		if owner then
			ShaguDPS.data["classes"][name] = owner
			return "PET"
		end
	end
	return r
end
