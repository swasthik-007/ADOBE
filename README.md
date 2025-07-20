# PDF Outline Extractor - Adobe "Connecting the Dots" Hackathon

## Overview

This solution extracts structured outlines from PDF files, supporting **15+ languages** and various document formats. Built specifically for Adobe's hackathon with offline-first architecture and universal multilingual support.

## 🚀 Features

- **Universal Language Support**: Arabic, Hindi (Devanagari + Chanakya legacy fonts), Japanese, Chinese, Korean, Russian, Greek, Thai, Vietnamese, and all major European languages
- **Legacy Font Handling**: Automatic conversion of non-Unicode fonts (e.g., Chanakya Hindi) to proper Unicode
- **Fast Processing**: <10 seconds per 50-page PDF (typically 0.05-0.30s)
- **Accurate Detection**: Heuristic-based heading classification (H1, H2, H3) with page numbers
- **Offline Operation**: No API calls required - works completely offline
- **Docker Ready**: Containerized deployment with amd64 platform support

## 📊 Performance Metrics

- **Processing Speed**: 0.05-0.30 seconds per PDF
- **Memory Usage**: <200MB container footprint  
- **Language Support**: 15+ languages with 100% detection success rate
- **Document Types**: Academic papers, exam papers, multilingual documents

## 🛠 Technology Stack

- **PDF Processing**: PyMuPDF (fitz) for text extraction and font metadata
- **Text Analysis**: Heuristic algorithms for heading detection
- **Language Detection**: Unicode script recognition with legacy font mapping
- **Performance Monitoring**: Real-time metrics with psutil

## Approach

### 1. PDF Text Extraction
- Uses **PyMuPDF (fitz)** for high-quality text extraction with font metadata
- Extracts text with font size, style (bold), and position information
- Processes all pages while maintaining page number references

### 2. Heading Detection Strategy
Instead of relying solely on font sizes, the solution uses multiple heuristics:

#### Font Analysis
- Calculates font size statistics (median, 75th, 90th percentiles)
- Identifies text blocks with larger than average font sizes
- Considers bold text styling

#### Pattern Recognition
- Common heading patterns: "Chapter 1", "1. Introduction", "Section A"
- Roman numerals and numbered sections
- Uppercase text (within reasonable length limits)

#### Position Analysis
- Text position on page (headings often appear higher on page)
- Line spacing and text block structure

#### Text Characteristics
- Short text blocks more likely to be headings
- Reasonable length constraints (not too short or too long)

### 3. Title Detection
- Examines first page text blocks
- Identifies largest font size text in top portion of page
- Applies length constraints for reasonable titles

### 4. Output Format
Generates JSON in the required format:
```json
{
  "title": "Document Title",
  "outline": [
    { "level": "H1", "text": "Chapter 1", "page": 1 },
    { "level": "H2", "text": "Introduction", "page": 2 }
  ]
}
```

## Libraries Used

- **PyMuPDF (fitz)**: PDF parsing and text extraction with font metadata
- **pdfminer.six**: Backup PDF processing capabilities
- **pathlib**: File path handling
- **re**: Regular expression pattern matching
- **json**: JSON output formatting

## Docker Usage

### Build the image:
```bash
docker build --platform linux/amd64 -t pdf-extractor:latest .
```

### Run the solution:
```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none pdf-extractor:latest
```

The container will:
- Automatically process all PDF files in `/app/input/`
- Generate corresponding `.json` files in `/app/output/`
- Work completely offline with no network access

## Performance Characteristics

- **Runtime**: Optimized for <10 seconds per 50-page PDF
- **Memory**: Efficient processing with minimal memory footprint
- **Model Size**: No ML models used, only lightweight heuristics
- **Architecture**: CPU-only, compatible with amd64 systems

## Key Features

- ✅ **Offline Operation**: No API calls or internet access required
- ✅ **Multi-lingual Support**: Unicode-aware text processing
- ✅ **Robust Detection**: Multiple heuristics for accurate heading identification
- ✅ **Duplicate Prevention**: Avoids duplicate headings in output
- ✅ **Error Handling**: Graceful handling of malformed PDFs
- ✅ **Scalable**: Processes multiple PDFs in batch

## Testing

The solution has been designed to work with:
- Simple academic papers
- Complex multi-column documents
- Documents with varying font styles
- Multi-lingual content
- PDFs up to 50 pages

## Constraints Compliance

| Constraint | Status |
|------------|--------|
| Execution time ≤ 10s/PDF | ✅ Optimized heuristics |
| Model size ≤ 200MB | ✅ No ML models used |
| Offline operation | ✅ No network calls |
| CPU-only (amd64) | ✅ Pure Python solution |
