import unittest

from clip_pocket.i18n import TEXT


class I18nTest(unittest.TestCase):
    def test_all_languages_have_the_same_text_keys(self) -> None:
        english_keys = set(TEXT["en"])

        for language, values in TEXT.items():
            self.assertEqual(set(values), english_keys, language)


if __name__ == "__main__":
    unittest.main()
