import html
from typing import Dict, Any
from services.gemini_analyzer import AnalysisBatchResult

class TelegramFormatter:
    @staticmethod
    def format_briefing(
        session_title: str, 
        prices: Dict[str, Dict[str, Any]], 
        analysis: AnalysisBatchResult
    ) -> str:
        
        def fmt_trend_icon(direction_str: str) -> str:
            d = direction_str.upper() if direction_str else "SIDEWAYS"
            if "UP" in d or "BULL" in d:
                return "🟢 Up"
            elif "DOWN" in d or "BEAR" in d:
                return "🔴 Down"
            return "⚪ Sideways"

        ticker = html.escape(getattr(analysis, 'asset_ticker', 'FCPO Continuous Futures'))
        tf_focus = html.escape(getattr(analysis, 'timeframe_focus', 'Intra-day / Swing'))
        bias = html.escape(getattr(analysis, 'futures_bias', '⚠️ VOLATILITY WATCH'))
        score = getattr(analysis, 'confluence_score', 5)
        conf_exp = html.escape(getattr(analysis, 'confluence_explanation', 'Neutral market alignment.'))
        mood = html.escape(getattr(analysis, 'market_mood', '⛽ ENERGY-DRIVEN'))
        mood_sum = html.escape(getattr(analysis, 'market_mood_summary', 'Market monitoring broader energy moves.'))

        msg = f"🚨 <b>[{ticker}] FUTURES FLASH</b>\n"
        msg += f"⏱️ <b>Timeframe Focus:</b> {tf_focus}\n\n"

        msg += f"🎯 <b>FUTURES BIAS:</b> {bias}\n"
        msg += f"📊 <b>CONFLUENCE SCORE:</b> [{score}/10] — {conf_exp}\n"
        msg += f"🎭 <b>MARKET MOOD:</b> [{mood}] — {mood_sum}\n\n"

        # Multi-Timeframe Compass
        trends = analysis.trends
        msg += "⏳ <b>MULTI-TIMEFRAME TRENDS (The Multi-Timeframe Compass)</b>\n"
        msg += f"• <b>Monthly (Big Trend):</b> [{fmt_trend_icon(trends.monthly.direction)}] ➔ {html.escape(trends.monthly.summary)}\n"
        msg += f"• <b>Weekly (Mid Trend):</b> [{fmt_trend_icon(trends.weekly.direction)}] ➔ {html.escape(trends.weekly.summary)}\n"
        msg += f"• <b>Daily (Current Trend):</b> [{fmt_trend_icon(trends.daily.direction)}] ➔ {html.escape(trends.daily.summary)}\n\n"

        # FCPO & Local Drivers
        msg += "🌴 <b>FCPO & LOCAL DRIVERS (MPOB & Home Front)</b>\n"
        if analysis.local_drivers:
            for d in analysis.local_drivers[:3]:
                msg += f"• [{html.escape(d.topic)}]: {html.escape(d.fact)} ➔ {html.escape(d.impact)}\n"
        else:
            msg += "• [Local Supply]: No new local regulatory updates ➔ Market maintaining balance.\n"
        msg += "\n"

        # Global Veg-Oil & Macro Drivers
        msg += "🌐 <b>GLOBAL VEG-OIL & MACRO DRIVERS (The Big Picture)</b>\n"
        if analysis.global_drivers:
            for g in analysis.global_drivers[:3]:
                msg += f"• [{html.escape(g.topic)}]: {html.escape(g.fact)} ➔ {html.escape(g.impact)}\n"
        else:
            msg += "• [Global Oils]: Soyoil and Crude markets steady ➔ External price drag is neutral.\n"
        msg += "\n"

        # Derivatives & Leverage Heat
        msg += "⚡ <b>DERIVATIVES & LEVERAGE HEAT (The Engine Heat)</b>\n"
        if analysis.derivatives_heat:
            for dh in analysis.derivatives_heat[:2]:
                msg += f"• [{html.escape(dh.topic)}]: {html.escape(dh.fact)} ➔ {html.escape(dh.impact)}\n"
        else:
            msg += "• [Open Interest]: Positions holding steady ➔ Low risk of sudden leverage pop.\n"
        msg += "\n"

        # Trader Takeaway & Risk
        key_lvl = html.escape(getattr(analysis, 'key_level_to_watch', 'RM 4,350 benchmark level.'))
        trap = html.escape(getattr(analysis, 'biggest_trap', 'Trading low volume chop without a breakout.'))

        msg += "💡 <b>TRADER TAKEAWAY & RISK (The Game Plan)</b>\n"
        msg += f"• <b>Key Level to Watch:</b> {key_lvl}\n"
        msg += f"• <b>Biggest Trap Right Now:</b> {trap}"

        return msg