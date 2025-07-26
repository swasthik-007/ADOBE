# Docker Usage Guide

## Building and Running the Unified Document Q&A System

### Prerequisites
- Docker installed on your system
- PDF documents in the `input/` folder
- Configuration file `input/config.json`

### Building the Docker Image
```bash
docker build -t adobe-document-qa .
```

### Running the Container

#### Method 1: With Volume Mounting (Recommended)
```bash
docker run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output adobe-document-qa
```

#### Method 2: Copy Files and Extract Results
```bash
# Run container
docker run --name qa-container adobe-document-qa

# Copy results out
docker cp qa-container:/app/output ./output
docker rm qa-container
```

### Input Structure
Your `input/` folder should contain:
```
input/
├── config.json          # Configuration file
├── document1.pdf        # PDF files to analyze
├── document2.pdf
└── ...
```

### Output Structure
Results will be saved to:
```
output/
└── analysis_result_TIMESTAMP.json
```

### Example config.json
```json
{
    "challenge_info": {
        "challenge_id": "round_1b_002",
        "test_case_name": "travel_planner",
        "description": "France Travel"
    },
    "documents": [
        {
            "filename": "document1.pdf",
            "title": "Document 1"
        }
    ],
    "persona": {
        "role": "Travel Planner"
    },
    "job_to_be_done": {
        "task": "Plan a trip for college friends."
    }
}
```

### Container Specifications
- **Base Image**: python:3.9-slim
- **Memory**: Works within 1GB constraint
- **CPU**: CPU-only processing (no GPU required)
- **Processing Time**: Typically completes within 60 seconds
- **Dependencies**: All required packages pre-installed

### Troubleshooting
- Ensure PDF files exist in input folder
- Check config.json format is valid
- Verify Docker has sufficient memory allocated
- Check output folder permissions for result extraction
