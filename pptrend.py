#!/usr/bin/env -S uv run --script
"""PyPI Download History Fetcher - Zero Dependencies"""
import json
import sqlite3
import sys
import platform
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from datetime import datetime, timedelta

try:
    from importlib.metadata import version as get_version
    __version__ = get_version("pptrend")
except Exception:
    # Fallback for development or if package is not installed
    __version__ = "0.1.2"

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
    """Sync data: check DB first, clean if old, then fetch only if needed"""
    print(f"Checking database for {package}...")
    
    # Check if we have recent data
    latest_date = get_latest_date(package)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if latest_date:
        latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
        days_old = (datetime.now() - latest_dt).days
        
        # If data is older than 180 days, it's disconnected. Clean it.
        if days_old > 180:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM downloads WHERE package = ?", (package,))
            conn.commit()
            conn.close()
            latest_date = None  # Reset so we fetch fresh data
        elif days_old < 2:
            # If data is less than 2 days old, skip network request
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

def clean_old_data():
    """Remove data for all packages where the latest record is older than 180 days"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get all unique packages
    c.execute("SELECT DISTINCT package FROM downloads")
    packages = [row[0] for row in c.fetchall()]
    
    if not packages:
        print("No data found in database.")
        conn.close()
        return

    cleaned_count = 0
    for package in packages:
        c.execute("SELECT MAX(date) FROM downloads WHERE package = ?", (package,))
        result = c.fetchone()[0]
        if result:
            latest_date = datetime.strptime(result, "%Y-%m-%d")
            days_since_update = (datetime.now() - latest_date).days
            
            if days_since_update > 180:
                c.execute("DELETE FROM downloads WHERE package = ?", (package,))
                deleted = c.rowcount
                cleaned_count += deleted
                print(f"  Cleaned {package}: {deleted} records (last updated {days_since_update} days ago)")
    
    conn.commit()
    conn.close()
    
    if cleaned_count > 0:
        print(f"\n✓ Successfully cleaned {cleaned_count} old/disconnected records.")
    else:
        print("\n✓ All data is up to date. No cleaning needed.")

def fill_missing_dates(rows):
    """Fill in missing dates with 0 downloads, extending to yesterday if needed"""
    if not rows:
        return rows
    
    # Convert to dict for easy lookup
    data_dict = {row[0]: row[1] for row in rows}
    
    # Get date range from data
    first_date = datetime.strptime(rows[0][0], "%Y-%m-%d")
    last_date_in_db = datetime.strptime(rows[-1][0], "%Y-%m-%d")
    
    # Extend to yesterday if the last date is more than 1 day ago
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    
    # If last date in DB is before yesterday, extend the range
    end_date = max(last_date_in_db, yesterday)
    
    # Fill in all dates in range
    filled_rows = []
    current_date = first_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        downloads = data_dict.get(date_str, 0)
        filled_rows.append((date_str, downloads))
        current_date += timedelta(days=1)
    
    return filled_rows

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
    
    # Fill in missing dates with 0 downloads
    rows = fill_missing_dates(rows)
    
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

def print_help():
    """Print help message"""
    help_text = f"""pptrend v{__version__} - PyPI Download Trend Tracker

Usage:
  pptrend <package>              Track and visualize download trends
  pptrend --clean                Remove all disconnected historical data
  pptrend --version, -V          Show version information
  pptrend --help, -H             Show this help message

Examples:
  pptrend requests               View download history for 'requests'
  pptrend flask                  View download history for 'flask'
  pptrend --clean                Clean all disconnected data automatically

Data Storage:
  Data is stored locally in your system's application data directory.
  The tool automatically aggregates data from PePy and PyPIStats APIs.

Note:
  APIs provide statistics for the last 180 days. By running pptrend
  periodically, you can build a historical record that extends far
  beyond this limit.

Star on GitHub: https://github.com/cphotor/pptrend
Report bugs:    https://github.com/cphotor/pptrend/issues/new"""
    print(help_text)

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    arg = sys.argv[1]
    
    # Check for help flag
    if arg in ["--help", "-H"]:
        print_help()
        sys.exit(0)
    
    # Check for version flag
    if arg in ["--version", "-V"]:
        print(f"pptrend {__version__}")
        sys.exit(0)

    # Check for clean flag
    if arg == "--clean":
        clean_old_data()
        sys.exit(0)

    package = arg

    try:
        # Sync data (check DB first, fetch only missing)
        total_records = sync_data(package)
        
        # Show adaptive chart
        show_stats(package)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
