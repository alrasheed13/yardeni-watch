# Yardeni Watch v10.2 · Druckenmiller Economic Indicator


## v10.2 · Automatic public QuickTakes + Windows daily schedule

**Built-in source reader (no subscription required):** the dashboard collects the public Ghost RSS feed at `https://www.yardeniquicktakes.com/rss/` through the **local Python server**. It displays publication titles, dated short public previews, access labels where supplied by RSS, and original links. It does **not** copy paid articles, bypass subscriptions, or automatically substitute unstructured article numbers for validated S&P 500 Forward EPS / NERI / Forward P/E. A source error is displayed as MISSING or STALE, and the last successful fetch timestamp is retained.

**Auto-refresh when the dashboard is open:** refresh is requested at first load and every 10 minutes while that browser tab stays open. Treasury/FRED and RSS are refreshed by the server in the background. ETF RS EOD history is refreshed on demand using the `Refresh ETF history` button, or via the optional daily Windows task.

**Optional daily morning scheduler:** run `INSTALL_DAILY_REFRESH_0830.bat` **only if you choose to install** a Windows Scheduled Task. It registers `YardeniWatchDaily0830` for **08:30 in your PC's local timezone** each day. It runs `RUN_DAILY_REFRESH.bat`, which updates FRED, Treasury, public QuickTakes and best-effort ETF end-of-day prices. The computer must be running and allowed to execute the task; if it is asleep/offline, the refresh may not run on time. Task status is visible in Windows Task Scheduler; its output is appended to `daily_refresh.log`. To remove it, open Task Scheduler and delete `YardeniWatchDaily0830`. This is not a ChatGPT hosted automation and does not deliver notifications.

**Python 3.15 error fix:** the startup file no longer invokes `pip`. No pandas, yfinance, tzdata or compiler is required just to open the dashboard. It tries the system IANA time-zone database first, then a tested US Eastern daylight-saving fallback. Automatic ETF data uses unofficial Yahoo chart JSON through the local backend (best effort, potential restrictions), with optional yfinance as a fallback. If you do want optional packages, run `INSTALL_OPTIONAL_PRICE_FEED.bat`, which selects a compatible pandas wheel for Python 3.15 and refuses to compile pandas from source.

**Validation:** 17 offline Python unit tests passed, Node syntax-check passed for dashboard and chart JavaScript, and local HTTP GET endpoints returned expected statuses. A headless Chromium navigation to localhost was blocked by the container's security layer, so a browser rendering smoke test could not be independently completed here. Network fetching from your Windows machine, Windows Scheduled Task registration, and actual `pandas`/`yfinance` installation on Python 3.15 were not exercised in this environment. Your Dashboard will expose an error rather than fabricate data if they fail.

**First launch (Windows):** unzip the v10.2 ZIP into a **new empty folder**, do not merge with v10. To start, double-click `START_LIVE_DASHBOARD.bat` from within `Yardeni_Watch_v10_2`. When running, visit `http://127.0.0.1:8765/health` and confirm `v10.2 · local-only` (port may advance to 8766–8769). Check QuickTakes, Macro, and Druckenmiller panels independently for fresh/stale source timestamps. Do not open `dashboard.html` in ChatGPT Preview.

---

## v10.2 إصلاح Windows / Python 3.15 (19 نوفمبر 2026)

**الإصدار v10 القديم يحتوي خطأين موثقين في تشغيل Python 3.15:** تثبيت `pandas<3` يؤدي لمحاولة بناء pandas من المصدر، و`ZoneInfo("America/New_York")` قد يفشل على Windows دون `tzdata`.

في **v10.2**:
- يبدأ السيرفر باستخدام مكتبات Python القياسية فقط، ولا يحاول تثبيت أي حزم تلقائيًا عند التشغيل.
- ساعة نيويورك تستخدم بيانات `ZoneInfo` إذا كانت موجودة، وإلا تعتمد قواعد التوقيت الصيفي الأمريكية الحالية (من 2007 فصاعدًا). تم اختبار انتقالَي مارس ونوفمبر 2026. لتطبيقات التواريخ التاريخية أو إذا تغير القانون الأمريكي، ثبّت `tzdata`.
- محاولة تنزيل الأسعار تبدأ من **Yahoo Finance chart JSON** دون اعتماديات إضافية. هذه واجهة غير رسمية وقد ترفض الطلب أو تتأخر؛ تُعرض أخطاء المصدر ولا تُستبدل بأرقام وهمية. إذا فشلت، يُستخدم `yfinance` كخيار بديل عند تثبيته. إذا فشل الاثنان، استخدم CSV.
- ملف `requirements.txt` الجديد يختار `pandas>=3.1.1` على Python 3.15، ويشترط حزم pandas/NumPy الجاهزة فقط عند تشغيل المثبّت الاختياري، فلا تبدأ عملية بناء pandas من المصدر.
- تظل بيانات Yardeni القديمة مؤرخة و**STALE**، ولا يتم احتساب درجة 0–100 إذا كانت المدخلات غير محدثة.

