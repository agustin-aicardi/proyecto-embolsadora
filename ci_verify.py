#!/usr/bin/env python3
"""Verify InfluxDB response from CI integration test."""
import sys
import csv
import io
import math

def main():
    try:
        with open('/tmp/result.txt') as f:
            lines = f.read().strip().split('\n')
        
        # Remove HTTP status code (last line)
        csv_data = '\n'.join(lines[:-1])
        
        if not csv_data.strip():
            print("ERROR: Empty CSV data")
            return 1
        
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        
        if not rows:
            print("ERROR: No CSV rows in response")
            return 2
        
        # Extract values by tag name
        vals = {}
        for row in rows:
            tag = row.get('tag', '')
            value = row.get('_value', '')
            if tag and value:
                try:
                    vals[tag] = float(value)
                except ValueError:
                    vals[tag] = value
        
        print(f"Values found: {vals}")
        
        # Validate expected values
        errors = []
        
        if 'pack_count' not in vals:
            errors.append("pack_count not found")
        elif vals['pack_count'] != 123.0:
            errors.append(f"pack_count={vals['pack_count']}, expected 123")
        
        if 'filled_weight' not in vals:
            errors.append("filled_weight not found")
        elif not math.isclose(vals['filled_weight'], 123.456, abs_tol=1e-3):
            errors.append(f"filled_weight={vals['filled_weight']}, expected ~123.456")
        
        if errors:
            print("ERRORS:")
            for e in errors:
                print(f"  - {e}")
            return 3
        
        print("✓ All verification checks passed!")
        return 0
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 4

if __name__ == '__main__':
    sys.exit(main())
