#!/usr/bin/env python3
"""
Fix VLAN range from [1-4094] to [2-4094] for all Internet2 nodes
"""

import os
import re
import glob

def fix_vlan_range(file_path):
    """Fix VLAN range in a single main.yaml file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Change vlan_range from [1-4094] to [2-4094]
    content = re.sub(
        r'vlan_range:\s*\[1-4094\]',
        'vlan_range: [2-4094]',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)

def main():
    print("🔧 Fixing VLAN range from [1-4094] to [2-4094]...")
    
    # Find all main.yaml files in T3_US_Internet2
    pattern = 'T3_US_Internet2/pas.*/main.yaml'
    yaml_files = glob.glob(pattern)
    
    fixed_count = 0
    for yaml_file in sorted(yaml_files):
        city = yaml_file.split('/')[1].replace('pas.', '').replace('.net.internet2.edu', '')
        
        fix_vlan_range(yaml_file)
        print(f"   ✅ Fixed {city}")
        fixed_count += 1
    
    print(f"\n📊 SUMMARY:")
    print(f"   ✅ Fixed: {fixed_count} config files")
    print(f"   🔧 VLAN range changed: [1-4094] → [2-4094]")

if __name__ == "__main__":
    main()


