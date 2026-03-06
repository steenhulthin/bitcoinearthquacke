# 🌍📉 BitCoinEarthQuacke

An unnecessarily dramatic dashboard that overlays:

- Daily earthquake counts (USGS) 🌋
- Daily Bitcoin price in USD (CoinGecko) ₿

Do earthquakes move Bitcoin?  
Does Bitcoin shake the Earth?  
Probably not. But the chart looks suspiciously convincing at 2am. 🕵️‍♂️

## 😄 What This Project Is

A Streamlit app that plots earthquakes and Bitcoin on a dual-axis chart so you can explore *casuality* (casual causality?) and enjoy beautiful, absolutely-not-peer-reviewed vibes.

## ✨ Features

- Red earthquakes, black Bitcoin line (because drama) 🔴⚫
- Configurable lookback window (default: 6 months)
- Magnitude filtering for earthquakes
- Defensive API handling and friendly error messages
- Basic tests for key data logic

## 🧰 Tech Stack

- Python
- Streamlit
- Pandas
- Plotly
- Requests

## 🚀 Quick Start

1. Clone the repo
2. Create and activate a virtual environment
3. Install dependencies
4. Run the app

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## ⚙️ Configuration

Edit constants in [`streamlit_app.py`](streamlit_app.py):

- `MONTHS_BACK` (default `6`)
- `MIN_MAGNITUDE` (default `4.5`)

Or use the UI sliders:

- `Months back`: `1` to `11`
- `Minimum earthquake magnitude`: `4.0` to `9.0`

### Magnitude Scale Note

USGS catalogs are not limited to the original Richter scale (`ML`). They commonly
use modern magnitude types such as moment magnitude (`Mw`) and other scale variants.
In this app, the minimum magnitude filter is passed directly to the USGS API and
applies to whatever magnitude type USGS reports for each event.
References:
- https://www.usgs.gov/faqs/moment-magnitude-richter-scale-what-are-different-magnitude-scales-and-why-are-there-so-many
- https://www.usgs.gov/programs/earthquake-hazards/magnitude-types

If APIs complain, reduce time range or magnitude sensitivity and try again.

## 🧪 Tests

Run unit tests:

```bash
python -m unittest discover -s tests -v
```

Test file: [`tests/test_streamlit_app.py`](tests/test_streamlit_app.py)

## 🧠 Interpretation Guide (Important)

- Correlation is not causation.
- Correlation with Bitcoin is *definitely* not causation.
- Two squiggly lines crossing is not an investment thesis.
- This app is for exploration, fun, and mild existential curiosity.

## 🛠️ Troubleshooting

- `401` from CoinGecko: you likely requested too many days for your tier.
- Empty chart: check network access and API status.
- Streamlit errors: verify dependencies in `requirements.txt`.

## 🤝 Contributing

PRs are welcome, especially if they include:

- Better jokes
- Better tests
- Better charts
- Better skepticism

## 📜 License

Licensed under the **GNU Affero General Public License v3.0 (or later)**.

See [`LICENSE`](LICENSE) for the full terms.

## 🧯 Disclaimer

Not financial advice.  
Not seismic advice.  
Not emotional advice when Bitcoin does Bitcoin things. 💀
