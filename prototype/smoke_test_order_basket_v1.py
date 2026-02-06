"""
SMOKE TEST — ORDER BASKET BUILDER V1
"""

from prototype.order_basket_builder_v1 import build_order_basket

def main():
    print("=== SMOKE TEST: ORDER BASKET V1 ===")

    for gear in ["SAFE_FUTURE", "RATIO_SPREAD", "BULL_CALL_SPREAD"]:
        basket = build_order_basket(gear=gear, spot=25100)
        print(gear, basket)

if __name__ == "__main__":
    main()
