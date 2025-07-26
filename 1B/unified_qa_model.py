import os
import json
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import re
import time
import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedDocumentQAModel:
    """
    Unified Document Q&A Model that processes PDFs once and answers questions instantly.
    Optimized for <60 second total processing time including PDF analysis and Q&A.
    """
    
    def __init__(self):
        self.documents = {}
        self.sections = []
        self.vectorizer = TfidfVectorizer(
            max_features=3000,
            stop_words='english',
            ngram_range=(1, 2),
            max_df=0.85,
            min_df=1
        )
        self.document_vectors = None
        self.is_loaded = False
        
        # Persona-specific keywords for quick classification
        self.persona_keywords = {
            'researcher': ['methodology', 'analysis', 'results', 'findings', 'experiment', 
                          'data', 'study', 'research', 'hypothesis', 'conclusion', 'algorithm',
                          'performance', 'evaluation', 'benchmark', 'dataset', 'statistical',
                          'empirical', 'validation', 'theoretical', 'investigation', 'literature'],
            'student': ['definition', 'example', 'concept', 'principle', 'theory', 'formula',
                       'explanation', 'mechanism', 'process', 'key', 'important', 'learn',
                       'understand', 'study', 'exam', 'chapter', 'tutorial', 'homework',
                       'assignment', 'textbook', 'lecture', 'course'],
            'analyst': ['trend', 'growth', 'revenue', 'profit', 'investment', 'market', 
                       'financial', 'performance', 'strategy', 'competitive', 'forecast',
                       'risk', 'opportunity', 'metrics', 'kpi', 'dashboard', 'report',
                       'insights', 'correlation', 'regression', 'statistical'],
            'business': ['strategy', 'market', 'competitive', 'revenue', 'growth', 'customer',
                        'product', 'service', 'opportunity', 'innovation', 'implementation',
                        'stakeholder', 'roi', 'budget', 'planning', 'execution', 'leadership',
                        'team', 'project', 'goal', 'objective'],
            'journalist': ['who', 'what', 'when', 'where', 'why', 'how', 'source', 'facts',
                          'evidence', 'statement', 'development', 'news', 'report', 'interview',
                          'investigation', 'story', 'article', 'press', 'media', 'breaking'],
            'developer': ['code', 'programming', 'software', 'application', 'framework',
                         'library', 'api', 'database', 'algorithm', 'debugging', 'testing',
                         'deployment', 'architecture', 'design', 'implementation', 'bug',
                         'feature', 'function', 'class', 'method'],
            'designer': ['visual', 'aesthetic', 'layout', 'typography', 'color', 'branding',
                        'user', 'interface', 'experience', 'prototype', 'mockup', 'wireframe',
                        'creative', 'design', 'style', 'graphics', 'illustration', 'theme',
                        'composition', 'balance'],
            'manager': ['team', 'project', 'planning', 'execution', 'leadership', 'coordination',
                       'resource', 'timeline', 'budget', 'deliverable', 'milestone', 'stakeholder',
                       'communication', 'meeting', 'decision', 'priority', 'workflow', 'process',
                       'efficiency', 'productivity'],
            'marketer': ['campaign', 'audience', 'brand', 'promotion', 'advertising', 'social',
                        'engagement', 'conversion', 'lead', 'customer', 'target', 'demographic',
                        'content', 'channel', 'reach', 'impression', 'click', 'roi', 'strategy',
                        'positioning'],
            'sales': ['customer', 'client', 'prospect', 'lead', 'conversion', 'revenue', 'quota',
                     'pipeline', 'deal', 'negotiation', 'relationship', 'follow-up', 'closing',
                     'proposal', 'pricing', 'discount', 'commission', 'territory', 'crm',
                     'outreach'],
            'consultant': ['advisory', 'recommendation', 'solution', 'strategy', 'implementation',
                          'best', 'practice', 'optimization', 'improvement', 'assessment',
                          'evaluation', 'framework', 'methodology', 'expertise', 'client',
                          'stakeholder', 'deliverable', 'proposal', 'engagement', 'project'],
            'teacher': ['education', 'learning', 'instruction', 'curriculum', 'lesson', 'student',
                       'assessment', 'evaluation', 'grade', 'classroom', 'pedagogy', 'teaching',
                       'knowledge', 'skill', 'development', 'objective', 'activity', 'assignment',
                       'feedback', 'progress'],
            'doctor': ['patient', 'diagnosis', 'treatment', 'medical', 'clinical', 'symptom',
                      'disease', 'condition', 'therapy', 'medication', 'procedure', 'examination',
                      'health', 'care', 'prevention', 'prognosis', 'consultation', 'specialist',
                      'hospital', 'clinic'],
            'lawyer': ['legal', 'law', 'regulation', 'compliance', 'contract', 'agreement',
                      'litigation', 'court', 'case', 'evidence', 'precedent', 'statute',
                      'jurisdiction', 'client', 'counsel', 'advice', 'representation', 'filing',
                      'brief', 'motion'],
            'engineer': ['technical', 'system', 'design', 'specification', 'requirement',
                        'solution', 'implementation', 'testing', 'optimization', 'efficiency',
                        'performance', 'quality', 'standard', 'protocol', 'methodology',
                        'architecture', 'infrastructure', 'maintenance', 'troubleshooting', 'repair'],
            'travel_planner': ['destination', 'itinerary', 'accommodation', 'hotel', 'flight',
                              'transport', 'activity', 'attraction', 'sightseeing', 'tour',
                              'budget', 'booking', 'reservation', 'travel', 'vacation', 'trip',
                              'journey', 'adventure', 'experience', 'local', 'culture', 'food',
                              'restaurant', 'entertainment', 'schedule'],
            'chef': ['recipe', 'ingredient', 'cooking', 'preparation', 'technique', 'flavor',
                    'seasoning', 'cuisine', 'dish', 'meal', 'kitchen', 'culinary', 'food',
                    'restaurant', 'menu', 'service', 'presentation', 'taste', 'texture',
                    'nutrition'],
            'fitness_trainer': ['exercise', 'workout', 'training', 'fitness', 'strength',
                               'cardio', 'muscle', 'nutrition', 'diet', 'health', 'wellness',
                               'routine', 'program', 'goal', 'progress', 'recovery', 'injury',
                               'prevention', 'movement', 'technique']
        }
        
        # Processing metrics
        self.metrics = {
            'total_processing_time': 0,
            'documents_processed': 0,
            'sections_extracted': 0,
            'qa_response_time': 0
        }
    
    def load_and_process_documents(self, input_dir: str, save_model_path: str = None) -> bool:
        """Load and process all PDFs to create searchable knowledge base."""
        
        # Check if we should load from saved model
        if save_model_path and os.path.exists(save_model_path):
            logger.info(f"Loading existing model from: {save_model_path}")
            return self.load_model(save_model_path)
        
        start_time = time.time()
        
        pdf_files = list(Path(input_dir).glob("*.pdf"))
        if not pdf_files:
            logger.error("No PDF files found in input directory")
            return False
        
        logger.info(f"Processing {len(pdf_files)} PDF files...")
        
        all_texts = []
        self.sections = []
        
        for pdf_file in pdf_files:
            logger.info(f"Processing: {pdf_file.name}")
            sections = self._extract_sections_from_pdf(str(pdf_file))
            
            for section in sections:
                section['document'] = pdf_file.name
                self.sections.append(section)
                all_texts.append(section['content'])
        
        # Create TF-IDF vectors for all sections
        if all_texts:
            logger.info("Creating document vectors...")
            self.document_vectors = self.vectorizer.fit_transform(all_texts)
            self.is_loaded = True
            
            # Update metrics
            self.metrics['documents_processed'] = len(pdf_files)
            self.metrics['sections_extracted'] = len(self.sections)
            self.metrics['total_processing_time'] = time.time() - start_time
            
            logger.info(f"✅ Processed {len(pdf_files)} documents with {len(self.sections)} sections in {self.metrics['total_processing_time']:.2f}s")
            
            # Save model if path provided
            if save_model_path:
                self.save_model(save_model_path)
            
            return True
        
        return False
    
    def save_model(self, filepath: str) -> bool:
        """Save the trained model to a pickle file."""
        try:
            model_data = {
                'documents': self.documents,
                'sections': self.sections,
                'vectorizer': self.vectorizer,
                'document_vectors': self.document_vectors,
                'is_loaded': self.is_loaded,
                'metrics': self.metrics,
                'persona_keywords': self.persona_keywords
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"✅ Model saved to: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save model: {e}")
            return False
    
    def load_model(self, filepath: str) -> bool:
        """Load a trained model from a pickle file."""
        try:
            if not os.path.exists(filepath):
                logger.error(f"❌ Model file not found: {filepath}")
                return False
            
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            # Restore model state
            self.documents = model_data['documents']
            self.sections = model_data['sections']
            self.vectorizer = model_data['vectorizer']
            self.document_vectors = model_data['document_vectors']
            self.is_loaded = model_data['is_loaded']
            self.metrics = model_data['metrics']
            self.persona_keywords = model_data.get('persona_keywords', self.persona_keywords)
            
            logger.info(f"✅ Model loaded from: {filepath}")
            logger.info(f"   Documents: {self.metrics['documents_processed']}")
            logger.info(f"   Sections: {self.metrics['sections_extracted']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return False
    
    def _extract_sections_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract sections from PDF with improved structure detection."""
        doc = fitz.open(pdf_path)
        sections = []
        
        for page_num, page in enumerate(doc, 1):
            blocks = page.get_text("dict")
            current_section = {
                'title': f'Page {page_num}',
                'content': '',
                'page': page_num,
                'sentences': []
            }
            
            for block in blocks.get("blocks", []):
                if "lines" not in block:
                    continue
                
                for line in block["lines"]:
                    line_text = ""
                    font_sizes = []
                    is_bold = False
                    
                    for span in line["spans"]:
                        line_text += span["text"] + " "
                        font_sizes.append(span.get("size", 12))
                        if span.get("flags", 0) & 2**4:  # Bold flag
                            is_bold = True
                    
                    line_text = line_text.strip()
                    if not line_text or len(line_text) < 5:
                        continue
                    
                    # Check if this is a section heading
                    if self._is_section_heading(line_text, font_sizes, is_bold):
                        # Save current section if it has content
                        if current_section['content'].strip():
                            sections.append(current_section.copy())
                        
                        # Start new section
                        current_section = {
                            'title': line_text,
                            'content': '',
                            'page': page_num,
                            'sentences': []
                        }
                    else:
                        # Add to current section
                        current_section['content'] += ' ' + line_text
                        
                        # Split into sentences for granular search
                        sentences = self._simple_sentence_split(line_text)
                        current_section['sentences'].extend(sentences)
            
            # Add final section
            if current_section['content'].strip():
                sections.append(current_section)
        
        doc.close()
        return sections
    
    def _is_section_heading(self, text: str, font_sizes: List[float], is_bold: bool) -> bool:
        """Determine if text is likely a section heading."""
        if len(text) < 5 or len(text) > 100:
            return False
        
        # Pattern-based detection
        heading_patterns = [
            r'^\d+\.\s+[A-Z]',  # "1. Introduction"
            r'^[A-Z][A-Z\s]+$',  # "INTRODUCTION"
            r'^[IVX]+\.\s+[A-Z]',  # "I. Introduction"
            r'^\d+\.\d+\s+[A-Z]',  # "1.1 Background"
            r'^Abstract$|^Introduction$|^Conclusion$|^References$'
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Font-based detection
        if font_sizes and is_bold:
            avg_size = sum(font_sizes) / len(font_sizes)
            if avg_size > 13 and len(text.split()) <= 8:
                return True
        
        return False
    
    def _simple_sentence_split(self, text: str) -> List[str]:
        """Simple sentence splitting without NLTK dependency."""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    
    def identify_persona_type(self, persona: str) -> str:
        """Quickly identify persona type from description."""
        persona_lower = persona.lower()
        
        for persona_type, keywords in self.persona_keywords.items():
            if persona_type in persona_lower:
                return persona_type
            # Check if persona contains relevant keywords
            keyword_matches = sum(1 for keyword in keywords[:5] if keyword in persona_lower)
            if keyword_matches >= 2:
                return persona_type
        
        return 'general'
    
    def answer_question(self, persona: str, job_to_be_done: str, question: str, top_k: int = 10) -> Dict[str, Any]:
        """Answer question instantly using pre-processed knowledge base."""
        if not self.is_loaded:
            return {
                "error": "Model not loaded. Please call load_and_process_documents() first.",
                "processing_time": 0
            }
        
        qa_start_time = time.time()
        
        # Identify persona type
        persona_type = self.identify_persona_type(persona)
        
        # Create enhanced query combining persona context
        persona_keywords = self.persona_keywords.get(persona_type, [])
        enhanced_query = f"{question} {' '.join(persona_keywords[:3])}"
        
        # Vectorize query
        query_vector = self.vectorizer.transform([enhanced_query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.document_vectors).flatten()
        
        # Get top-k most relevant sections
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Prepare results
        extracted_sections = []
        subsection_analysis = []
        answer_parts = []
        
        for i, idx in enumerate(top_indices):
            if similarities[idx] > 0.05:  # Minimum relevance threshold
                section = self.sections[idx]
                
                extracted_sections.append({
                    "document": section['document'],
                    "page_number": section['page'],
                    "section_title": section['title'],
                    "importance_rank": i + 1
                })
                
                # Get most relevant sentences from this section
                if section['sentences']:
                    best_sentences = self._get_best_sentences(
                        section['sentences'], question, persona_keywords, max_sentences=2
                    )
                    
                    for sentence in best_sentences:
                        subsection_analysis.append({
                            "document": section['document'],
                            "section_title": section['title'],
                            "refined_text": sentence,
                            "page_number": section['page']
                        })
                        answer_parts.append(sentence)
                else:
                    # Use section content if no sentences
                    content_preview = section['content'][:200] + "..." if len(section['content']) > 200 else section['content']
                    subsection_analysis.append({
                        "document": section['document'],
                        "section_title": section['title'],
                        "refined_text": content_preview,
                        "page_number": section['page']
                    })
                    answer_parts.append(content_preview)
        
        # Generate final answer
        if answer_parts:
            answer = self._format_answer_for_persona(answer_parts[:3], persona_type)
        else:
            answer = f"I couldn't find relevant information for the question '{question}' in the loaded documents."
        
        qa_time = time.time() - qa_start_time
        self.metrics['qa_response_time'] = qa_time
        
        return {
            "metadata": {
                "input_documents": list(set(section['document'] for section in self.sections)),
                "persona": persona,
                "job_to_be_done": job_to_be_done,
                "processing_timestamp": datetime.now().isoformat(),
                "persona_type": persona_type,
                "qa_response_time": qa_time
            },
            "extracted_sections": extracted_sections,
            "subsection_analysis": subsection_analysis,
            "answer": answer,
            "confidence": float(np.max(similarities)) if len(similarities) > 0 else 0.0,
            "processing_time": qa_time
        }
    
    def _get_best_sentences(self, sentences: List[str], question: str, persona_keywords: List[str], max_sentences: int = 2) -> List[str]:
        """Get most relevant sentences from a section."""
        if not sentences:
            return []
        
        # Score sentences based on question and persona keywords
        scored_sentences = []
        question_words = set(question.lower().split())
        
        for sentence in sentences:
            if len(sentence.strip()) < 20:
                continue
                
            sentence_words = set(sentence.lower().split())
            
            # Question overlap score
            question_overlap = len(question_words & sentence_words) / len(question_words)
            
            # Persona keyword score
            persona_score = sum(1 for keyword in persona_keywords if keyword in sentence.lower())
            
            # Combined score
            total_score = question_overlap * 0.7 + persona_score * 0.3
            
            scored_sentences.append((sentence, total_score))
        
        # Sort by score and return top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sent[0] for sent in scored_sentences[:max_sentences]]
    
    def _format_answer_for_persona(self, answer_parts: List[str], persona_type: str) -> str:
        """Format answer based on persona type."""
        if persona_type == 'student':
            return f"Key Information: {' '.join(answer_parts)}"
        elif persona_type == 'researcher':
            return f"Research Findings: {' '.join(answer_parts)}"
        elif persona_type == 'analyst':
            return f"Analysis: {' '.join(answer_parts)}"
        elif persona_type == 'business':
            return f"Business Insights: {' '.join(answer_parts)}"
        else:
            return ' '.join(answer_parts)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get model performance metrics."""
        return {
            "total_processing_time": f"{self.metrics['total_processing_time']:.2f}s",
            "documents_processed": self.metrics['documents_processed'],
            "sections_extracted": self.metrics['sections_extracted'],
            "last_qa_response_time": f"{self.metrics['qa_response_time']:.3f}s",
            "model_status": "loaded" if self.is_loaded else "not_loaded",
            "avg_sections_per_doc": self.metrics['sections_extracted'] / max(self.metrics['documents_processed'], 1)
        }

def main():
    """Main function to demonstrate the unified Q&A model."""
    input_dir = Path("input")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    if not input_dir.exists():
        print("❌ Input directory not found. Please create 'input' folder and add PDF files.")
        return
    
    # Initialize the unified model
    print("🚀 Initializing Unified Document Q&A Model...")
    model = UnifiedDocumentQAModel()
    
    # Load and process documents (happens once)
    print("📂 Loading and processing documents...")
    if not model.load_and_process_documents(str(input_dir)):
        print("❌ Failed to load documents.")
        return
    
    # Show performance metrics
    metrics = model.get_performance_metrics()
    print(f"✅ Model loaded successfully!")
    print(f"   Processing time: {metrics['total_processing_time']}")
    print(f"   Documents: {metrics['documents_processed']}")
    print(f"   Sections: {metrics['sections_extracted']}")
    
    # Check for predefined question in config
    config_file = input_dir / "config.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if all(key in config for key in ['persona', 'job_to_be_done', 'question']):
            persona = config['persona']
            job_to_be_done = config['job_to_be_done']
            question = config['question']
            
            print(f"\n🎭 Persona: {persona}")
            print(f"🎯 Job: {job_to_be_done}")
            print(f"❓ Question: {question}")
            print("\n🔍 Generating answer...")
            
            # Answer the question (instant response)
            result = model.answer_question(persona, job_to_be_done, question)
            
            # Save result
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            output_file = output_dir / f"qa_result_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Result saved to: {output_file}")
            print(f"💡 Answer: {result['answer']}")
            print(f"🎯 Confidence: {result['confidence']:.3f}")
            print(f"⏱️  Response time: {result['processing_time']:.3f}s")
            print(f"📊 Found {len(result['extracted_sections'])} relevant sections")
            
            return
    
    # Interactive mode
    print("\n" + "="*60)
    print("🎭 UNIFIED DOCUMENT Q&A - INTERACTIVE MODE")
    print("="*60)
    print("The model is loaded and ready for instant Q&A!")
    print("Format: Enter persona, job, and question when prompted")
    print("Type 'quit' to exit")
    print("="*60)
    
    while True:
        try:
            persona = input("\n🎭 Persona (e.g., 'Data Scientist'): ").strip()
            if persona.lower() == 'quit':
                break
                
            job = input("🎯 Job to be done: ").strip()
            if job.lower() == 'quit':
                break
                
            question = input("❓ Question: ").strip()
            if question.lower() == 'quit':
                break
            
            print("🔍 Searching...")
            result = model.answer_question(persona, job, question)
            
            print(f"\n💡 Answer ({result['processing_time']:.3f}s):")
            print("-" * 50)
            print(result['answer'])
            print(f"\n🎯 Confidence: {result['confidence']:.3f}")
            print(f"📊 Sources: {len(result['extracted_sections'])} sections found")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
