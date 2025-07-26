#!/usr/bin/env python3
"""
Extract all headings from processed JSON files
"""

import json
from pathlib import Path

def extract_all_headings():
    """Extract and display all headings from JSON files."""
    output_dir = Path('output')
    all_headings = {'H1': [], 'H2': [], 'H3': []}
    
    print("=== CURRENT HEADING EXTRACTION RESULTS ===\n")
    
    for json_file in sorted(output_dir.glob('*.json')):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📄 FILE: {json_file.stem}")
            print(f"📖 TITLE: {data.get('title', 'N/A')}")
            print("=" * 60)
            
            headings_found = {'H1': 0, 'H2': 0, 'H3': 0}
            
            for item in data.get('outline', []):
                level = item.get('level')
                text = item.get('text', '')
                page = item.get('page', 0)
                
                if level in ['H1', 'H2', 'H3']:
                    headings_found[level] += 1
                    all_headings[level].append({
                        'file': json_file.stem,
                        'text': text,
                        'page': page
                    })
                    print(f"{level}: {text} (Page {page})")
            
            print(f"Summary: H1={headings_found['H1']}, H2={headings_found['H2']}, H3={headings_found['H3']}")
            print("-" * 60)
            print()
            
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
    
    print("\n=== OVERALL SUMMARY ===")
    print(f"Total H1 headings: {len(all_headings['H1'])}")
    print(f"Total H2 headings: {len(all_headings['H2'])}")
    print(f"Total H3 headings: {len(all_headings['H3'])}")
    print(f"Total headings: {sum(len(headings) for headings in all_headings.values())}")
    
    return all_headings

if __name__ == "__main__":
    extract_all_headings()
