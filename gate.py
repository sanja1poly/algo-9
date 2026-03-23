from dataclasses import dataclass

@dataclass
class GateDecision:
    allow: bool
    p_win: float
    reason: str

def trade_gate(p_win: float, min_p: float, liquidity_ok: bool, risk_ok: bool, ev_ok: bool) -> GateDecision:
    if not liquidity_ok:
        return GateDecision(False, p_win, "LIQUIDITY_BLOCK")
    if not risk_ok:
        return GateDecision(False, p_win, "RISK_BLOCK")
    if not ev_ok:
        return GateDecision(False, p_win, "EV_BLOCK")
    if p_win < min_p:
        return GateDecision(False, p_win, "PROB_BELOW_THRESHOLD")
    return GateDecision(True, p_win, "OK")
