#!/usr/bin/env python3
"""
Test script to validate PDF outline extraction locally.
"""

import sys
import json
import time
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from main import PDFOutlineExtractor

def test_extractor():
    """Test the PDF extractor with sample files."""
    start_time = time.time()
    
    extractor = PDFOutlineExtractor()
    
    input_dir = Path("input")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Process any PDF files in the input directory
    pdf_files = list(input_dir.glob("*.pdf"))
    extractor.metrics['total_files'] = len(pdf_files)
    
    if not pdf_files:
        print("No PDF files found in input/ directory")
        print("Please add some PDF files to test the extractor")
        return
    
    for pdf_file in pdf_files:
        print(f"\nProcessing: {pdf_file.name}")
        file_start = time.time()
        
        try:
            result = extractor.extract_outline(str(pdf_file))
            
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            file_time = time.time() - file_start
            print(f"Title: {result['title']}")
            print(f"Headings found: {len(result['outline'])}")
            
            for heading in result['outline'][:5]:  # Show first 5
                print(f"  {heading['level']}: {heading['text']} (Page {heading['page']})")
            
            if len(result['outline']) > 5:
                print(f"  ... and {len(result['outline']) - 5} more")
            
            print(f"Output saved to: {output_file}")
            print(f"Processing time: {file_time:.2f}s")
            
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")
            extractor.metrics['failed_files'] += 1
            extractor.metrics['errors'].append(f"{pdf_file.name}: {str(e)}")
    
    # Print summary metrics
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\n{'='*50}")
    print(f"📊 SUMMARY METRICS:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Files processed: {extractor.metrics['total_files']}")
    print(f"   Success rate: {(extractor.metrics['successful_files']/max(extractor.metrics['total_files'],1)*100):.1f}%")
    print(f"   Total headings: {extractor.metrics['headings_detected']}")
    print(f"   Average per file: {total_time/max(extractor.metrics['total_files'],1):.2f}s")
    print(f"{'='*50}")

if __name__ == "__main__":
    test_extractor()
