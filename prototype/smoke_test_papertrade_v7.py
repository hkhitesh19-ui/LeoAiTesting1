from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.indicators_v1 import compute_indicators
from prototype.papertrade_engine_v2 import PaperTradeEngineV2
from prototype.signals_v1_compat_v3 import generate_signal_v1


def main():
    print("=== SMOKE TEST: PAPERTRADE V7 (STRICT SIGNAL CONTRACT) ===")

    broker = ShoonyaAdapterV4()
    assert broker.login(), "Login failed"
    print("✅ Login OK")

    pack = broker.get_spot_candles_1h_pack()
    print("✅ CandlePack OK")

    ind = compute_indicators(pack)
    print("✅ IndicatorPack OK")

    sig = generate_signal_v1(ind.to_dict())
    assert isinstance(sig, dict)
    assert "decision" in sig
    assert "close" in sig
    print("✅ SignalPack OK")

    engine = PaperTradeEngineV2()
    r1 = engine.step(sig)
    r2 = engine.step(sig)

    assert r2["action"]["action"] != "ENTER", "Re-entry bug"
    print("✅ Engine HOLD behavior OK")

    print("PASS:", sig)


if __name__ == "__main__":
    main()