**خطوة واحدة للتشغيل:** افتح مجلد `Yardeni_Watch_v10_1` ثم شغّل `START_LIVE_DASHBOARD.bat`. لا تشغّل ملف v10 القديم. إذا رغبت في زيادة فرص جلب الأسعار، شغّل `INSTALL_OPTIONAL_PRICE_FEED.bat` مرة واحدة ثم أعد تشغيل اللوحة. التثبيت الاختياري ليس مطلوبًا لفتح اللوحة، وCSV يعمل دونه.

**تحقق:** افتح `http://127.0.0.1:8765/health` بعد تشغيل السيرفر. يجب أن يظهر `v10.2 · local-only` (وقد يتغير رقم المنفذ إلى 8766–8769).

## تشغيل Windows

1. فك ضغط ZIP في **مجلد جديد**، مستقل عن v8/v9. لا تنسخ ملفات `dashboard_cache.json` من الإصدارات القديمة.
2. ثبّت **Python 3.11 أو أحدث** إذا لم يكن موجودًا على جهازك، مع تفعيل إضافة Python إلى PATH.
3. انقر مرتين على `START_LIVE_DASHBOARD.bat`.
4. ستُفتح لوحة المعلومات على `http://127.0.0.1:8765/` أو منفذ 8766–8769 إذا كان الأول مشغولًا.
5. في قسم **Druckenmiller Economic Indicator** اضغط **Refresh ETF history**. يجري تنزيل أسعار إغلاق يومية معدلة (عند توفرها) من مصدر بيانات تاريخية مجاني غير رسمي، مع yfinance كبديل اختياري. يحدث التحميل تلقائيًا عند الافتتاح الأول إذا لم يوجد ملف أسعار محفوظ. ليس هذا بثًا لحظيًا للأسعار.
6. إذا تعطل مصدر الأسعار أو قيّد الوصول، استخدم **Import dated CSV** بالصيغة الموضحة أدناه. اللوحة لن تضع بيانات افتراضية بدل الأسعار المفقودة.
7. انقر `Update now` لتحديث بيانات Treasury وFRED/ICE عندما تكون الاتصالات متاحة. بيانات Yardeni وBreadth تتطلب مراجعة دورية ولا يدّعي النظام وجود API موثوق لها.

> لا تفتح `dashboard.html` مباشرة، ولا داخل ChatGPT Preview. تستدعي صفحة المتصفح خادمًا محليًا فقط، وهو المسؤول عن الاتصالات بمصادر البيانات العامة. لا تستخدم TradingView widgets.

## What was added

- **XHB/SPY, XRT/SPY, IYT/SPY** raw daily close ratios, each with a configurable EMA, default 21 daily bars.
- Raw ratio cards plus one normalized-to-100 relative performance comparison plot.
- Selectable `SPY`, `QQQ`, or `IWM` benchmark where source history includes the requested ETF.
- Configurable EMA length (1–100) and chart window (3 months, 6 months, 1 year, all).
- Independent state labels: `Leading`, `Weakening`, `Improving`, `Mixed`, and `STALE`.
- `Weakening` requires three ratios consecutively below their EMA **and** the EMA declining over the last five sessions. `Leading` is the reverse. These are *research choices*, not Druckenmiller's official rules.
- **Divergence watch**: benchmark within 2% of its 60-session closing high while 2+ sector RS series are weakening. Another warning shows 3/3 weakening. This is not a statistically validated market-timing signal.
- Missing, stale and inconsistent prices do not generate a current signal. Date gaps are aligned by **intersection**, not silently forward-filled.
- The Druckenmiller panel is **not added to the Yardeni 0–100 score** before a historical backtest demonstrates useful incremental information.

## Data quality, pricing, and alerts

The ETF updater first attempts **Yahoo Finance's unofficial historical adjusted close chart JSON** with Python standard libraries; the open-source `yfinance` library is an optional fallback. Prices are auto-adjusted for dividends/splits. This third-party historical feed is unofficial, may be delayed, rate-limited, or blocked, and is intended for personal research. The application also accepts an existing user-provided CSV export from a licensed data source. CSV data are tagged as `User CSV import · unverified` unless independently reviewed.

The original v9 market Score is **experimental** and is not an official Yardeni Research score. Our source review found that its implemented point formula does not implement the separately discussed 40/30/30 conceptual weights. v10 preserves the v9 formula for comparison but prevents a new numerical Score when critical dated inputs are missing/stale. `— / Unrated` is intentional, not a software error.

