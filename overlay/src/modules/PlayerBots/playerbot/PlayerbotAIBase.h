#pragma once

class Player;
class PlayerbotMgr;
class ChatHandler;
class PerformanceMonitorOperation;

#include <memory>

class PlayerbotAIBase
{
public:
    PlayerbotAIBase();

public:
    bool IsActive() const;
    virtual void UpdateAI(uint32 elapsed);
    
    uint32 GetAIInternalUpdateDelay() const { return aiInternalUpdateDelay; }

    // [custom vagues] qualite de jeu : multiplicateur du temps de reaction (1 = normal, 4 = debutant)
    void SetReactMult(float mult) { reactMult = mult; }
    float GetReactMult() const { return reactMult; }

protected:
    virtual void UpdateAIInternal(uint32 elapsed, bool minimal = false);
    bool CanUpdateAIInternal() const { return aiInternalUpdateDelay < 100U; }
    void SetAIInternalUpdateDelay(const uint32 delay);
    void ResetAIInternalUpdateDelay() { aiInternalUpdateDelay = 0U; }
    void IncreaseAIInternalUpdateDelay(uint32 delay);
    void YieldAIInternalThread(bool minimal = false);
    
protected:
	uint32 aiInternalUpdateDelay;
    float reactMult = 1.0f;

    std::unique_ptr<PerformanceMonitorOperation> totalPmo;
};
