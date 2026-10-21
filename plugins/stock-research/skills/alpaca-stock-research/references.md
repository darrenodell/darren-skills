# Alpaca connection and provenance

The local Wheel implementation was inspected read-only at `/Users/mac/Projects/Wheel/wheel/shared/alpaca.py` and `wheel/shared/config.py`. It uses `ALPACA_KEY` and `ALPACA_SECRET`, headers `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`, `https://data.alpaca.markets`, `GET /v2/stocks/{symbol}/bars`, `timeframe=1Day`, `adjustment=all`, `feed=iex`, and `limit=10000`. Its calendar/trading host defaults to `https://paper-api.alpaca.markets`. This plugin does not import or modify Wheel, run its server, scanner or executor, or inherit its scan gates. Wheel need not be installed on another user's computer.

The new helper independently implements that read-only market-data pattern, follows pagination, checks US trading sessions, and adds `GET /v2/stocks/{symbol}/snapshot` plus `GET /v2/calendar`. The calendar call uses a paper/live API host but never reads accounts or submits orders. Requests are allowlisted GETs to official Alpaca hosts; redirects and custom credential destinations are rejected. Use matching paper or live credentials for the configured calendar host. Credentials are consumed from environment and never included in saved outputs. Do not share Darren's keys with another user.

- [Historical stock bars](https://docs.alpaca.markets/us/reference/stockbars): pagination, adjustments, feed and date parameters. The helper calls the equivalent single-symbol `/v2/stocks/{symbol}/bars` endpoint used by Wheel.
- [Single-stock snapshot](https://docs.alpaca.markets/us/reference/stocksnapshotsingle): latest trade and quote, minute/daily/previous bars. The helper uses only trade/quote and separately validates historical bars.
- [US market calendar](https://docs.alpaca.markets/us/reference/legacycalendar): trading dates, opening and closing times, including early closes.
- [Market data FAQ](https://docs.alpaca.markets/us/v1.1/docs/market-data-faq): IEX is one venue, SIP is consolidated, and entitlements differ.

Only `iex` and `sip` are supported in this initial plugin. Unsupported SIP access fails instead of changing the feed. Daily history uses all adjustments (splits, dividends and spin-offs according to Alpaca), which can revise historical values. Save the actual JSON. Returns are adjusted-price observations rather than a complete investment-return calculation. The 250-session calendar test can reject new listings, halted or thinly traded symbols, or incomplete IEX coverage; do not pad data or silently switch feeds.

Python 3.10+ is required. The helper and renderer use the standard library. On Windows or any machine without IANA timezone data, install `tzdata` into the selected Python environment. Credentials from a GUI-only launch may differ from a login shell; report missing variables without showing their values.
