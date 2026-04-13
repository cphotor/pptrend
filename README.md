# pptrend

A zero-dependency command-line tool to track and visualize PyPI package download trends directly in your terminal.

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.8+-brightgreen)

## ✨ Features

- **Zero Dependencies**: Built entirely with Python standard libraries. No `pip install` required for dependencies.
- **Adaptive ASCII Charts**: Automatically adjusts the chart granularity (daily, weekly, monthly, or yearly) based on the data range.
- **Smart Caching**: Stores data locally to minimize API calls. Skips network requests if data is recent.
- **Cross-Platform**: Works on macOS, Linux, and Windows.
- **Offline Viewing**: View historical trends instantly from the local database without an internet connection.

## 📡 Data Source & Limitations

- **Primary Source**: [PePy.tech](https://pepy.tech/) API.
- **Fallback Source**: [PyPIStats.org](https://pypistats.org/) API (used if PePy is unavailable).
- **Data Range**: Both APIs typically provide download statistics for the **last 180 days**. 
- **Accuracy**: Data is aggregated from PyPI's public BigQuery dataset. Note that download counts may include automated systems (like CI/CD pipelines) and might not represent unique human users.

## 🚀 Installation

### Option 1: Using uv (Recommended)
```bash
uv tool install pptrend
```

### Option 2: Using pipx
```bash
pipx install pptrend
```

### Option 3: Manual Install
Download `pptrend.py` and run it directly:
```bash
./pptrend.py <package_name>
```

## 📖 Usage

Track the download history of any PyPI package:

```bash
pptrend requests
pptrend flask
pptrend numpy
```

**Check version:**
```bash
pptrend --version
```

## 📊 Example Output

```text
requests - Week view (181 days of data)
======================================================================
10-13 │                                             │   180.4M
10-20 │██████████████████████████████████████       │   306.2M
...
04-06 │█████████████████████████████████████████████│   326.7M
======================================================================
Total records: 181 | Periods shown: 26 weeks
Min: 178,740,886 | Max: 326,665,297 | Avg: 247,929,848
```

## ⚙️ Data Storage

`pptrend` stores its database in the standard application data directory for your OS:

- **macOS**: `~/Library/Application Support/pptrend/pptrend.db`
- **Linux**: `~/.local/share/pptrend/pptrend.db`
- **Windows**: `%APPDATA%\pptrend\pptrend.db`

## 🛠️ Development

To run the script from source using `uv`:

```bash
git clone https://github.com/cphotor/pptrend.git
cd pptrend
uv run pptrend.py requests
```

## 📄 License

MIT License
