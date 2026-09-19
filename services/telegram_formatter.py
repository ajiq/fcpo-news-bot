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
        
        def format_bias_tag(bias_str: str) -> str:
            b = bias_str.upper() if bias_str else "VOLATILITY WATCH"
            if "BULL" in b:
                return "🟢 BULLISH"
            elif "BEAR" in b:
                return "🔴 BEARISH"
            return "⚠️ VOLATILITY WATCH"

        ticker = html.escape(getattr(analysis, 'asset_ticker', 'FCPO Continuous Futures'))
        timeframe = html.escape(getattr(analysis, 'timeframe', 'Intra-day / Swing'))
        futures_bias = format_bias_tag(getattr(analysis, 'futures_bias', 'VOLATILITY WATCH'))
        
        biases = analysis.biases
        monthly_bias = format_bias_tag(getattr(biases, 'monthly', 'NEUTRAL'))
        weekly_bias = format_bias_tag(getattr(biases, 'weekly', 'NEUTRAL'))
        daily_bias = format_bias_tag(getattr(biases, 'daily', 'NEUTRAL'))
        
        score = getattr(analysis, 'confluence_score', 5)
        confluence_explanation = html.escape(getattr(analysis, 'confluence_explanation', 'Neutral market alignment.'))

        msg = f"🚨 <b>[{ticker}] FUTURES FLASH</b>\n"
        msg += f"⏱️ <b>Timeframe:</b> {timeframe}\n\n"
        
        msg += f"🎯 <b>FUTURES BIAS:</b> {futures_bias}\n"
        msg += f"<b>MONTHLY:</b> {monthly_bias}\n"
        msg += f"<b>WEEKLY:</b> {weekly_bias}\n"
        msg += f"<b>DAILY :</b> {daily_bias}\n"
        msg += f"📊 <b>CONFLUENCE SCORE:</b> [{score}/10] — {confluence_explanation}\n\n"

        # Global Macro & Geopolitical Drivers
        msg += "🌐 <b>MACRO & GEOPOLITICAL DRIVERS</b>\n"
        if analysis.macro_drivers:
            for m in analysis.macro_drivers[:2]:
                msg += f"• [{html.escape(m.event)}]: {html.escape(m.fact)} ➔ {html.escape(m.impact)}\n"
        if analysis.geopolitical_drivers:
            for g in analysis.geopolitical_drivers[:2]:
                msg += f"• [{html.escape(g.policy)}]: {html.escape(g.fact)} ➔ {html.escape(g.reaction)}\n"
        msg += "\n"

        # Micro & Derivatives Drivers
        msg += "⚡ <b>MICRO & DERIVATIVES DRIVERS</b>\n"
        if analysis.micro_drivers:
            for mic in analysis.micro_drivers[:2]:
                msg += f"• [{html.escape(mic.catalyst)}]: {html.escape(mic.fact)} ➔ {html.escape(mic.price_impact)}\n"
                msg += f"• [{html.escape(mic.metric)}]: {html.escape(mic.squeeze_risk)}\n"
        msg += "\n"

        # Trader Takeaway & Risk
        trigger = html.escape(getattr(analysis, 'key_trigger_level', 'Monitor RM 4,350 key benchmark level.'))
        risk = html.escape(getattr(analysis, 'execution_risk', 'Beware of low volume chop and fakeouts near key levels.'))

        msg += "💡 <b>TRADER TAKEAWAY & RISK</b>\n"
        msg += f"• <b>Key Trigger Level:</b> {trigger}\n"
        msg += f"• <b>Execution Risk:</b> {risk}"

        return msg