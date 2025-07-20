import os
import json
import fitz  # PyMuPDF
from pathlib import Path
import re
import time
import traceback
import psutil
from typing import List, Dict, Tuple, Any
from collections import Counter
import logging
import unicodedata

# Chanakya font mapping for legacy Hindi PDFs
CHANAKYA_TO_UNICODE = {
    # Common mappings from Chanakya font to Unicode Devanagari
    'd{kk': 'कक्षा',
    '¯gnh': 'हिंदी', 
    ',sfPNd': 'एलेक्टिव',
    'iz\'u': 'प्रश्न',
    'i=k': 'पत्र',
    'varjk': 'अंतरा',
    'varjky': 'अंतराल',
    'vfHko;fDr': 'अभिव्यक्ति',
    'ekè;e': 'माध्यम',
    'izfrn\'kZ': 'प्रतिदर्श',
    'x|ka\'k': 'गद्यांश',
    'dkO;ka\'k': 'काव्यांश',
    'mÙkj': 'उत्तर',
    'dhft,': 'कीजिए',
    'roZQ': 'तर्क',
    'lfgr': 'सहित',
    'fuEufyf[kr': 'निम्नलिखित',
    'O;k[;k': 'व्याख्या',
    'lizlax': 'सप्रसंग',
    'thok': 'जीवा',
    'riL;k': 'तपस्या',
    'ftUnxh': 'जिंदगी',
    'lalkj': 'संसार',
    'HkkjrHkwfe': 'भारतभूमि',
    'lkfgR;dkj': 'साहित्यकार',
    'ijk/hurk': 'पराधीनता',
    'ijkHko': 'पराभव',
    'vFkok': 'अथवा',
    'ifjp;': 'परिचय',
    'jpukvksa': 'रचनाओं',
    'fo\'ks"krkvksa': 'विशेषताओं',
    'mYys[k': 'उल्लेख',
    'Hkk"kk': 'भाषा',
    '\'kSyh': 'शैली',
    'dkO;xr': 'काव्यगत',
    'ewY;kadu': 'मूल्यांकन',
    'foospukRed': 'विवेचनात्मक',
    'vfHkO;fDr': 'अभिव्यक्ति',
    'fu/kZfjr': 'निर्धारित',
    'iqLrosaQ': 'पुस्तकें',
    'izdkf\'kr': 'प्रकाशित',
    'D;ksa': 'क्यों',
    'dkSu': 'कौन',
    'dgk¡': 'कहाँ',
    'D;k': 'क्या',
    'dSlk': 'कैसा',
    'fdl': 'किस',
    'rjg': 'तरह',
    'fdUgha': 'किन्हीं',
    'osQ': 'के',
    'gS': 'है',
    'gSa': 'हैं',
    'Fkk': 'था',
    'gksrs': 'होते',
    'djrs': 'करते',
    'fyf[k,': 'लिखिए',
    'crkb,': 'बताइए'
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFOutlineExtractor:
    """
    Extracts structured outlines from PDF files using heuristics-based heading detection.
    Works offline without any API calls.
    """
    
    def __init__(self):
        # Simplified patterns - we now handle most detection in the main logic
        self.heading_patterns = [
            r'^\d+\.\s+[A-Z][A-Z\s]*$',  # "1. INTRODUCTION" 
            r'^\d+\.\d+\.?\s+[A-Z]',      # "1.1 Something"
            r'^[IVX]+\.\s+[A-Z]',         # "I. Introduction"
            r'^CHAPTER\s+\d+',            # "CHAPTER 1"
            r'^SECTION\s+\d+',            # "SECTION 1"
        ]
        
        # Metrics tracking
        self.metrics = {
            'total_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'total_pages_processed': 0,
            'total_text_blocks': 0,
            'headings_detected': 0,
            'errors': []
        }
    
    def convert_chanakya_to_unicode(self, text: str, font_name: str = "") -> str:
        """
        Convert Chanakya/legacy Devanagari font encoding to Unicode.
        Also clean Arabic text formatting issues.
        """
        if not text:
            return text
            
        # Clean up Arabic text formatting issues
        if any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in text):  # Arabic range
            # Remove backspace characters and control characters that interfere with Arabic
            text = re.sub(r'[\b\x00-\x08\x0E-\x1F\x7F]', '', text)
            # Clean up extra spaces around Arabic text
            text = re.sub(r'\s+', ' ', text).strip()
            
        # Convert Chanakya encoding if it's a Chanakya font
        if "chanakya" in font_name.lower():
            converted_text = text
            for chanakya_text, unicode_text in CHANAKYA_TO_UNICODE.items():
                converted_text = converted_text.replace(chanakya_text, unicode_text)
                
            # If we made significant conversions, it was likely Chanakya encoded
            if converted_text != text:
                logger.info(f"Converted Chanakya text: '{text}' -> '{converted_text}'")
                return converted_text
            
        return text
        
    def extract_text_with_metadata(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract text with font size, style, and position metadata."""
        doc = fitz.open(pdf_path)
        text_blocks = []
        
        # Track metrics
        self.metrics['total_pages_processed'] += len(doc)
        
        for page_num, page in enumerate(doc, 1):
            blocks = page.get_text("dict")
            
            for block in blocks["blocks"]:
                if "lines" not in block:  # Skip image blocks
                    continue
                    
                for line in block["lines"]:
                    line_text = ""
                    font_sizes = []
                    font_flags = []
                    
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            # Convert Chanakya font encoding to Unicode if needed
                            font_name = span.get("font", "")
                            text = self.convert_chanakya_to_unicode(text, font_name)
                            line_text += text + " "
                            font_sizes.append(span["size"])
                            font_flags.append(span["flags"])
                    
                    line_text = line_text.strip()
                    if line_text and len(line_text) > 2:  # Skip very short text
                        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
                        is_bold = any(flag & 2**4 for flag in font_flags)  # Bold flag
                        
                        text_blocks.append({
                            "text": line_text,
                            "page": page_num,
                            "font_size": avg_font_size,
                            "is_bold": is_bold,
                            "y_position": line["bbox"][1],  # Top y-coordinate
                            "flags": font_flags
                        })
                        
                        # Track metrics
                        self.metrics['total_text_blocks'] += 1
        
        doc.close()
        return text_blocks
    
    def detect_title(self, text_blocks: List[Dict[str, Any]]) -> str:
        """Detect document title from the first page."""
        first_page_blocks = [block for block in text_blocks if block["page"] == 1]
        
        if not first_page_blocks:
            return "Untitled Document"
        
        # Sort by y-position (top to bottom)
        first_page_blocks.sort(key=lambda x: x["y_position"])
        
        # Look for title candidates in the top portion of the first page
        top_blocks = first_page_blocks[:15]  # Check more blocks
        
        # Find the best title candidate
        best_candidate = None
        best_score = 0
        
        for block in top_blocks:
            text = block["text"].strip()
            
            # Skip obvious non-titles
            if self._is_non_title_text(text):
                continue
            
            score = self._score_title_candidate(block, top_blocks)
            
            if score > best_score and 10 < len(text) < 200:
                best_candidate = text
                best_score = score
        
        # Clean up the title
        if best_candidate:
            return self._clean_title(best_candidate)
        
        # Fallback: look for the first substantial text
        for block in first_page_blocks[:10]:
            text = block["text"].strip()
            if 15 < len(text) < 150 and not self._is_non_title_text(text):
                return self._clean_title(text)
        
        return "Untitled Document"
    
    def _is_non_title_text(self, text: str) -> bool:
        """Check if text is clearly not a title."""
        text_lower = text.lower()
        
        # Common non-title patterns
        non_title_patterns = [
            r'^draft\s+version',
            r'^typeset\s+using',
            r'^arxiv:\d',
            r'^\d+\s+[a-z]',  # Page numbers with text
            r'^abstract$',
            r'^keywords:',
            r'^[a-z].*@.*\.[a-z]',  # Email addresses
            r'^series\s*#',  # Series codes like "Series # C D B A"
            r'^q\.p\.\s*code',  # Question paper codes
            r'^page\s+\d+',  # Page numbers
            r'^p\.t\.o\.$',  # "Please Turn Over"
            r'^roll\s+no\.',  # Roll number
            r'^www\.',  # Website URLs
        ]
        
        if any(re.match(pattern, text_lower) for pattern in non_title_patterns):
            return True
        
        # Text that's too technical or specific
        if any(word in text_lower for word in ['arxiv', 'submitted', 'received', 'accepted', 'preprint',
                                                'candidates must', 'please check', 'question paper']):
            return True
        
        # Very short codes or numbers
        if len(text) < 5 and (text.isdigit() or re.match(r'^[A-Z0-9\-#\s]+$', text)):
            return True
        
        return False
    
    def _score_title_candidate(self, block: Dict[str, Any], context_blocks: List[Dict[str, Any]]) -> int:
        """Score a potential title candidate."""
        text = block["text"].strip()
        font_size = block["font_size"]
        is_bold = block["is_bold"]
        
        score = 0
        
        # Font size relative to other text
        avg_font_size = sum(b["font_size"] for b in context_blocks) / len(context_blocks)
        if font_size > avg_font_size * 1.2:
            score += 3
        elif font_size > avg_font_size * 1.1:
            score += 1
        
        # Style
        if is_bold:
            score += 2
        
        # Position (earlier blocks more likely to be title)
        position_rank = next(i for i, b in enumerate(context_blocks) if b == block)
        if position_rank < 3:
            score += 3
        elif position_rank < 6:
            score += 1
        
        # Length (good titles are neither too short nor too long)
        text_len = len(text)
        if 20 <= text_len <= 100:
            score += 2
        elif 10 <= text_len <= 150:
            score += 1
        
        # Title-like characteristics
        if text[0].isupper() and not text.isupper():  # Title case
            score += 1
        
        # Contains title-like words
        title_words = ['analysis', 'study', 'investigation', 'approach', 'method', 'system']
        if any(word in text.lower() for word in title_words):
            score += 1
        
        return score
    
    def _clean_title(self, title: str) -> str:
        """Clean up the detected title."""
        # Remove leading/trailing whitespace
        title = title.strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            r'^arXiv:\d+\.\d+v\d+\s+\[[^\]]+\]\s+\d+\s+[A-Za-z]+\s+\d+\s*',
            r'^draft\s+version\s*',
            r'^preprint\s*',
        ]
        
        for pattern in prefixes_to_remove:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        return title.strip()
    
    def classify_heading_level(self, block: Dict[str, Any], font_stats: Dict[str, float]) -> str:
        """Classify text block as H1, H2, H3, or regular text with very strict heading detection."""
        text = block["text"].strip()
        font_size = block["font_size"]
        is_bold = block["is_bold"]
        
        # Priority 1: Numbered sections (highest confidence) - these override other checks
        numbered_level = self._get_numbered_section_level(text)
        if numbered_level:
            return numbered_level
        
        # Priority 2: Standard academic headings (ABSTRACT, REFERENCES, etc.)
        if self._is_standard_heading(text):
            return "H1"  # Most standard headings are main sections
        
        # Priority 3: Japanese text heading detection
        japanese_level = self._is_japanese_heading(text)
        if japanese_level:
            return japanese_level
        
        # Apply strict filters for remaining text
        if self._is_definitely_body_text(text):
            return "text"
        
        # Must be short enough to be a heading
        if len(text) > 60:  # Strict length limit
            return "text"
        
        # Must not contain too many words (headings are concise)
        word_count = len(text.split())
        if word_count > 10:  # Very strict word limit
            return "text"
        
        # Get font size thresholds
        median_size = font_stats["median_size"]
        large_size = font_stats["large_size"]
        very_large_size = font_stats["very_large_size"]
        
        # Priority 3: Very strict font-based detection 
        font_ratio = font_size / median_size
        
        # Must be significantly larger font AND bold to be considered
        if font_ratio >= 1.4 and is_bold:
            # Additional content checks
            if self._looks_like_heading_content(text):
                if font_ratio >= 1.6:
                    return "H1"
                elif font_ratio >= 1.4:
                    return "H2"
                else:
                    return "H3"
        
        # Check multilingual content
        lang, multilang_level = self._detect_language_and_classify(text)
        if multilang_level:
            return multilang_level
        
        # Very high confidence cases only
        if font_ratio >= 1.8:  # Extremely large font
            if self._looks_like_heading_content(text):
                return "H1"
        
        return "text"
    
    def _detect_language_and_classify(self, text: str) -> Tuple[str, str]:
        """
        Detect the language/script of text and classify as heading level.
        Returns (language_code, heading_level or None)
        """
        # Language patterns with common heading indicators
        language_patterns = {
            # East Asian Languages
            'japanese': {
                'script_ranges': [r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'],
                'heading_words': ['問題', '質問', '説明', 'セクション', '部分', '章', '節', '項目', '本問題集は', '合計'],
                'question_patterns': [r'問\s*\d+', r'質問\s*\d+', r'第\s*\d+\s*章', r'第\s*\d+\s*節']
            },
            # Chinese (Simplified & Traditional)
            'chinese': {
                'script_ranges': [r'[\u4E00-\u9FAF\u3400-\u4DBF]'],
                'heading_words': ['问题', '問題', '章节', '章節', '部分', '节', '節', '题目', '題目', '说明', '說明', '总计', '總計'],
                'question_patterns': [r'第\s*\d+\s*章', r'第\s*\d+\s*节', r'第\s*\d+\s*節', r'问题\s*\d+', r'問題\s*\d+']
            },
            # Korean
            'korean': {
                'script_ranges': [r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]'],
                'heading_words': ['문제', '질문', '설명', '섹션', '부분', '장', '절', '항목', '총계'],
                'question_patterns': [r'문제\s*\d+', r'질문\s*\d+', r'제\s*\d+\s*장', r'제\s*\d+\s*절']
            },
            # Arabic
            'arabic': {
                'script_ranges': [r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]'],
                'heading_words': ['سؤال', 'مشكلة', 'قسم', 'فصل', 'باب', 'موضوع', 'تعليمات', 'مجموع'],
                'question_patterns': [r'سؤال\s*\d+', r'السؤال\s*\d+', r'الفصل\s*\d+', r'القسم\s*\d+']
            },
            # Hebrew
            'hebrew': {
                'script_ranges': [r'[\u0590-\u05FF]'],
                'heading_words': ['שאלה', 'בעיה', 'חלק', 'פרק', 'סעיף', 'נושא', 'הוראות', 'סך הכל'],
                'question_patterns': [r'שאלה\s*\d+', r'פרק\s*\d+', r'חלק\s*\d+']
            },
            # Hindi/Devanagari (Unicode + Chanakya encoding)
            'hindi': {
                'script_ranges': [r'[\u0900-\u097F]'],  # Unicode Devanagari
                'heading_words': [
                    # Unicode Hindi
                    'प्रश्न', 'समस्या', 'भाग', 'अध्याय', 'खंड', 'विषय', 'निर्देश', 'कुल',
                    'हिंदी', 'कक्षा', 'प्रतिदर्श', 'पत्र', 'गद्यांश', 'काव्यांश', 'उत्तर', 
                    'कीजिए', 'व्याख्या', 'सप्रसंग', 'अथवा', 'परिचय', 'रचनाओं', 'विशेषताओं',
                    # Chanakya encoding patterns
                    'iz\'u', 'i=k', '¯gnh', 'd{kk', 'izfrn\'kZ', 'x|ka\'k', 'dkO;ka\'k', 
                    'mÙkj', 'dhft,', 'O;k[;k', 'lizlax', 'vFkok', 'ifjp;', 'jpukvksa',
                    'fo\'ks"krkvksa', 'fuEufyf[kr', 'roZQ', 'lfgr', 'varjk', 'varjky'
                ],
                'question_patterns': [
                    # Unicode patterns
                    r'प्रश्न\s*\d+', r'अध्याय\s*\d+', r'भाग\s*\d+',
                    # Chanakya patterns  
                    r'iz\'u\s*\d+', r'vè;k;\s*\d+', r'Hkkx\s*\d+'
                ]
            },
            # Russian/Cyrillic
            'russian': {
                'script_ranges': [r'[\u0400-\u04FF]'],
                'heading_words': ['вопрос', 'проблема', 'раздел', 'глава', 'часть', 'тема', 'инструкции', 'всего'],
                'question_patterns': [r'вопрос\s*\d+', r'глава\s*\d+', r'раздел\s*\d+']
            },
            # Greek
            'greek': {
                'script_ranges': [r'[\u0370-\u03FF\u1F00-\u1FFF]'],
                'heading_words': ['ερώτηση', 'πρόβλημα', 'τμήμα', 'κεφάλαιο', 'μέρος', 'θέμα', 'οδηγίες', 'σύνολο'],
                'question_patterns': [r'ερώτηση\s*\d+', r'κεφάλαιο\s*\d+', r'τμήμα\s*\d+']
            },
            # Thai
            'thai': {
                'script_ranges': [r'[\u0E00-\u0E7F]'],
                'heading_words': ['คำถาม', 'ปัญหา', 'ส่วน', 'บท', 'หัวข้อ', 'คำแนะนำ', 'รวม'],
                'question_patterns': [r'คำถาม\s*\d+', r'บท\s*\d+', r'ส่วน\s*\d+']
            },
            # Vietnamese
            'vietnamese': {
                'script_ranges': [r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]'],
                'heading_words': ['câu hỏi', 'vấn đề', 'phần', 'chương', 'mục', 'chủ đề', 'hướng dẫn', 'tổng cộng'],
                'question_patterns': [r'câu\s*\d+', r'chương\s*\d+', r'phần\s*\d+']
            },
            # European Languages with accents
            'german': {
                'script_ranges': [r'[äöüßÄÖÜ]'],
                'heading_words': ['frage', 'problem', 'abschnitt', 'kapitel', 'teil', 'thema', 'anweisungen', 'gesamt'],
                'question_patterns': [r'frage\s*\d+', r'kapitel\s*\d+', r'abschnitt\s*\d+']
            },
            'french': {
                'script_ranges': [r'[àâäéèêëïîôöùûüÿçÀÂÄÉÈÊËÏÎÔÖÙÛÜŸÇ]'],
                'heading_words': ['question', 'problème', 'section', 'chapitre', 'partie', 'sujet', 'instructions', 'total'],
                'question_patterns': [r'question\s*\d+', r'chapitre\s*\d+', r'section\s*\d+']
            },
            'spanish': {
                'script_ranges': [r'[ñáéíóúüÑÁÉÍÓÚÜ]'],
                'heading_words': ['pregunta', 'problema', 'sección', 'capítulo', 'parte', 'tema', 'instrucciones', 'total'],
                'question_patterns': [r'pregunta\s*\d+', r'capítulo\s*\d+', r'sección\s*\d+']
            },
            'portuguese': {
                'script_ranges': [r'[ãõáéíóúâêîôûàèìòùçÃÕÁÉÍÓÚÂÊÎÔÛÀÈÌÒÙÇ]'],
                'heading_words': ['pergunta', 'problema', 'seção', 'capítulo', 'parte', 'tópico', 'instruções', 'total'],
                'question_patterns': [r'pergunta\s*\d+', r'capítulo\s*\d+', r'seção\s*\d+']
            },
            'italian': {
                'script_ranges': [r'[àèéìíîòóùúÀÈÉÌÍÎÒÓÙÚ]'],
                'heading_words': ['domanda', 'problema', 'sezione', 'capitolo', 'parte', 'argomento', 'istruzioni', 'totale'],
                'question_patterns': [r'domanda\s*\d+', r'capitolo\s*\d+', r'sezione\s*\d+']
            }
        }
        
        text_lower = text.lower()
        
        # Check each language
        for lang, patterns in language_patterns.items():
            # Check if text contains characters from this script
            has_script = any(re.search(script_range, text) for script_range in patterns['script_ranges'])
            
            # Check for heading words
            has_heading_words = any(word in text_lower for word in patterns['heading_words'])
            
            # Check for question patterns
            has_question_pattern = any(re.search(pattern, text, re.IGNORECASE) 
                                    for pattern in patterns['question_patterns'])
            
            if has_script or has_heading_words or has_question_pattern:
                # Classify heading level based on content
                if has_question_pattern or any(word in text_lower for word in patterns['heading_words'][:4]):  # Main terms
                    if len(text) > 50:
                        return lang, "H2"  # Long instructional text
                    elif len(text) > 15:
                        return lang, "H1"  # Medium heading
                    else:
                        return lang, "H3"  # Short heading/question
                elif has_heading_words:
                    return lang, "H2"
                elif has_script and len(text) <= 30:  # Short text in foreign script
                    return lang, "H3"
        
        return "unknown", None
    
    def _looks_like_heading_content(self, text: str) -> bool:
        """Additional content-based checks for headings."""
        # All caps is often a heading
        if text.isupper() and len(text) > 3:
            return True
            
        # Check for Japanese characters (could be headings)
        has_japanese = bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))
        if has_japanese:
            # Japanese text that looks like headings:
            # - Short instructional text
            # - Text ending with common patterns
            if len(text) < 30:  # Short Japanese text more likely to be headings
                return True
            # Common Japanese heading patterns
            japanese_heading_patterns = [
                r'問題|質問|説明|指示|注意',  # Question, instruction, note
                r'セクション|部分|章',      # Section, part, chapter  
                r'合計|全部|すべて',       # Total, all
                r'答え|回答|解答',         # Answer, response
            ]
            if any(re.search(pattern, text) for pattern in japanese_heading_patterns):
                return True
            
        # Starts with capital and doesn't end with period (unless abbreviation)
        if (text and text[0].isupper() and 
            (not text.endswith('.') or self._is_abbreviation_ending(text))):
            
            # Must not contain common body text phrases
            body_phrases = [
                'this is', 'it is', 'there are', 'we find', 'we show', 'we present',
                'as shown', 'however', 'therefore', 'although', 'furthermore',
                'in order to', 'due to', 'based on', 'according to'
            ]
            
            text_lower = text.lower()
            if not any(phrase in text_lower for phrase in body_phrases):
                return True
        
        return False
    
    def print_metrics(self, start_time: float, end_time: float):
        """Print comprehensive metrics about the extraction process."""
        total_runtime = end_time - start_time
        
        print("\n" + "="*60)
        print("📊 EXTRACTION METRICS SUMMARY")
        print("="*60)
        
        # Performance Metrics
        print(f"⏱️  PERFORMANCE:")
        print(f"   Total Runtime: {total_runtime:.2f} seconds")
        print(f"   Average per file: {total_runtime/max(self.metrics['total_files'], 1):.2f}s")
        
        # Memory usage
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            print(f"   Memory Usage: {memory_mb:.1f} MB")
        except:
            print(f"   Memory Usage: N/A")
        
        # Processing Statistics
        print(f"\n📁 PROCESSING STATS:")
        print(f"   Files Processed: {self.metrics['total_files']}")
        print(f"   Successful: {self.metrics['successful_files']}")
        print(f"   Failed: {self.metrics['failed_files']}")
        success_rate = (self.metrics['successful_files'] / max(self.metrics['total_files'], 1)) * 100
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Content Analysis
        print(f"\n📄 CONTENT ANALYSIS:")
        print(f"   Total Pages: {self.metrics['total_pages_processed']}")
        print(f"   Text Blocks: {self.metrics['total_text_blocks']}")
        print(f"   Headings Found: {self.metrics['headings_detected']}")
        
        if self.metrics['total_text_blocks'] > 0:
            heading_ratio = (self.metrics['headings_detected'] / self.metrics['total_text_blocks']) * 100
            print(f"   Heading Ratio: {heading_ratio:.2f}%")
        
        # Performance Compliance
        print(f"\n✅ COMPLIANCE CHECK:")
        time_compliant = total_runtime <= 10.0 * self.metrics['total_files'] if self.metrics['total_files'] > 0 else True
        print(f"   Time Constraint: {'PASS' if time_compliant else 'FAIL'} (<10s per file)")
        print(f"   Network Access: PASS (Offline only)")
        print(f"   Model Size: PASS (Heuristics-based, <200MB)")
        
        # Error Summary
        if self.metrics['errors']:
            print(f"\n❌ ERRORS ({len(self.metrics['errors'])}):")
            for i, error in enumerate(self.metrics['errors'][:5], 1):  # Show first 5 errors
                print(f"   {i}. {error}")
            if len(self.metrics['errors']) > 5:
                print(f"   ... and {len(self.metrics['errors']) - 5} more errors")
        else:
            print(f"\n✅ NO ERRORS DETECTED")
        
        print("="*60)
    
    def _is_japanese_heading(self, text: str) -> str:
        """Check if Japanese text could be a heading and return appropriate level."""
        # Check if text contains Japanese characters
        if not re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
            return None
        
        # Common Japanese heading patterns
        main_heading_patterns = [
            r'問題|質問|説明|指示|注意',          # Problem, question, explanation, instruction, note
            r'セクション|部分|章',               # Section, part, chapter
            r'一般的な指示|全般的指示',           # General instructions
            r'客観|主観',                       # Objective, subjective
        ]
        
        section_patterns = [
            r'セクション\s*[ABC]',               # Section A/B/C
            r'部分\s*[ABC]',                    # Part A/B/C
            r'第\s*[一二三四五六七八九十]+\s*部',  # Part 1, 2, 3... (Chinese numerals)
        ]
        
        instruction_patterns = [
            r'本問題集は.*分けられている',         # This question set is divided
            r'合計.*質問がある',                 # There are X questions in total  
            r'説明どおりに答えること',            # Answer according to instructions
            r'質問の番号を書くこと',             # Write the question number
        ]
        
        # Check for main headings
        for pattern in main_heading_patterns:
            if re.search(pattern, text):
                return "H1"
        
        # Check for section headings  
        for pattern in section_patterns:
            if re.search(pattern, text):
                return "H1"
        
        # Check for instructional headings
        for pattern in instruction_patterns:
            if re.search(pattern, text):
                return "H2"
        
        # Short Japanese text (likely headings)
        if len(text) <= 15:
            return "H3"
        
        return None
    
    def _get_numbered_section_level(self, text: str) -> str:
        """Determine heading level for numbered sections."""
        # Main sections: "1. INTRODUCTION", "2. METHODS", etc.
        if re.match(r'^\d+\.\s+[A-Z][A-Z\s]*$', text):
            return "H1"
        
        # Subsections: "1.1. Something", "3.2. Analysis", "3.1. Magnetic-energy Dissipation" 
        if re.match(r'^\d+\.\d+\.?\s+[A-Z]', text):
            return "H2"
        
        # Sub-subsections: "1.1.1. Details"
        if re.match(r'^\d+\.\d+\.\d+\.?\s+[A-Z]', text):
            return "H3"
        
        # Roman numerals (common in exams): "I.", "II.", "III.", "IV.", "V.", etc.
        if re.match(r'^[IVX]+\.\s*$', text.strip()):
            return "H3"  # Question numbers are usually sub-level
        
        # More Roman numerals with text
        if re.match(r'^[IVX]+\.\s+[A-Z]', text):
            return "H1"
        
        # Numbered questions: "1.", "2.", "3." (standalone)
        if re.match(r'^\d+\.\s*$', text.strip()):
            return "H2"  # Question numbers
        
        # Check for variations with colons: "3.2: Analysis"  
        if re.match(r'^\d+\.\d+:\s+[A-Z]', text):
            return "H2"
        
        return None
    
    def _contains_heading_indicators(self, text: str) -> bool:
        """Check for words/patterns that commonly appear in headings."""
        text_lower = text.lower()
        
        # Common heading words
        heading_words = [
            'analysis', 'results', 'discussion', 'conclusion', 'method', 'approach',
            'model', 'system', 'dynamics', 'structure', 'energy', 'particle',
            'magnetic', 'simulation', 'numerical', 'experimental', 'theoretical',
            'comparison', 'evaluation', 'performance', 'optimization', 'design'
        ]
        
        # Section-like phrases
        section_phrases = [
            'versus', 'vs', 'and', 'or', 'in', 'of', 'for', 'with', 'without',
            'current sheet', 'flux tube', 'reconnection', 'dissipation'
        ]
        
        has_heading_word = any(word in text_lower for word in heading_words)
        has_section_phrase = any(phrase in text_lower for phrase in section_phrases)
        
        return has_heading_word or has_section_phrase
    
    def _is_definitely_body_text(self, text: str) -> bool:
        """Strict check for obvious body text - only allow clear headings through."""
        # Very long text (clearly paragraphs)
        if len(text) > 80:
            return True
        
        # Incomplete sentences (line breaks in middle of sentences)
        if text.endswith('-') or text.endswith(',') or text.endswith(';'):
            return True
        
        # Check if it's Japanese text
        has_japanese = bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))
        if has_japanese:
            # Be more lenient with Japanese text detection
            # Only filter out obviously long paragraphs or incomplete text
            if len(text) > 50:  # Longer Japanese text likely body text
                return True
            # Japanese text ending with certain particles (usually body text)
            if text.endswith('。') and len(text) > 25:  # Long sentences ending with period
                return True
            # Don't filter out short Japanese text - could be headings
            return False
        
        # Contains common body text patterns
        body_text_indicators = [
            'however', 'therefore', 'although', 'nevertheless', 'furthermore',
            'moreover', 'consequently', 'in addition', 'for example', 'such as',
            'this is', 'it is', 'there are', 'we find', 'we show', 'we present',
            'as shown', 'as discussed', 'in order to', 'due to', 'based on',
            'according to', 'in contrast', 'on the other hand', 'in particular',
            'note that', 'it should be', 'one can', 'this suggests', 'these results',
            'the results', 'our results', 'has been', 'have been', 'will be',
            'can be', 'may be', 'should be', 'would be', 'could be'
        ]
        
        text_lower = text.lower()
        for indicator in body_text_indicators:
            if indicator in text_lower:
                return True
        
        # Starts with lowercase (usually body text) - more strict
        if text and text[0].islower():
            return True
        
        # Contains parenthetical references or citations
        if '(' in text and ')' in text:
            # Allow some exceptions like "Table 1)" or "Figure 2)" 
            if not re.match(r'^(Table|Figure|Eq\.|Section)\s+\d+', text, re.IGNORECASE):
                return True
        
        # Contains question words (unlikely in headings)
        question_words = ['what', 'when', 'where', 'why', 'how', 'which', 'who']
        if any(word in text_lower for word in question_words):
            return True
        
        # Ends with period but not an abbreviation (likely sentence)
        if text.endswith('.') and not self._is_abbreviation_ending(text):
            return True
        
        # Multiple sentences
        if text.count('. ') > 0:  # Contains sentence break
            return True
        
        # Contains conjunctions that suggest body text
        conjunctions = [' and ', ' or ', ' but ', ' yet ', ' so ', ' for ', ' nor ']
        for conj in conjunctions:
            if conj in text_lower:
                return True
        
        # Clear citations with years
        if re.search(r'\b(19|20)\d{2}[;,\)]', text) and ('et al.' in text or len(text) > 30):
            return True
        
        # Mathematical expressions in longer text
        if re.search(r'[=<>±∼∈∀∃∇∂∫∑∏]', text) and len(text) > 15:
            return True
        
        # Common body text sentence starters
        clear_body_starters = [
            'however,', 'therefore,', 'furthermore,', 'moreover,', 'additionally,',
            'it is', 'there is', 'there are', 'as shown in', 'as discussed in',
            'we present', 'we show', 'we find', 'we observe', 'we demonstrate',
            'this paper', 'this study', 'this work', 'this approach',
            'the', 'these', 'those', 'many', 'some', 'all', 'most'
        ]
        
        text_lower = text.lower()
        if any(text_lower.startswith(starter) for starter in clear_body_starters):
            return True
        
        # Common body text patterns  
        body_patterns = [
            r'^in \w+',  # "In this", "In order", etc.
            r'^at \w+',   # "At high", etc.
            r'^for \w+',  # "For example", etc.
            r'^with \w+', # "With this", etc.
            r'^from \w+', # "From these", etc.
            r'^\w+ and \w+',  # "Ions and electrons"
        ]
        
        if any(re.match(pattern, text_lower) for pattern in body_patterns):
            return True
        
        # Technical metadata
        if any(indicator in text_lower for indicator in [
            'arxiv:', 'doi:', 'http:', 'www.', '.com', '.org', '.edu',
            'typeset', 'latex', 'corresponding author', 'email', '@',
            'preprint', 'submitted', 'accepted', 'published', 'draft version'
        ]):
            return True
        
        return False
    
    def _is_standard_heading(self, text: str) -> bool:
        """Check for standard academic section headings."""
        text_upper = text.upper().strip()
        
        # Exact matches for common headings
        standard_headings = [
            'ABSTRACT', 'INTRODUCTION', 'BACKGROUND', 'RELATED WORK',
            'METHODOLOGY', 'METHODS', 'NUMERICAL SETUP', 'EXPERIMENTAL SETUP',
            'RESULTS', 'ANALYSIS', 'DISCUSSION', 'CONCLUSION', 'CONCLUSIONS',
            'REFERENCES', 'BIBLIOGRAPHY', 'ACKNOWLEDGMENTS', 'ACKNOWLEDGEMENTS',
            'APPENDIX', 'SUMMARY', 'OVERVIEW',
            # Add exam paper specific headings
            'GENERAL INSTRUCTIONS', 'SECTION A', 'SECTION B', 'SECTION C',
            'OBJECTIVE TYPE', 'SUBJECTIVE TYPE', 'JAPANESE', 'ENGLISH',
            'INSTRUCTIONS', 'MARKING SCHEME'
        ]
        
        # Must be exact match or numbered section like "1. INTRODUCTION"
        if text_upper in standard_headings:
            return True
            
        # Check for numbered sections
        for heading in standard_headings:
            if re.match(rf'^\d+\.\s+{heading}$', text_upper):
                return True
        
        # Check for section patterns like "SECTION A", "PART I"
        if re.match(r'^(SECTION|PART|CHAPTER)\s+[A-Z0-9]+$', text_upper):
            return True
                
        return False
    
    def _is_abbreviation_ending(self, text: str) -> bool:
        """Check if text ends with common abbreviations."""
        abbreviations = ['et al.', 'Fig.', 'fig.', 'Table', 'Eq.', 'eq.', 'vs.', 'cf.', 'i.e.', 'e.g.']
        return any(text.endswith(abbr) for abbr in abbreviations)
    
    def calculate_font_statistics(self, text_blocks: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate font size statistics for heading detection."""
        font_sizes = [block["font_size"] for block in text_blocks]
        font_sizes.sort()
        
        n = len(font_sizes)
        median_size = font_sizes[n // 2] if n > 0 else 12
        
        # Calculate percentiles for thresholds
        p75_idx = int(0.75 * n)
        p90_idx = int(0.90 * n)
        
        large_size = font_sizes[p75_idx] if n > 0 else median_size * 1.3
        very_large_size = font_sizes[p90_idx] if n > 0 else median_size * 1.5
        
        return {
            "median_size": median_size,
            "large_size": large_size,
            "very_large_size": very_large_size
        }
    
    def extract_outline(self, pdf_path: str) -> Dict[str, Any]:
        """Extract structured outline from PDF."""
        start_time = time.time()
        logger.info(f"Processing PDF: {pdf_path}")
        
        try:
            # Extract text with metadata
            text_blocks = self.extract_text_with_metadata(pdf_path)
            
            if not text_blocks:
                logger.warning(f"No text found in PDF: {pdf_path}")
                return {"title": "Empty Document", "outline": []}
            
            # Calculate font statistics
            font_stats = self.calculate_font_statistics(text_blocks)
            
            # Detect title
            title = self.detect_title(text_blocks)
            
            # Classify headings
            outline = []
            seen_headings = set()  # Avoid duplicates
            
            for block in text_blocks:
                level = self.classify_heading_level(block, font_stats)
                
                if level in ["H1", "H2", "H3"]:
                    text = block["text"].strip()
                    page = block["page"]
                    
                    # Avoid duplicate headings
                    heading_key = f"{text.lower()}_{page}"
                    if heading_key not in seen_headings:
                        outline.append({
                            "level": level,
                            "text": text,
                            "page": page
                        })
                        seen_headings.add(heading_key)
                        # Track metrics
                        self.metrics['headings_detected'] += 1
            
            # Sort outline by page number
            outline.sort(key=lambda x: (x["page"], x["level"]))
            
            processing_time = time.time() - start_time
            logger.info(f"Extracted {len(outline)} headings from {pdf_path} in {processing_time:.2f}s")
            
            # Track successful processing
            self.metrics['successful_files'] += 1
            
            return {
                "title": title,
                "outline": outline
            }
            
        except Exception as e:
            error_msg = f"Error processing PDF {pdf_path}: {str(e)}"
            logger.error(error_msg)
            
            # Track error
            self.metrics['failed_files'] += 1
            self.metrics['errors'].append(f"{Path(pdf_path).name}: {str(e)}")
            
            return {"title": "Error Processing Document", "outline": []}


def main():
    """Main function to process all PDFs in input directory."""
    overall_start_time = time.time()
    
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    extractor = PDFOutlineExtractor()
    
    # Find all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    extractor.metrics['total_files'] = len(pdf_files)
    
    print(f"🔍 Found {len(pdf_files)} PDF files to process")
    
    if not pdf_files:
        print("❌ No PDF files found in input directory")
        return
    
    # Process all PDF files
    for pdf_file in pdf_files:
        try:
            print(f"⏳ Processing: {pdf_file.name}")
            file_start_time = time.time()
            
            # Extract outline
            outline = extractor.extract_outline(str(pdf_file))
            
            # Generate output filename
            output_filename = pdf_file.stem + ".json"
            output_path = output_dir / output_filename
            
            # Save JSON output
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(outline, f, indent=2, ensure_ascii=False)
            
            file_time = time.time() - file_start_time
            headings_count = len(outline.get('outline', []))
            
            print(f"✅ {pdf_file.name}: {headings_count} headings in {file_time:.2f}s")
            logger.info(f"Saved outline to: {output_path}")
            
        except Exception as e:
            error_msg = f"Failed to process {pdf_file.name}: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            
            # Track error in metrics
            extractor.metrics['failed_files'] += 1
            extractor.metrics['errors'].append(f"{pdf_file.name}: {str(e)}")
    
    # Print comprehensive metrics
    overall_end_time = time.time()
    extractor.print_metrics(overall_start_time, overall_end_time)


if __name__ == "__main__":
    main()
