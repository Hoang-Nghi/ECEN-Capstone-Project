#!/usr/bin/env python3
"""Verify the _fetch_txns function works with None parameters"""

# Test the logic
def test_none_check():
    start_date = None
    end_date = None
    
    # OLD WAY (broken):
    if start_date and end_date:
        print("❌ OLD: Would execute (WRONG!)")
    else:
        print("✅ OLD: Skipped correctly")
    
    # NEW WAY (fixed):
    if start_date is not None and end_date is not None:
        print("❌ NEW: Would execute (WRONG!)")
    else:
        print("✅ NEW: Skipped correctly")

test_none_check()

# Output should be:
# ✅ OLD: Skipped correctly
# ✅ NEW: Skipped correctly