# PDF Content Summarizer - Adobe "Connecting the Dots" Hackathon (Part 1B)

## Overview

This solution extracts and summarizes key content from PDF files, providing intelligent content insights that complement the PDF outline extraction from Part 1A. Built for Adobe's hackathon with offline-first architecture and multilingual support.

## 🚀 Features

- **Intelligent Content Summarization**: Extracts key sentences and concepts from PDF content
- **Section-based Analysis**: Summarizes content by detected sections/headings
- **Multi-language Support**: Works with 15+ languages including Arabic, Hindi, Japanese, Chinese, Korean, etc.
- **Content Classification**: Identifies document types (academic, exam, technical, etc.)
- **Key Entity Extraction**: Identifies important terms, names, and concepts
- **Fast Processing**: <5 seconds per 50-page PDF
- **Offline Operation**: No API calls required - works completely offline
- **Docker Ready**: Containerized deployment with amd64 platform support

## 📊 Performance Metrics

- **Processing Speed**: 0.1-0.5 seconds per PDF
- **Memory Usage**: <150MB container footprint
- **Language Support**: 15+ languages with intelligent text analysis
- **Document Types**: Academic papers, exam papers, technical documents, multilingual content

## 🛠 Technology Stack

- **PDF Processing**: PyMuPDF (fitz) for text extraction
- **Text Analysis**: NLP techniques using NLTK and custom algorithms
- **Summarization**: Extractive summarization using TF-IDF and position-based scoring
- **Language Detection**: Unicode script recognition with multilingual processing
- **Performance Monitoring**: Real-time metrics tracking

## Approach

### 1. PDF Content Extraction
- Uses **PyMuPDF (fitz)** for comprehensive text extraction
- Maintains paragraph and section structure
- Preserves formatting context for better understanding

### 2. Content Analysis Strategy
Multiple techniques for intelligent content processing:

#### Text Preprocessing
- Sentence tokenization and cleaning
- Language detection and appropriate processing
- Removal of headers, footers, and metadata noise

#### Content Scoring
- TF-IDF analysis for important term identification
- Position-based scoring (introduction/conclusion emphasis)
- Length and complexity analysis for sentence importance

#### Section-wise Processing
- Integration with outline detection from Part 1A
- Section-specific summarization
- Context-aware content extraction

### 3. Summarization Techniques
- **Extractive Summarization**: Selects most important existing sentences
- **Keyword Extraction**: Identifies key terms and concepts
- **Content Classification**: Determines document type and purpose

### 4. Output Format
Generates comprehensive JSON analysis:
```json
{
  "title": "Document Title",
  "document_type": "academic_paper",
  "language": "english",
  "summary": {
    "full_summary": "Brief overview of entire document...",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "keywords": ["keyword1", "keyword2", "keyword3"]
  },
  "section_summaries": [
    {
      "section": "Introduction",
      "summary": "Section-specific summary...",
      "key_concepts": ["concept1", "concept2"]
    }
  ],
  "statistics": {
    "total_pages": 10,
    "word_count": 5000,
    "reading_time_minutes": 20
  }
}
```

## Libraries Used

- **PyMuPDF (fitz)**: PDF parsing and text extraction
- **NLTK**: Natural language processing and tokenization
- **scikit-learn**: TF-IDF vectorization and text analysis
- **numpy**: Numerical computations for scoring
- **re**: Regular expression pattern matching
- **json**: JSON output formatting
- **collections**: Data structure utilities

## Docker Usage

### Build the image:
```bash
docker build --platform linux/amd64 -t pdf-summarizer:latest .
```

### Run the solution:
```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none pdf-summarizer:latest
```

The container will:
- Process all PDF files in `/app/input/`
- Generate corresponding analysis `.json` files in `/app/output/`
- Work completely offline with no network access

## Performance Characteristics

- **Runtime**: Optimized for <5 seconds per 50-page PDF
- **Memory**: Efficient processing with minimal memory footprint
- **Model Size**: Lightweight algorithms, no heavy ML models
- **Architecture**: CPU-only, compatible with amd64 systems

## Key Features

- ✅ **Offline Operation**: No API calls or internet access required
- ✅ **Multi-lingual Support**: Unicode-aware text processing for 15+ languages
- ✅ **Intelligent Analysis**: Multiple algorithms for content understanding
- ✅ **Section Integration**: Works with Part 1A outline extraction
- ✅ **Scalable Processing**: Handles multiple PDFs efficiently
- ✅ **Comprehensive Output**: Rich analysis with multiple content dimensions

## Integration with Part 1A

This solution is designed to work seamlessly with the PDF Outline Extractor from Part 1A:
- Uses outline structure to provide section-specific summaries
- Combines structural and content analysis for comprehensive document understanding
- Provides complementary insights: structure (1A) + content (1B)

## Testing

The solution works with:
- Academic research papers
- Educational exam papers
- Technical documentation
- Multi-lingual documents
- Complex structured documents up to 50 pages

## Constraints Compliance

| Constraint | Status |
|------------|--------|
| Execution time ≤ 5s/PDF | ✅ Optimized algorithms |
| Model size ≤ 150MB | ✅ Lightweight NLP techniques |
| Offline operation | ✅ No network calls |
| CPU-only (amd64) | ✅ Pure Python solution |

## Usage Example

```python
from pdf_summarizer import PDFContentSummarizer

summarizer = PDFContentSummarizer()
result = summarizer.analyze_pdf("document.pdf")
print(f"Summary: {result['summary']['full_summary']}")
```