Historical Yardeni values are supplied as **dated, stale examples**, not as the current market reading. `data/yardeni_metrics.json` contains September 2026 examples; its `forward_eps_target` is specifically separate from `forward_eps`. The source values MUST be reviewed/updated against fresh S&P 500 Yardeni figures before the market score is enabled. `data/breadth_metrics.json` contains a November 17 example. Use actual source dates, do not change `asof` to today without genuine new observations.

Danger Combination flags `UNKNOWN` where required comparisons are missing. A large HY spread level is not, by itself, evidence of recent *widening*. For monitoring, material HY widening is defined here as at least **+25 basis points across 10 recorded trading observations**; verify and backtest this threshold before treating it as a calibrated warning. NERI "material weakening" requires an earlier comparable NERI value and a decline of at least 2 percentage points, or the latest value turning negative. These are explicit research heuristics.

**Important:** A rising XHB/SPY ratio indicates outperformance, not a directly observed inflow of institutional capital. XHB contains building suppliers and improvement retailers as well as homebuilders; XRT is a modified equal-weight retail fund; IYT includes airlines, trucking, and rail companies. Do not interpret their relative prices as direct measures of mortgage volume, real retail sales or freight tonnage.

## CSV file format

Export or prepare aligned **completed daily closing** ETF prices. Header fields must be:

```csv
date,SPY,XHB,XRT,IYT,QQQ,IWM
2026-01-02,....
```

- Date format `YYYY-MM-DD`, **ascending and unique**.
- Positive USD closing prices for `SPY`, `XHB`, `XRT`, `IYT` on every row.
- `QQQ` and `IWM` are optional if you only use SPY as the baseline.
- At least 63 rows for EMA21; to support EMA100 supply at least 300 completed trading sessions.
- Prices must have the same adjustment convention across all symbols. Do not mix Yahoo adjusted closes with unadjusted closes from another source.
- Missing dates are **not** filled forward; supply a consistently aligned series.
- **No fictional example prices have been included in this ZIP.** The template has a header only.

## Files

| File | Purpose |
|---|---|
| `START_LIVE_DASHBOARD.bat` | Launches on Windows without package installation |
| `server.py` | Local HTTP server (127.0.0.1 only), U.S. Treasury / FRED / ETF data integration |
| `rs_engine.py`, `eastern_clock.py` | Tested ratios, EMA, and Windows-safe Eastern market clock |
| `history_feed.py` | Optional dependency-free unofficial adjusted-close retrieval |
| `INSTALL_OPTIONAL_PRICE_FEED.bat` | Optional yfinance/pandas wheel-based installer for Python 3.15 |
| `dashboard.html` | Yardeni v9-style dashboard, data-integrity guard, and new section |
| `rs_module.js`, `rs.css` | Interactive module, source badges and charting; no external JS / TradingView |
| `data/yardeni_metrics.json` | Historic manually reviewed Yardeni examples, STALE by design |
| `data/breadth_metrics.json` | Historical breadth sample, dated and unverified |
| `rs_prices_template.csv` | Empty CSV header for importing own daily data |
| `tests/test_rs_engine.py` | Unit tests using synthetic data strictly for test execution |

## Testing

```shell
python -m unittest discover -s tests -v
```

Seventeen unit tests passed on Python 3.13.5, covering calculations, date alignment, complete-session guard and US daylight-saving fallbacks. Local HTTP/CSV import was also inspected. Browser chart rendering and Arabic/English toggling were tested using **explicitly synthetic fixture data**, not published market observations. **Live Yahoo/FRED/Treasury downloads, PyPI package installation on Python 3.15, and Windows installation could not be independently exercised in this runtime**; their status must be confirmed on your PC. The code reports failures and will not label them fresh. Public RSS parsing and access labeling were tested with a synthetic XML fixture.

## Primary references

- [StockCharts: Price Relative calculation](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/price-relative-relative-strength)
- [Stanley Druckenmiller 2022 Sohn interview transcript](https://ceointerviews.ai/interview/b2X7DWsDV86M3iwz0I1ebtd2F7Io0g%3D%3D/)
- [State Street SPDR XHB](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-homebuilders-etf-xhb)
- [State Street SPDR XRT](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-retail-etf-xrt)
- [iShares IYT fund fact sheet](https://www.blackrock.com/us/individual/literature/fact-sheet/iyt-ishares-u-s-transportation-etf-fund-fact-sheet-en-us.pdf)
- [U.S. Treasury official XML feed documentation](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed)
- [FRED CSV data downloads](https://fred.stlouisfed.org/help/data/downloading/using-the-download-data-link/)
- [yfinance history documentation](https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html)
