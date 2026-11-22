"""Keywords and the optional "Why it matters" sentence."""

import json
import unittest

from trend_digest.keywords import pick_keywords
from trend_digest.why import add_why, llm_from_env


def item(item_id, title, summary=""):
    return {"id": item_id, "title": title, "summary": summary, "source": "x/y", "why": None}


class KeywordTest(unittest.TestCase):
    def test_words_used_by_several_items_come_first(self):
        items = [item("a", "Rust compiler gets faster"), item("b", "Why Rust beats Go"),
                 item("c", "Agents in Rust"), item("d", "Agents everywhere"), item("e", "Compiler news")]
        self.assertEqual(pick_keywords(items), ["Rust", "compiler", "Agents"])

    def test_all_unique_words_fall_back_to_one_word_per_item(self):
        items = [item("a", "Quantum supremacy"), item("b", "Penguins migrate"), item("c", "Volcano erupts")]
        self.assertEqual(pick_keywords(items), ["supremacy", "Penguins", "Volcano"])

    def test_model_answer_is_used_and_bad_answer_falls_back(self):
        items = [item("a", "Quantum supremacy"), item("b", "Penguins migrate"), item("c", "Volcano erupts")]
        self.assertEqual(pick_keywords(items, lambda p: '["one", "two", "three"]'), ["one", "two", "three"])
        self.assertEqual(pick_keywords(items, lambda p: "sorry"), ["supremacy", "Penguins", "Volcano"])


class WhyTest(unittest.TestCase):
    def test_good_sentences_kept_long_ones_dropped(self):
        items = [item("a", "A"), item("b", "B"), item("c", "C")]
        answer = json.dumps({"a": "Short and useful.", "b": " ".join(["word"] * 26)})
        prompts = []
        add_why(items, lambda p: prompts.append(p) or f"Here you go: {answer}")
        self.assertEqual([i["why"] for i in items], ["Short and useful.", None, None])
        self.assertEqual(len(prompts), 1, "one request for the whole digest")

    def test_broken_model_leaves_no_sentences(self):
        items = [item("a", "A")]

        def broken(prompt):
            raise RuntimeError("down")

        add_why(items, broken)
        self.assertIsNone(items[0]["why"])

    def test_model_is_off_without_key(self):
        self.assertIsNone(llm_from_env({"llm_model": "m"}, environ={}))
        self.assertIsNotNone(llm_from_env({"llm_model": "m"}, environ={"LLM_API_KEY": "k"}))


if __name__ == "__main__":
    unittest.main()
