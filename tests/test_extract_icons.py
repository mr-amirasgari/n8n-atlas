
import unittest
from scripts.extract_icons import (
    extract_icon_candidates,
    extract_codex_from_source,
    sanitize_svg,
)

class ExtractIconsTests(unittest.TestCase):
    def test_extracts_file_icon_string(self):
        source = '''
        description = {
          displayName: 'Example',
          icon: 'file:example.svg',
          properties: [],
        }
        '''
        self.assertEqual(extract_icon_candidates(source), ['example.svg'])

    def test_extracts_themed_icon(self):
        source = '''
        description = {
          icon: { light: 'file:logo.svg', dark: 'file:logo.dark.svg' },
          displayName: 'Example',
        }
        '''
        self.assertEqual(
            extract_icon_candidates(source),
            ['logo.svg', 'logo.dark.svg']
        )

    def test_ignores_non_file_icon(self):
        source = '''
        description = {
          icon: 'fa:code',
          displayName: 'Example',
        }
        '''
        self.assertEqual(extract_icon_candidates(source), [])

    def test_extracts_codex_categories_and_subcategories(self):
        source = '''
        description = {
          displayName: 'Example',
          codex: {
            categories: ['AI', 'Data & Storage'],
            subcategories: {
              AI: ['Tools'],
              'Data & Storage': ['Databases'],
            },
          },
        }
        '''
        codex = extract_codex_from_source(source)
        self.assertEqual(codex['categories'], ['AI', 'Data & Storage'])
        self.assertEqual(codex['subcategories']['AI'], ['Tools'])
        self.assertEqual(codex['subcategories']['Data & Storage'], ['Databases'])

    def test_sanitize_svg_removes_script_and_event_handlers(self):
        svg = b'''<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">
          <script>alert(1)</script>
          <rect width="10" height="10" onclick="alert(1)" fill="red"/>
        </svg>'''
        clean = sanitize_svg(svg).decode('utf-8')
        self.assertNotIn('<script', clean)
        self.assertNotIn('onload=', clean)
        self.assertNotIn('onclick=', clean)
        self.assertIn('rect', clean)

if __name__ == '__main__':
    unittest.main()
