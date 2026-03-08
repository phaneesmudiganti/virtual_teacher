"""
Document processing utilities extracted from `utils.py`.
"""
import os
import io
import logging
from typing import Optional, Dict, Any
import pytesseract
from PIL import Image
import fitz
import cv2

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Handles various document types including camera-captured PDFs and images.
    Provides OCR capabilities and content analysis.
    """

    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def enhance_image_quality(self, image_path: str) -> str:
        logger.info(f"Enhancing image quality: {image_path}")
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        enhanced_path = image_path.replace('.jpg', '_enhanced.jpg').replace('.png', '_enhanced.png')
        cv2.imwrite(enhanced_path, thresh)
        logger.info(f"Enhanced image saved: {enhanced_path}")
        return enhanced_path

    def extract_text_from_image(self, image_path: str) -> str:
        try:
            logger.info(f"Extracting text from image: {image_path}")
            enhanced_path = self.enhance_image_quality(image_path)

            # Try Hindi first, then English, then both
            text_results = []

            # Try Hindi OCR
            try:
                hindi_text = pytesseract.image_to_string(
                    Image.open(enhanced_path),
                    config='--psm 6 -l hin'
                )
                if hindi_text.strip():
                    text_results.append(("hindi", hindi_text.strip()))
                    logger.info(f"Hindi OCR extracted {len(hindi_text.strip())} characters")
            except Exception as e:
                logger.warning(f"Hindi OCR failed: {e}")

            # Try English OCR
            try:
                eng_text = pytesseract.image_to_string(
                    Image.open(enhanced_path),
                    config='--psm 6 -l eng'
                )
                if eng_text.strip():
                    text_results.append(("english", eng_text.strip()))
                    logger.info(f"English OCR extracted {len(eng_text.strip())} characters")
            except Exception as e:
                logger.warning(f"English OCR failed: {e}")

            # Try combined Hindi+English OCR
            try:
                combined_text = pytesseract.image_to_string(
                    Image.open(enhanced_path),
                    config='--psm 6 -l hin+eng'
                )
                if combined_text.strip():
                    text_results.append(("combined", combined_text.strip()))
                    logger.info(f"Combined OCR extracted {len(combined_text.strip())} characters")
            except Exception as e:
                logger.warning(f"Combined OCR failed: {e}")

            # Choose the best result
            if text_results:
                # Prefer combined, then Hindi, then English
                for lang_type, text in text_results:
                    if lang_type == "combined" and len(text) > 20:
                        result = text
                        break
                    elif lang_type == "hindi" and len(text) > 20:
                        result = text
                        break
                else:
                    # Use the longest result
                    result = max(text_results, key=lambda x: len(x[1]))[1]
            else:
                result = ""

            if os.path.exists(enhanced_path):
                os.remove(enhanced_path)

            logger.info(f"Final image OCR result: {len(result)} characters")
            return result
        except Exception:
            logger.exception("Failed to extract text from image")
            raise ValueError("Failed to extract text from image")

    def process_pdf_with_ocr(self, pdf_path: str) -> str:
        try:
            logger.info(f"Processing PDF with OCR if needed: {pdf_path}")
            regular_text = self._extract_regular_pdf_text(pdf_path)
            if regular_text and len(regular_text.strip()) > 50:
                logger.info("Using regular PDF text extraction path")
                return regular_text
            logger.info("Falling back to OCR PDF extraction")
            return self._extract_pdf_with_ocr(pdf_path)
        except Exception:
            logger.exception("Failed to process PDF")
            raise ValueError("Failed to process PDF")

    def identify_content_type(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        # Also check for Devanagari script characters (Hindi)
        text_combined = text_lower

        content_type = {
            'type': 'general',
            'subject': 'unknown',
            'has_questions': False,
            'has_exercises': False,
            'confidence': 0.5
        }

        subjects = {
            'math': ['math', 'mathematics', 'algebra', 'geometry', 'arithmetic',
                     'addition', 'subtraction', 'multiplication', 'division',
                     'गणित', 'जोड़', 'घटाव', 'गुणा', 'भाग', 'अंकगणित'],
            'english': ['english', 'grammar', 'vocabulary', 'reading', 'writing', 'story', 'poem',
                       'अंग्रेजी', 'व्याकरण', 'शब्दावली', 'पठन', 'लेखन', 'कहानी', 'कविता'],
            'science': ['science', 'physics', 'chemistry', 'biology', 'experiment', 'observation',
                       'विज्ञान', 'भौतिकी', 'रसायन', 'जीवविज्ञान', 'प्रयोग', 'निरीक्षण'],
            'history': ['history', 'ancient', 'medieval', 'freedom', 'independence', 'rulers',
                       'इतिहास', 'प्राचीन', 'मध्यकालीन', 'स्वतंत्रता', 'राजा', 'सम्राट'],
            'geography': ['geography', 'map', 'continent', 'country', 'climate', 'river', 'mountain',
                         'भूगोल', 'नक्शा', 'महाद्वीप', 'देश', 'जलवायु', 'नदी', 'पर्वत'],
            'hindi': ['hindi', 'language', 'literature', 'poetry', 'story', 'grammar',
                     'हिंदी', 'भाषा', 'साहित्य', 'कविता', 'व्याकरण', 'कहानी']
        }

        for subject, keywords in subjects.items():
            if any(keyword in text_combined for keyword in keywords):
                content_type['subject'] = subject
                content_type['confidence'] = 0.8
                break

        # Check for homework indicators (both English and Hindi)
        homework_indicators = ['homework', 'assignment', 'complete', 'solve', 'गृहकार्य', 'अभ्यास', 'हल करें', 'पूरा करें']
        if any(word in text_combined for word in homework_indicators):
            content_type['type'] = 'homework'
            content_type['confidence'] = 0.9
        elif any(word in text_combined for word in ['chapter', 'lesson', 'learn', 'understand', 'अध्याय', 'पाठ', 'सीखें', 'समझें']):
            content_type['type'] = 'textbook'
            content_type['confidence'] = 0.8

        # Check for questions (both English and Hindi)
        question_indicators = ['?', 'what', 'how', 'why', 'where', 'when', 'which', 'solve', 'find', 'calculate',
                              'क्या', 'कैसे', 'क्यों', 'कहाँ', 'कब', 'कौन', 'हल करें', 'ढूँढें', 'गणना करें']
        if any(indicator in text_combined for indicator in question_indicators):
            content_type['has_questions'] = True

        # Check for exercises (both English and Hindi)
        exercise_indicators = ['exercise', 'practice', 'solve', 'complete', 'fill', 'choose', 'match',
                              'अभ्यास', 'प्रयोग', 'हल', 'पूरा', 'भरें', 'चुनें', 'मिलाएँ']
        if any(indicator in text_combined for indicator in exercise_indicators):
            content_type['has_exercises'] = True

        return content_type

    def _extract_regular_pdf_text(self, pdf_path: str) -> str:
        try:
            doc = fitz.open(pdf_path)
            content = ""
            for page in doc:
                text = page.get_text()
                if text:
                    content += text + "\n"
            doc.close()
            logger.info(f"Regular PDF extraction characters: {len(content.strip())}")
            return content.strip()
        except Exception:
            logger.exception("Regular PDF text extraction failed")
            return ""

    def _extract_pdf_with_ocr(self, pdf_path: str) -> str:
        doc = fitz.open(pdf_path)
        full_text = ""
        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))

                # Try multiple OCR languages like in image processing
                page_results = []

                # Try Hindi OCR
                try:
                    hindi_text = pytesseract.image_to_string(img, config='--psm 6 -l hin')
                    if hindi_text.strip():
                        page_results.append(("hindi", hindi_text.strip()))
                except Exception as e:
                    logger.warning(f"Hindi OCR failed for page {page_num + 1}: {e}")

                # Try English OCR
                try:
                    eng_text = pytesseract.image_to_string(img, config='--psm 6 -l eng')
                    if eng_text.strip():
                        page_results.append(("english", eng_text.strip()))
                except Exception as e:
                    logger.warning(f"English OCR failed for page {page_num + 1}: {e}")

                # Try combined OCR
                try:
                    combined_text = pytesseract.image_to_string(img, config='--psm 6 -l hin+eng')
                    if combined_text.strip():
                        page_results.append(("combined", combined_text.strip()))
                except Exception as e:
                    logger.warning(f"Combined OCR failed for page {page_num + 1}: {e}")

                # Choose best result for this page
                if page_results:
                    for lang_type, text in page_results:
                        if lang_type == "combined" and len(text) > 20:
                            page_text = text
                            break
                        elif lang_type == "hindi" and len(text) > 20:
                            page_text = text
                            break
                    else:
                        page_text = max(page_results, key=lambda x: len(x[1]))[1]
                else:
                    page_text = ""

                full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                logger.debug(f"OCR processed page {page_num + 1}, extracted {len(page_text)} characters")
            return full_text.strip()
        except Exception:
            logger.exception("OCR PDF extraction failed")
            return full_text.strip()
        finally:
            doc.close()
