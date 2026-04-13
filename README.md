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

## 📡 Data Source & Limitations

- **Primary Source**: [PePy.tech](https://pepy.tech/) API.
- **Fallback Source**: [PyPIStats.org](https://pypistats.org/) API (used if PePy is unavailable).
- **Data Range**: APIs provide statistics for the last **180 days**. However, `pptrend` stores data locally, allowing you to build a historical record that extends far beyond 180 days by running the tool periodically.
- **Data Continuity**: If a package hasn't been updated in the database for more than 180 days, its historical data is considered "disconnected" and can no longer be extended.
- **Accuracy**: Download counts are aggregated from PyPI statistics. Note that these figures may include automated systems (like CI/CD pipelines) and might not represent unique human users.

## 🚀 Installation

First, ensure you have [uv](https://github.com/astral-sh/uv) installed. If not, you can install it quickly:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Option 1: Using uvx (Quickest)
Run `pptrend` directly without installing it permanently:
```bash
uvx pptrend requests
```

### Option 2: Using uv tool install
Install `pptrend` permanently for faster subsequent runs:
```bash
uv tool install pptrend
pptrend requests
```

### Option 3: Using pipx
`pipx` uses your system's Python installation to run the tool in an isolated environment.
```bash
pipx install pptrend
pptrend requests
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

**Clean disconnected data:**
If a package hasn't been tracked for over 180 days, its history can no longer be extended. Use this command to remove such stale records:
```bash
pptrend --clean <package_name>
```

## 📊 Example Output

```text
requests - Week view (180 days of data)
======================================================================
10-13 │                                             │   180.4M
10-20 │██████████████████████████████████████       │   306.2M
...
04-06 │█████████████████████████████████████████████│   326.7M
======================================================================
Total records: 180 | Periods shown: 26 weeks
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
