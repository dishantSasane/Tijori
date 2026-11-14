# 00 — How the whole system works

## What this is
Think of a small company with departments. You are the owner. The departments watch markets, look for setups, check safety, and tell you what they found. Nothing real happens with your money unless you allow it.

## The daily loop

1. **Watch (Eyes):** collect prices and news for each market while it is open.
2. **Measure (Calculator):** turn raw prices into numbers such as "is the price rising?" (indicators), then ask each strategy "does your rule match right now?"
3. **Context (Brain, optional):** a cheap AI reads a short summary and may say "support", "neutral", or "veto".
4. **Check (Hands):** the **risk engine** asks "is this safe for the whole portfolio?" It can say no to anything.
5. **Act and tell you (Hands + Voice):** paper trade, ask you to approve, or (later) trade automatically, then send you a message.

## What an alert looks like
"BUY HDFC Bank. Why: broke the 20-day high with strong volume. Entry 1650, target 1683, stop-loss 1634. [Approve] [Paper test] [Reject]". The numbers are examples.

- **Entry:** where to buy. **Target:** where to take profit. **Stop-loss:** where to sell if wrong, so the loss stays small and planned.

## Modes
- **Paper:** fake money, real prices. Always where a strategy starts.
- **Approval:** real money, but only after you tap Approve.
- **Auto:** the system trades within strict limits. Only after a long good record.

## Two tiers so we can cover thousands of stocks
- **Tier A:** the top ~100 stocks, watched live all day.
- **Tier B:** every stock, checked once a day from the exchange's end-of-day file. The best-looking ones are promoted to live watch.

## Why we do not trust a backtest blindly
A backtest replays old data. It looks better than reality because of costs, slippage, overfitting and other traps. So we test on data the strategy never saw, then paper trade for weeks, then go live with tiny money. See lessons 02 and 03.

## Check yourself
1. What can the risk engine do that the AI Brain cannot?
2. What is the difference between Paper and Approval mode?
3. Why do we keep candles but throw away raw ticks?

## Words
- **Candle:** a summary of a time period: open, high, low, close, volume.
- **Indicator:** a number computed from prices (for example RSI).
- **Sleeve:** one market's budget and rules.
- **Slippage:** getting a slightly worse price than shown.
