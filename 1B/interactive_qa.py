#!/usr/bin/env python3
"""
Automated Document Analysis using Unified Model with Config Input
"""

from unified_qa_model import UnifiedDocumentQAModel
from pathlib import Path
import json
from datetime import datetime

def main():
    """Process documents based on config.json and generate output."""
    print("🎭 UNIFIED DOCUMENT Q&A SYSTEM")
    print("="*60)
    
    # Read configuration from input/config.json
    config_path = Path("input/config.json")
    if not config_path.exists():
        print("❌ Config file not found at input/config.json")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Extract configuration
    persona = config["persona"]["role"]
    job_to_be_done = config["job_to_be_done"]["task"]
    document_filenames = [doc["filename"] for doc in config["documents"]]
    
    print(f"📋 Persona: {persona}")
    print(f"📋 Job: {job_to_be_done}")
    print(f"📋 Documents: {len(document_filenames)} files")
    
    # Initialize unified model and load documents
    qa_model = UnifiedDocumentQAModel()
    input_dir = Path("input")
    model_path = Path("models/travel_qa_model.pkl")
    
    # Create models directory if it doesn't exist
    model_path.parent.mkdir(exist_ok=True)
    
    print("📂 Loading and processing documents...")
    success = qa_model.load_and_process_documents(str(input_dir), str(model_path))
    
    if not success:
        print("❌ No documents found in input folder or processing failed.")
        return
    
    # Get processing stats from the model metrics
    print(f"✅ Processed {qa_model.metrics['documents_processed']} documents with {qa_model.metrics['sections_extracted']} sections.")
    print(f"⏱️  Processing completed in {qa_model.metrics['total_processing_time']:.2f} seconds")
    
    print("🔍 Analyzing documents for persona-driven extraction...")
    
    # Use job_to_be_done as the question for document analysis
    result = qa_model.answer_question(persona, job_to_be_done, job_to_be_done)
    
    # Display results
    print(f"\n🎯 Analysis completed successfully!")
    print(f"⏱️  Response time: {result['processing_time']:.3f} seconds")
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create formatted output matching the required structure
    formatted_output = {
        "metadata": {
            "input_documents": document_filenames,
            "persona": persona,
            "job_to_be_done": job_to_be_done,
            "processing_timestamp": datetime.now().isoformat()
        },
        "extracted_sections": result["extracted_sections"],
        "subsection_analysis": result["subsection_analysis"]
    }
    
    # Generate output filename with timestamp
    timestamp_safe = formatted_output["metadata"]["processing_timestamp"].replace(':', '-').replace('.', '-')
    output_file = output_dir / f"analysis_result_{timestamp_safe}.json"
    
    # Save output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(formatted_output, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Results saved to: {output_file}")
    print(f"📊 Extracted {len(formatted_output['extracted_sections'])} sections")
    print(f"📝 Generated {len(formatted_output['subsection_analysis'])} refined analyses")

if __name__ == "__main__":
    main()
