-- Groupe de 6 : buff « Groupe complet » (6 vrais joueurs dans le même donjon : +50 % d'XP sur les monstres du donjon)
-- Aura factice : l'effet est appliqué par le module compagnons.
DELETE FROM spell_template WHERE Id=46991;
DROP TEMPORARY TABLE IF EXISTS tmp_sp;
CREATE TEMPORARY TABLE tmp_sp LIKE spell_template;
INSERT INTO tmp_sp SELECT * FROM spell_template WHERE Id=12042;
UPDATE tmp_sp SET Id=46991, SpellName='Groupe complet', Rank1='', School=0, Category=0, Dispel=0, Mechanic=0,
  Attributes=2147549184, AttributesEx=0, AttributesEx2=0, AttributesEx3=1048576, AttributesEx4=0, Stances=0, StancesNot=0, Targets=0,
  CastingTimeIndex=1, RecoveryTime=0, CategoryRecoveryTime=0, InterruptFlags=0, AuraInterruptFlags=0, ChannelInterruptFlags=0,
  ProcFlags=0, ProcChance=101, ProcCharges=0, MaxLevel=0, BaseLevel=0, SpellLevel=0, DurationIndex=21, PowerType=0, ManaCost=0,
  ManaCostPerlevel=0, ManaPerSecond=0, ManaPerSecondPerLevel=0, RangeIndex=1, StackAmount=0, ManaCostPercentage=0,
  StartRecoveryTime=0, StartRecoveryCategory=0, SpellVisual=0, SpellIconID=1669, SpellFamilyName=0, SpellFamilyFlags=0,
  Effect1=6, EffectApplyAuraName1=4, EffectMiscValue1=0, EffectBasePoints1=49, EffectDieSides1=1, EffectImplicitTargetA1=1, EffectImplicitTargetB1=0,
  EffectRadiusIndex1=0, EffectAmplitude1=0, EffectTriggerSpell1=0,
  Effect2=0, EffectApplyAuraName2=0, EffectMiscValue2=0, EffectBasePoints2=0, EffectDieSides2=0, EffectImplicitTargetA2=0, EffectImplicitTargetB2=0,
  Effect3=0, EffectApplyAuraName3=0, EffectMiscValue3=0, EffectBasePoints3=0, EffectDieSides3=0, EffectImplicitTargetA3=0, EffectImplicitTargetB3=0
  WHERE Id=12042;
INSERT INTO spell_template SELECT * FROM tmp_sp;
DROP TEMPORARY TABLE tmp_sp;
SELECT Id, SpellName FROM spell_template WHERE Id=46991;
