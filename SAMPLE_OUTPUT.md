# Sample Input/Output Examples

## Example 1: Stock Sentiment Query

**Input:**
```
What's the sentiment on RELIANCE?
```

**Output:**
```
Based on recent YouTube creator analysis and NSE deal data, RELIANCE shows a predominantly
**bullish** sentiment:

1. **CA Rachana Ranade** discusses Reliance's strong Q4 results with revenue growth of 12% YoY
   and highlights Jio's improving ARPU as a key positive [Source 1] — "Reliance Q4 Results
   Analysis" @ 3:42 (https://youtube.com/watch?v=abc123)

2. **Akshat Shrivastava** recommends Reliance as a long-term portfolio pick, citing the
   new energy business as a multi-year growth driver [Source 2] — "Top 5 Stocks to Buy
   in April 2026" @ 12:15 (https://youtube.com/watch?v=def456)

3. **NSE Bulk Deal**: Morgan Stanley purchased 1.8 lakh shares of RELIANCE at ₹2,680 on
   24-Apr-2026 [Source 3]

4. **Power of Stocks** is neutral on Reliance for short-term trading, noting resistance
   at ₹2,750 level [Source 4] — "Nifty & Stock Analysis" @ 8:30

**Sentiment Summary:** 3 bullish, 0 bearish, 1 neutral from 4 sources.

⚠️ This is based on YouTube creator sentiment and NSE deal data analysis, not financial
advice. Always do your own research and consult a SEBI-registered advisor before trading.
```

---

## Example 2: FII Activity Query

**Input:**
```
What are FIIs doing?
```

**Output:**
```
Based on today's NSE Bulk & Block deal data, here's the FII/institutional activity:

**Block Deals (Large Institutional Trades):**
1. Goldman Sachs bought 3.2L shares of HDFCBANK at ₹1,650 [Source 1]
2. JP Morgan sold 1.5L shares of INFY at ₹1,420 [Source 2]

**Bulk Deals:**
3. Citigroup purchased 2.1L shares of ICICIBANK at ₹1,180 [Source 3]
4. CLSA sold 80K shares of TATAMOTORS at ₹920 [Source 4]

**YouTube Creator Insights:**
5. **Vivek Bajaj** notes FIIs have been net buyers for 3 consecutive sessions, focusing on
   banking and IT sectors [Source 5] — "FII DII Data Analysis" @ 2:15

Overall: FIIs appear to be **accumulating banking stocks** while **reducing IT exposure**.

⚠️ Not financial advice. Consult a SEBI-registered advisor.
```

---

## Example 3: Why Bullish Query

**Input:**
```
Why are people bullish on HDFC Bank?
```

**Output:**
```
Multiple YouTube creators and institutional activity suggest bullish sentiment on HDFCBANK:

**Creator Analysis:**
1. **Pranjal Kamra** (confidence: 85%): Post-merger integration is ahead of schedule, cost
   synergies of ₹3,500 Cr expected this fiscal [Source 1] @ 5:20

2. **Nitin Bhatia** (confidence: 80%): HDFC Bank's NIM improvement from 3.4% to 3.7% signals
   strong profitability ahead [Source 2] @ 14:30

3. **CA Rachana Ranade** (confidence: 75%): Loan book growth of 18% YoY makes it the
   fastest-growing large bank [Source 3] @ 7:45

**Institutional Activity:**
4. Goldman Sachs block deal purchase of 3.2L shares at ₹1,650 confirms FII confidence [Source 4]

**Key Bullish Reasons:**
- Post-merger synergies materializing faster than expected
- NIM expansion indicating pricing power
- Strong loan growth outpacing peers
- FII accumulation in recent sessions

⚠️ Not financial advice. Consult a SEBI-registered advisor.
```

---

## Example 4: Trading Recommendation

**Input:**
```
Should I buy TATA Motors?
```

**Output:**
```
Based on available creator sentiment and market data for TATAMOTORS:

**Sentiment: Mixed (Neutral to Slightly Bullish)**

1. **Booming Bulls** is bullish short-term, noting a breakout above ₹950 with target ₹1,020
   [Source 1] @ 6:30
2. **Trading Chanakya** is neutral, citing EV transition costs as near-term headwind
   [Source 2] @ 11:15
3. NSE data shows CLSA sold 80K shares — some institutional profit-taking [Source 3]

**Recommendation Context:**
- Short-term: Technically bullish if ₹950 support holds
- Long-term: EV story is strong but execution risk remains
- Institutional: Mixed signals (some buying, some selling)

⚠️ IMPORTANT DISCLAIMER: This is based on YouTube creator sentiment and NSE deal data
analysis, NOT professional financial advice. The sentiment reflects opinions of content
creators, not qualified analysts. Always:
- Do your own research (DYOR)
- Consult a SEBI-registered investment advisor
- Consider your risk tolerance and financial goals
- Never invest money you can't afford to lose
```

---

## Example 5: Feedback Loop

**Input:**
```
/feedback bad The RELIANCE sentiment was wrong, most creators are actually bearish due to telecom competition
```

**Output:**
```
✓ Feedback recorded: bad
📝 Learning from your feedback for future responses.
```

*On next session, the agent will incorporate this correction:*
```
LEARNED FROM PREVIOUS FEEDBACK:
- When asked about 'RELIANCE', user feedback: The RELIANCE sentiment was wrong, most
  creators are actually bearish due to telecom competition
```

---

## Example 6: Market Summary

**Input:**
```
/summary
```

**Output:**
```
📊 MARKET SENTIMENT SUMMARY (24 Apr 2026)

Stock Sentiment Summary:
  RELIANCE:   BULLISH  (3↑ 0↓ 1→) from 4 mentions
  HDFCBANK:   BULLISH  (4↑ 0↓ 1→) from 5 mentions
  TCS:        NEUTRAL  (1↑ 1↓ 2→) from 4 mentions
  INFY:       BEARISH  (0↑ 2↓ 1→) from 3 mentions
  TATAMOTORS: NEUTRAL  (2↑ 1↓ 2→) from 5 mentions
  NIFTY:      BULLISH  (5↑ 2↓ 1→) from 8 mentions
  BANKNIFTY:  BULLISH  (3↑ 1↓ 0→) from 4 mentions
  ADANIENT:   BEARISH  (1↑ 3↓ 1→) from 5 mentions
  SBIN:       BULLISH  (2↑ 0↓ 1→) from 3 mentions

Overall Market Mood: CAUTIOUSLY BULLISH
- Banking sector: Strong positive sentiment
- IT sector: Mixed to negative
- Auto sector: Neutral with EV optimism

Data from 100 YouTube videos (68 with transcripts) and 23 NSE bulk/block deals.

⚠️ Not financial advice.
```
