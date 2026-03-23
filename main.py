"""
╔══════════════════════════════════════════════╗
║  FILE 10: main.py                            ║
║  🚀 APPLICATION ENTRY POINT                  ║
╚══════════════════════════════════════════════╝
"""

from config import TradingConfig
from auto_trader import AutoTrader


def main():
    print("""
    ╔═══════════════════════════════════════════════╗
    ║  🇮🇳 DHAN HQ CONFLUENCE AUTO TRADER             ║
    ║  Data: DhanHQ API | Money: Virtual ₹          ║
    ║  Trade only when win rate >= 85%              ║
    ╠═══════════════════════════════════════════════╣
    ║  1. 🤖 AUTO MODE   (Full automatic)           ║
    ║  2. 🔍 MANUAL MODE (Analyze one-by-one)       ║
    ║  3. 📊 DASHBOARD   (View portfolio)           ║
    ║  4. 🔄 RESET       (Fresh start)              ║
    ║  5. ❌ EXIT                                    ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    config = TradingConfig(
        symbols=["NIFTY", "BANKNIFTY"],
        initial_capital=500000,
        min_confluence_score=85,
        max_trades_per_day=3,
        max_daily_loss=8000,
        check_interval_seconds=180,
    )
    
    bot = AutoTrader(config)
    
    choice = input("  Select (1/2/3/4/5): ").strip()
    
    if choice == "1":
        bot.start()
    
    elif choice == "2":
        while True:
            sym = input("\n  Symbol (NIFTY/BANKNIFTY) or 'q': ").strip().upper()
            if sym == 'Q':
                break
            bot.analyze_once(sym)
    
    elif choice == "3":
        bot.portfolio.dashboard()
    
    elif choice == "4":
        if input("  Sure? (y/n): ").strip().lower() == 'y':
            bot.portfolio.reset()
    
    elif choice == "5":
        print("  👋 Bye!")
    
    else:
        print("  ❌ Invalid!")


if __name__ == "__main__":
    main()
