import unittest

from scripts.build_catalog import (
    get_node_kind,
    is_featured,
)


class CatalogFeatureTests(unittest.TestCase):

    def test_trigger_detection(self):
        self.assertEqual(
            get_node_kind(
                "Telegram Trigger",
                "TelegramTrigger.node.js"
            ),
            "trigger"
        )

    def test_action_detection(self):
        self.assertEqual(
            get_node_kind(
                "OpenAI",
                "OpenAi.node.js"
            ),
            "action"
        )

    def test_featured_openai(self):
        self.assertTrue(
            is_featured(
                "OpenAI",
                "n8n-nodes-base"
            )
        )

    def test_random_node_not_featured(self):
        self.assertFalse(
            is_featured(
                "Some Random Node",
                "n8n-nodes-random-test"
            )
        )


if __name__ == "__main__":
    unittest.main()