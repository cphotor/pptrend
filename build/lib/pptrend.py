#!/usr/bin/env -S uv run --script
"""PyPI Download History Fetcher - Zero Dependencies"""
__version__ = "0.1.0"
import json
import sqlite3
import sys
import platform
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from datetime import datetime, timedelta

def get_data_dir():
    """Get the appropriate data directory for the current OS"""
    system = platform.system()
    app_name = "pptrend"
    
    if system == "Windows":
        base = Path.home() / "AppData" / "Roaming"
    elif system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux and others
        base = Path.home() / ".local" / "share"
    
    data_dir = base / app_name
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

DB_FILE = get_data_dir() / "pptrend.db"

def get_existing_dates(package):
    """Get existing dates from database for a package"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT date FROM downloads WHERE package = ? ORDER BY date", (package,))
    dates = {row[0] for row in c.fetchall()}
    conn.close()
    return dates

def get_latest_date(package):
    """Get the latest date in database for a package"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT MAX(date) FROM downloads WHERE package = ?", (package,))
    result = c.fetchone()[0]
    conn.close()
    return result

def fetch_history(package):
    """Fetch download history from PePy or PyPIStats"""
    url = f"https://pepy.tech/api/v2/projects/{package}"
    request = Request(url, headers={"User-Agent": "dlchart/1.0"})
    try:
        with urlopen(request) as response:
            data = json.loads(response.read().decode())
    except URLError:
        # Fallback to PyPIStats
        url = f"https://pypistats.org/api/packages/{package}/overall?mirrors=false"
        with urlopen(url) as response:
            data = json.loads(response.read().decode())
            return data.get("data", [])

    if "data" not in data:
        raise Exception("Invalid response from PePy")
    return data["data"]

def save_to_db(package, history):
    """Save download history to SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS downloads
                 (date TEXT, package TEXT, downloads INTEGER,
                  PRIMARY KEY (date, package))""")
    c.executemany("INSERT OR IGNORE INTO downloads VALUES (?, ?, ?)",
                  [(item["date"], package, item["downloads"]) for item in history])
    conn.commit()
    conn.close()

def sync_data(package):
    """Sync data: check DB first, fetch only if needed"""
    print(f"Checking database for {package}...")
    
    # Check if we have recent data
    latest_date = get_latest_date(package)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if latest_date:
        latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
        days_old = (datetime.now() - latest_dt).days
        
        # If data is less than 2 days old, skip network request
        if days_old < 2:
            print(f"✓ Data is recent ({latest_date}, {days_old} day(s) old)")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM downloads WHERE package = ?", (package,))
            count = c.fetchone()[0]
            conn.close()
            print(f"✓ Total records: {count}")
            return count
    
    # Fetch new data
    print(f"Fetching latest data from API...")
    all_history = fetch_history(package)
    
    # Get existing dates to filter
    existing_dates = get_existing_dates(package)
    new_records = [item for item in all_history if item["date"] not in existing_dates]
    
    if new_records:
        print(f"Found {len(new_records)} new records, saving to database...")
        save_to_db(package, new_records)
        print(f"✓ Added {len(new_records)} new records")
    else:
        print(f"✓ Data is up to date ({len(all_history)} total records)")
    
    return len(all_history)

def aggregate_data(rows, num_days):
    """Aggregate data based on time range"""
    if not rows:
        return [], []
    
    # Determine aggregation strategy
    if num_days <= 30:
        # Daily
        dates = [r[0][5:] for r in rows]  # MM-DD
        values = [r[1] for r in rows]
        label = "day"
    elif num_days <= 210:  # ~30 weeks
        # Weekly
        weekly_data = {}
        for date_str, val in rows:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            # Get week start (Monday)
            week_start = dt - timedelta(days=dt.weekday())
            week_key = week_start.strftime("%m-%d")
            if week_key not in weekly_data:
                weekly_data[week_key] = 0
            weekly_data[week_key] += val
        
        dates = list(weekly_data.keys())
        values = list(weekly_data.values())
        label = "week"
    elif num_days <= 900:  # ~30 months
        # Monthly
        monthly_data = {}
        for date_str, val in rows:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = dt.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = 0
            monthly_data[month_key] += val
        
        dates = list(monthly_data.keys())
        values = list(monthly_data.values())
        label = "month"
    else:
        # Yearly
        yearly_data = {}
        for date_str, val in rows:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            year_key = dt.strftime("%Y")
            if year_key not in yearly_data:
                yearly_data[year_key] = 0
            yearly_data[year_key] += val
        
        dates = list(yearly_data.keys())
        values = list(yearly_data.values())
        label = "year"
    
    return dates, values, label

def show_stats(package):
    """Display download statistics with adaptive ASCII chart"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT date, downloads FROM downloads WHERE package = ? ORDER BY date", (package,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"No data for {package}")
        return
    
    # Calculate date range
    first_date = datetime.strptime(rows[0][0], "%Y-%m-%d")
    last_date = datetime.strptime(rows[-1][0], "%Y-%m-%d")
    num_days = (last_date - first_date).days + 1
    
    # Aggregate data based on range
    dates, downloads, period_label = aggregate_data(rows, num_days)
    
    print(f"\n{package} - {period_label.capitalize()} view ({num_days} days of data)")
    print("=" * 70)
    
    # Create ASCII bar chart
    max_val = max(downloads)
    min_val = min(downloads)
    chart_width = 45
    
    for date, val in zip(dates, downloads):
        # Normalize to chart width
        if max_val > min_val:
            bar_len = int((val - min_val) / (max_val - min_val) * chart_width)
        else:
            bar_len = chart_width // 2
        
        bar = '█' * bar_len
        # Format number
        if val >= 1_000_000_000:
            val_str = f"{val/1_000_000_000:.1f}B"
        elif val >= 1_000_000:
            val_str = f"{val/1_000_000:.1f}M"
        elif val >= 1_000:
            val_str = f"{val/1_000:.0f}K"
        else:
            val_str = str(val)
        
        print(f"{date} │{bar:<{chart_width}}│ {val_str:>8}")
    
    print("=" * 70)
    print(f"Total records: {len(rows)} | Periods shown: {len(dates)} {period_label}s")
    print(f"Min: {min_val:,} | Max: {max_val:,} | Avg: {sum(downloads)//len(downloads):,}")

def main():
    if len(sys.argv) < 2:
        print("Usage: pptrend <package>")
        print("       pptrend --version")
        sys.exit(1)
    
    # Check for version flag
    if sys.argv[1] in ["--version", "-v"]:
        print(f"pptrend {__version__}")
        sys.exit(0)

    package = sys.argv[1]

    try:
        # Sync data (check DB first, fetch only missing)
        total_records = sync_data(package)
        
        # Show adaptive chart
        show_stats(package)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
