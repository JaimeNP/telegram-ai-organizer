from dataclasses import dataclass


@dataclass
class BotDecision:
    action: str
    reason: str
    confidence: float
    simulated: bool = True