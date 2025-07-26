#!/usr/bin/env python3
"""
Test improved heading detection
"""

from main import PDFOutlineExtractor
import json

def test_improved_detection():
    extractor = PDFOutlineExtractor()
    
    # Test on plant_leaf.pdf specifically
    print("=== TESTING IMPROVED DETECTION ===")
    result = extractor.extract_outline('input/plant_leaf.pdf')
    
    print(f'Title: {result["title"]}')
    print('\nHeadings found:')
    for item in result['outline']:
        print(f'{item["level"]}: {item["text"]} (Page {item["page"]})')
    
    # Save the improved result
    with open('output/plant_leaf_improved.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f'\nTotal headings: {len(result["outline"])}')
    
    # Count by level
    h1_count = sum(1 for item in result['outline'] if item['level'] == 'H1')
    h2_count = sum(1 for item in result['outline'] if item['level'] == 'H2')
    h3_count = sum(1 for item in result['outline'] if item['level'] == 'H3')
    
    print(f'H1: {h1_count}, H2: {h2_count}, H3: {h3_count}')

if __name__ == "__main__":
    test_improved_detection()
