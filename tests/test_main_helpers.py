import os
import sys
import unittest

# ensure src/ is on path so package imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from virtual_teacher.main import normalize_question, fallback_for_unknown


class TestMainHelpers(unittest.TestCase):

    def test_normalize_question_various_synonyms(self):
        inputs = [
            "Please explain the hard words and their English meanings",
            "Can you tell me the meaning of the words?",
            "I need the meanings of tricky words",
            "Their english meanings are confusing",
        ]
        expected_substrings = [
            "difficult words",
            "meanings of difficult words",
            "difficult words",
            "English meanings",
        ]

        for inp, expected in zip(inputs, expected_substrings):
            normalized = normalize_question(inp)
            self.assertIn(expected.lower(), normalized.lower(),
                          f"Failed to normalize '{inp}' -> '{normalized}'")

    def test_fallback_for_unknown_with_vocab_request(self):
        subject = "Hindi"
        q = "Please explain the hard words and their English meanings"
        resp = fallback_for_unknown(subject, q)
        self.assertTrue("difficult words" in resp.lower() or "meaning" in resp.lower())

    def test_fallback_for_unknown_with_offtopic(self):
        subject = "Math"
        q = "What is the score of the cricket match?"
        resp = fallback_for_unknown(subject, q)
        self.assertNotIn("cricket", resp.lower())
        self.assertIn(subject.lower(), resp.lower())


if __name__ == "__main__":
    unittest.main()
