from typing import Dict, Any
from services.gemini_analyzer import AnalysisBatchResult

class TelegramFormatter:
    @staticmethod
    def format_briefing(
        session_title: str, 
        prices: Dict[str, Dict[str, Any]], 
        analysis: AnalysisBatchResult
    ) -> str:
        
        def fmt_change(change: float, pct: float) -> str:
            icon = "🟢 +" if change >= 0 else "🔴 "
            return f"{icon}{change:.2f} ({pct:+.2f}%)"

        fcpo = prices.get("FCPO_Futures", {})
        dce = prices.get("DCE_Palm_Olein", {})
        cbot = prices.get("CBOT_Soybean_Oil", {})
        brent = prices.get("Brent_Crude", {})
        fx = prices.get("USD_MYR", {})

        bias_emoji = "🟢" if analysis.overall_bias == "BULLISH" else ("🔴" if analysis.overall_bias == "BEARISH" else "🟡")

        msg = f"<b>📊 FCPO DAILY BRIEFING | {session_title.upper()}</b>\n"
        msg += f"<i>Bias: {bias_emoji} {analysis.overall_bias}</i>\n"
        msg += "───────────────────\n\n"

        msg += "<b>📈 CORRELATED MARKETS SNAPSHOT</b>\n"
        msg += f"• 🌴 <b>FCPO 3M:</b> RM {fcpo.get('price', 0):,.0f} | {fmt_change(fcpo.get('change',0), fcpo.get('pct_change',0))}\n"
        msg += f"• 🇨🇳 <b>DCE Olein:</b> ¥ {dce.get('price', 0):,.0f} | {fmt_change(dce.get('change',0), dce.get('pct_change',0))}\n"
        msg += f"• 🇺🇸 <b>CBOT Soyoil:</b> {cbot.get('price', 0):.2f}¢ | {fmt_change(cbot.get('change',0), cbot.get('pct_change',0))}\n"
        msg += f"• 🛢️ <b>Brent Crude:</b> ${brent.get('price', 0):.2f} | {fmt_change(brent.get('change',0), brent.get('pct_change',0))}\n"
        msg += f"• 💱 <b>USD/MYR:</b> RM {fx.get('price', 0):.4f} | {fmt_change(fx.get('change',0), fx.get('pct_change',0))}\n\n"

        msg += "<b>🧠 MARKET SYNTHESIS</b>\n"
        msg += f"{analysis.market_synthesis}\n\n"

        filtered_news = [a for a in analysis.articles if a.relevance_score >= 7 and not a.is_duplicate_narrative]

        if filtered_news:
            msg += "<b>📰 KEY DRIVERS & FUNDAMENTALS</b>\n"
            for item in filtered_news[:4]:
                icon = "🟢" if item.market_bias == "BULLISH" else ("🔴" if item.market_bias == "BEARISH" else "🔹")
                msg += f"{icon} {item.key_narrative}\n"
        else:
            msg += "<b>📰 KEY DRIVERS</b>\n🔹 No fresh high-impact developments relative to prior session.\n"

        msg += "\n<i>#FCPO #PalmOil #TradingUpdate</i>"
        return msg