<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# PDF Outline Extractor - Adobe Hackathon

This project extracts structured outlines from PDF files for the Adobe "Connecting the Dots" hackathon.

## Project Context
- **Constraint**: Must work offline, no API calls allowed
- **Target**: Extract title and headings (H1, H2, H3) with page numbers
- **Performance**: <10 seconds per 50-page PDF
- **Architecture**: CPU-only, amd64 compatible

## Code Generation Guidelines
When generating code for this project:

1. **Use only offline libraries**: PyMuPDF, pdfminer.six, standard Python libraries
2. **No external API calls**: No OpenAI, Gemini, or any web services
3. **Focus on heuristics**: Font size, style, position-based heading detection
4. **Optimize for performance**: Efficient algorithms, minimal memory usage
5. **Handle edge cases**: Malformed PDFs, missing text, unusual formatting
6. **Unicode support**: Handle multi-lingual documents properly

## Key Components
- `main.py`: Main application entry point
- `PDFOutlineExtractor`: Core extraction logic class
- Docker configuration for containerized execution
- Heuristics-based heading detection (no ML models)
