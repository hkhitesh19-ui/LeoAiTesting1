from prototype.pnl_engine_v1 import on_tick, on_exit

def main():
    print("=== SMOKE TEST: PNL ENGINE V1 ===")
    print("MTM:", on_tick(entry=25000, current=25080, qty=1))
    print("EXIT:", on_exit(realized_pnl=80))

if __name__ == "__main__":
    main()
