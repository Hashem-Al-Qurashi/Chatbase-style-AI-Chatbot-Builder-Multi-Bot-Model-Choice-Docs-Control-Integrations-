#!/usr/bin/env python3
"""
CRITICAL DOCUMENT PROCESSING TESTING
Testing assumption: Document processing is completely broken and will fail on edge cases.
"""

import os
import sys
import django
import io
import tempfile
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
sys.path.append('/home/sakr_quraish/Projects/Ismail')

try:
    django.setup()
    print("✓ Django setup successful")
except Exception as e:
    print(f"✗ Django setup FAILED: {e}")
    sys.exit(1)

from apps.core.document_processing import (
    DocumentProcessingPipeline,
    PDFProcessor, 
    DOCXProcessor,
    TextProcessor,
    URLProcessor,
    PrivacyLevel,
    DocumentType
)

class CriticalDocumentTest:
    """Ruthlessly test document processing to expose what's broken."""
    
    def __init__(self):
        self.pipeline = DocumentProcessingPipeline()
        self.failures = []
        self.successes = []
        self.test_files_dir = Path('/home/sakr_quraish/Projects/Ismail')
    
    def log_failure(self, test_name, error):
        """Log a test failure."""
        self.failures.append(f"{test_name}: {error}")
        print(f"✗ FAIL: {test_name} - {error}")
    
    def log_success(self, test_name):
        """Log a test success."""
        self.successes.append(test_name)
        print(f"✓ PASS: {test_name}")
    
    def test_pdf_processor_basic(self):
        """Test PDF processor with a real PDF file."""
        try:
            processor = PDFProcessor()
            
            # Look for test PDF files in the project
            pdf_files = list(self.test_files_dir.rglob("*.pdf"))
            if not pdf_files:
                raise Exception("No PDF files found in project for testing")
            
            test_pdf = pdf_files[0]
            
            # Read file content
            with open(test_pdf, 'rb') as f:
                file_content = f.read()
            
            if len(file_content) == 0:
                raise Exception(f"PDF file {test_pdf} is empty")
            
            # Test processor can handle it
            if not processor.can_process("application/pdf", ".pdf"):
                raise Exception("PDF processor claims it can't process PDF files")
            
            # Extract content
            content = processor.extract_content(
                file_content, 
                str(test_pdf), 
                PrivacyLevel.CITABLE
            )
            
            if not content.text or len(content.text.strip()) == 0:
                raise Exception("PDF processor extracted no text")
            
            if content.token_count <= 0:
                raise Exception("PDF processor calculated invalid token count")
            
            if not content.content_hash:
                raise Exception("PDF processor didn't generate content hash")
            
            self.log_success("PDF processor basic functionality")
            return content
            
        except Exception as e:
            self.log_failure("PDF processor basic functionality", str(e))
            return None
    
    def test_docx_processor_basic(self):
        """Test DOCX processor with a real DOCX file."""
        try:
            processor = DOCXProcessor()
            
            # Look for test DOCX files
            docx_files = list(self.test_files_dir.rglob("*.docx"))
            if not docx_files:
                raise Exception("No DOCX files found in project for testing")
            
            test_docx = docx_files[0]
            
            # Read file content
            with open(test_docx, 'rb') as f:
                file_content = f.read()
            
            if len(file_content) == 0:
                raise Exception(f"DOCX file {test_docx} is empty")
            
            # Test processor can handle it
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if not processor.can_process(content_type, ".docx"):
                raise Exception("DOCX processor claims it can't process DOCX files")
            
            # Extract content
            content = processor.extract_content(
                file_content,
                str(test_docx),
                PrivacyLevel.CITABLE
            )
            
            if not content.text or len(content.text.strip()) == 0:
                raise Exception("DOCX processor extracted no text")
            
            if content.token_count <= 0:
                raise Exception("DOCX processor calculated invalid token count")
            
            if not content.content_hash:
                raise Exception("DOCX processor didn't generate content hash")
            
            self.log_success("DOCX processor basic functionality")
            return content
            
        except Exception as e:
            self.log_failure("DOCX processor basic functionality", str(e))
            return None
    
    def test_text_processor_basic(self):
        """Test text processor with real text files."""
        try:
            processor = TextProcessor()
            
            # Look for test text files
            txt_files = list(self.test_files_dir.rglob("*.txt"))
            if not txt_files:
                raise Exception("No TXT files found in project for testing")
            
            test_txt = txt_files[0]
            
            # Read file content
            with open(test_txt, 'rb') as f:
                file_content = f.read()
            
            if len(file_content) == 0:
                raise Exception(f"Text file {test_txt} is empty")
            
            # Test processor can handle it
            if not processor.can_process("text/plain", ".txt"):
                raise Exception("Text processor claims it can't process text files")
            
            # Extract content
            content = processor.extract_content(
                file_content,
                str(test_txt),
                PrivacyLevel.CITABLE
            )
            
            if not content.text:
                raise Exception("Text processor extracted no text")
            
            if content.token_count <= 0:
                raise Exception("Text processor calculated invalid token count")
            
            if not content.content_hash:
                raise Exception("Text processor didn't generate content hash")
            
            self.log_success("Text processor basic functionality")
            return content
            
        except Exception as e:
            self.log_failure("Text processor basic functionality", str(e))
            return None
    
    def test_malformed_files(self):
        """Test processors with malformed files."""
        try:
            processors = [PDFProcessor(), DOCXProcessor(), TextProcessor()]
            
            # Test with empty content
            for processor in processors:
                try:
                    processor.extract_content(b"", "empty_file.txt", PrivacyLevel.CITABLE)
                    raise Exception(f"{processor.__class__.__name__} should reject empty files")
                except ValueError:
                    pass  # Expected
            
            # Test with corrupted content
            corrupted_content = b"This is not a valid PDF/DOCX file"
            
            for processor in processors:
                try:
                    if isinstance(processor, PDFProcessor):
                        processor.extract_content(corrupted_content, "fake.pdf", PrivacyLevel.CITABLE)
                    elif isinstance(processor, DOCXProcessor):
                        processor.extract_content(corrupted_content, "fake.docx", PrivacyLevel.CITABLE)
                    else:
                        # Text processor should handle this
                        continue
                    
                    raise Exception(f"{processor.__class__.__name__} should reject corrupted files")
                except ValueError:
                    pass  # Expected
            
            self.log_success("Malformed file handling")
            return True
            
        except Exception as e:
            self.log_failure("Malformed file handling", str(e))
            return False
    
    def test_pipeline_integration(self):
        """Test the document processing pipeline."""
        try:
            pipeline = DocumentProcessingPipeline()
            
            # Test with text file
            test_content = "This is a test document with some content."
            
            content = pipeline.process_document(
                test_content.encode('utf-8'),
                "test.txt",
                "text/plain",
                PrivacyLevel.CITABLE
            )
            
            if not content.text:
                raise Exception("Pipeline failed to extract text")
            
            if content.text.strip() != test_content:
                raise Exception("Pipeline modified text content")
            
            if content.source_type != DocumentType.TXT:
                raise Exception("Pipeline detected wrong document type")
            
            if content.privacy_level != PrivacyLevel.CITABLE:
                raise Exception("Pipeline didn't preserve privacy level")
            
            self.log_success("Pipeline integration")
            return content
            
        except Exception as e:
            self.log_failure("Pipeline integration", str(e))
            return None
    
    def test_large_file_handling(self):
        """Test handling of large files."""
        try:
            # Create a large text file (1MB+)
            large_content = "This is a test line that will be repeated many times.\n" * 50000
            large_content_bytes = large_content.encode('utf-8')
            
            if len(large_content_bytes) < 1024 * 1024:  # Ensure it's at least 1MB
                large_content = large_content * 10
                large_content_bytes = large_content.encode('utf-8')
            
            content = self.pipeline.process_document(
                large_content_bytes,
                "large_test.txt",
                "text/plain",
                PrivacyLevel.CITABLE
            )
            
            if not content.text:
                raise Exception("Pipeline failed to process large file")
            
            if len(content.text) < len(large_content) * 0.9:  # Allow for some processing differences
                raise Exception("Pipeline truncated large file content")
            
            self.log_success("Large file handling")
            return True
            
        except Exception as e:
            self.log_failure("Large file handling", str(e))
            return False
    
    def test_special_characters(self):
        """Test handling of special characters and encodings."""
        try:
            # Test various character encodings
            test_cases = [
                ("UTF-8", "Hello 世界! 🌍 Héllö"),
                ("Special chars", "Test with ñ, é, ü, ß characters"),
                ("Numbers", "123456789 and symbols !@#$%^&*()"),
            ]
            
            for name, test_text in test_cases:
                content = self.pipeline.process_document(
                    test_text.encode('utf-8'),
                    f"{name.lower()}.txt",
                    "text/plain",
                    PrivacyLevel.CITABLE
                )
                
                if test_text not in content.text:
                    raise Exception(f"Pipeline corrupted {name} text: expected '{test_text}', got '{content.text[:100]}'")
            
            self.log_success("Special character handling")
            return True
            
        except Exception as e:
            self.log_failure("Special character handling", str(e))
            return False
    
    def test_content_validation(self):
        """Test content validation and error handling."""
        try:
            # Test with invalid content types
            try:
                self.pipeline.process_document(
                    b"test content",
                    "test.unknown",
                    "application/unknown",
                    PrivacyLevel.CITABLE
                )
                raise Exception("Pipeline should reject unknown content types")
            except ValueError:
                pass  # Expected
            
            # Test with mismatched content type and extension
            try:
                content = self.pipeline.process_document(
                    b"test content",
                    "test.pdf",  # Claims to be PDF
                    "text/plain",  # But content type is text
                    PrivacyLevel.CITABLE
                )
                # This might work if the processor handles the mismatch gracefully
            except Exception:
                pass  # Either way is acceptable
            
            self.log_success("Content validation")
            return True
            
        except Exception as e:
            self.log_failure("Content validation", str(e))
            return False
    
    def test_caching_behavior(self):
        """Test document processing caching."""
        try:
            test_content = "This is a test for caching behavior."
            
            # Process same content twice
            content1 = self.pipeline.process_document(
                test_content.encode('utf-8'),
                "cache_test.txt",
                "text/plain",
                PrivacyLevel.CITABLE,
                use_cache=True
            )
            
            content2 = self.pipeline.process_document(
                test_content.encode('utf-8'),
                "cache_test.txt",
                "text/plain",
                PrivacyLevel.CITABLE,
                use_cache=True
            )
            
            # Results should be identical
            if content1.content_hash != content2.content_hash:
                raise Exception("Cached content has different hash")
            
            if content1.text != content2.text:
                raise Exception("Cached content has different text")
            
            # Process with caching disabled
            content3 = self.pipeline.process_document(
                test_content.encode('utf-8'),
                "no_cache_test.txt",
                "text/plain",
                PrivacyLevel.CITABLE,
                use_cache=False
            )
            
            if not content3.text:
                raise Exception("Processing without cache failed")
            
            self.log_success("Caching behavior")
            return True
            
        except Exception as e:
            self.log_failure("Caching behavior", str(e))
            return False
    
    def test_privacy_levels(self):
        """Test privacy level handling."""
        try:
            test_content = "This document contains sensitive information."
            
            for privacy_level in [PrivacyLevel.PRIVATE, PrivacyLevel.CITABLE, PrivacyLevel.PUBLIC]:
                content = self.pipeline.process_document(
                    test_content.encode('utf-8'),
                    f"privacy_{privacy_level.value}.txt",
                    "text/plain",
                    privacy_level
                )
                
                if content.privacy_level != privacy_level:
                    raise Exception(f"Privacy level not preserved: expected {privacy_level}, got {content.privacy_level}")
            
            self.log_success("Privacy level handling")
            return True
            
        except Exception as e:
            self.log_failure("Privacy level handling", str(e))
            return False
    
    def run_all_tests(self):
        """Run all document processing tests."""
        print("\n" + "="*80)
        print("CRITICAL DOCUMENT PROCESSING TESTING")
        print("="*80)
        print("Testing assumption: Document processing is fundamentally broken.")
        print()
        
        # Run tests
        self.test_pdf_processor_basic()
        self.test_docx_processor_basic()
        self.test_text_processor_basic()
        self.test_malformed_files()
        self.test_pipeline_integration()
        self.test_large_file_handling()
        self.test_special_characters()
        self.test_content_validation()
        self.test_caching_behavior()
        self.test_privacy_levels()
        
        # Summary
        print("\n" + "="*80)
        print("DOCUMENT PROCESSING TEST RESULTS")
        print("="*80)
        
        total_tests = len(self.successes) + len(self.failures)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {len(self.successes)}")
        print(f"Failed: {len(self.failures)}")
        print(f"Success Rate: {(len(self.successes)/total_tests)*100:.1f}%" if total_tests > 0 else "0.0%")
        
        if self.failures:
            print("\nCRITICAL FAILURES:")
            for failure in self.failures:
                print(f"  ✗ {failure}")
        
        if self.successes:
            print("\nSUCCESSES:")
            for success in self.successes:
                print(f"  ✓ {success}")
        
        print("\n" + "="*80)
        
        if len(self.failures) > len(self.successes):
            print("VERDICT: DOCUMENT PROCESSING IS FUNDAMENTALLY BROKEN")
            return False
        else:
            print("VERDICT: Document processing appears functional (but still suspicious)")
            return True

if __name__ == '__main__':
    tester = CriticalDocumentTest()
    tester.run_all_tests()