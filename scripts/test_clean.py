#!/usr/bin/env python3
"""Test script to verify the --clean functionality of pptrend"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path to import pptrend logic if needed, 
# but here we'll interact directly with the DB for testing.
DB_FILE = Path.home() / "Library" / "Application Support" / "pptrend" / "pptrend.db"

def setup_test_data():
    """Insert some fake old data that should be cleaned"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create table if not exists
    c.execute("""CREATE TABLE IF NOT EXISTS downloads
                 (date TEXT, package TEXT, downloads INTEGER,
                  PRIMARY KEY (date, package))""")
    
    # 1. Insert a package with very old data (should be cleaned)
    old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
    c.execute("INSERT OR IGNORE INTO downloads VALUES (?, ?, ?)", (old_date, "test-old-pkg", 100))
    
    # 2. Insert a package with recent data (should NOT be cleaned)
    recent_date = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT OR IGNORE INTO downloads VALUES (?, ?, ?)", (recent_date, "test-new-pkg", 500))
    
    conn.commit()
    conn.close()
    print(f"✓ Test data inserted into {DB_FILE}")
    print(f"  - 'test-old-pkg': last updated 200 days ago")
    print(f"  - 'test-new-pkg': last updated today")

def check_data_exists(package):
    """Check if data for a package still exists"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM downloads WHERE package = ?", (package,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

if __name__ == "__main__":
    print("--- Pptrend Clean Functionality Test ---\n")
    
    # Step 1: Setup
    setup_test_data()
    
    # Step 2: Verify data is there
    assert check_data_exists("test-old-pkg"), "Old data missing before test!"
    assert check_data_exists("test-new-pkg"), "New data missing before test!"
    
    print("\nRunning: pptrend --clean ...")
    # We simulate the clean action by calling the module or just running the command
    import subprocess
    result = subprocess.run([sys.executable, str(Path(__file__).parent.parent / "pptrend.py"), "--clean"], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

    # Step 3: Verify results
    old_exists = check_data_exists("test-old-pkg")
    new_exists = check_data_exists("test-new-pkg")
    
    print("\n--- Verification ---")
    if not old_exists and new_exists:
        print("✅ SUCCESS: Old data was cleaned, new data was preserved.")
    else:
        print("❌ FAILURE:")
        if old_exists: print("   - Old data was NOT cleaned.")
        if not new_exists: print("   - New data was accidentally deleted.")
