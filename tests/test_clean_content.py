import re
import unittest

def clean_content(text: str) -> str:
    # Rimuove immagini Markdown: ![alt](url)
    text = re.sub(r'!\s*\[.*?\]\s*\(.*?\)', '', text)
    
    # Rimuove link Markdown mantenendo il testo: [testo](url) -> testo
    text = re.sub(r'\[([^\\]+?)\]\s*\(.*?\)', r'\1', text)
    
    # Rimuove tag HTML residui
    text = re.sub(r'<[^>]+>', '', text)
    
    # Rimuove righe con troppi caratteri speciali
    text = re.sub(r'^\s*[-=_*]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Collassa newline multipli
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Rimuove spazi multipli
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()

class TestCleanContent(unittest.TestCase):
    def test_clean_links(self):
        raw = "This is a [link](http://example.com) to a site."
        expected = "This is a link to a site."
        self.assertEqual(clean_content(raw), expected)

    def test_clean_images(self):
        raw = "Image: ![alt text](image.jpg) here."
        expected = "Image: here."
        self.assertEqual(clean_content(raw), expected)
        
    def test_clean_newlines(self):
        raw = "Line 1\n\n\n\nLine 2"
        expected = "Line 1\n\nLine 2"
        self.assertEqual(clean_content(raw), expected)

    def test_clean_separators(self):
        raw = "Header\n===\nText\n---"
        expected = "Header\n\nText"
        # Note: clean_content collapses \n\n\n to \n\n
        self.assertEqual(clean_content(raw), expected)

    def test_table_preservation(self):
        # Tables use | so they shouldn't be removed by the separator check
        raw = "| Header 1 | Header 2 |\n| --- | --- |\n| Val 1 | Val 2 |"
        # The separator check is `^[-=_*]{3,}$`.
        # `| --- | --- |` has pipes, so it shouldn't match `^[-=_*]{3,}$`.
        processed = clean_content(raw)
        self.assertIn("| Header 1 | Header 2 |", processed)
        self.assertIn("| Val 1 | Val 2 |", processed)

if __name__ == '__main__':
    unittest.main()
