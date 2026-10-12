import unittest
from brain.benchmarks.naturalness.architecture_costs_20260928 import token_cost


class TokenCostTests(unittest.TestCase):
    rate = {'input_usd_per_million': .35, 'output_usd_per_million': .75}

    def test_reasoning_is_already_in_completion_total(self):
        usage = {'prompt_tokens': 1000, 'completion_tokens': 200,
                 'completion_tokens_details': {'reasoning_tokens': 150}}
        self.assertAlmostEqual(token_cost(usage, self.rate), .0005)

    def test_no_invented_cache_discount(self):
        usage = {'prompt_tokens': 1000, 'completion_tokens': 200,
                 'prompt_tokens_details': {'cached_tokens': 900}}
        self.assertAlmostEqual(token_cost(usage, self.rate), .0005)
        self.assertAlmostEqual(token_cost(usage, {**self.rate, 'cached_input_usd_per_million': .1}), .000275)

    def test_missing_usage_or_rate_is_unknown_not_free(self):
        self.assertIsNone(token_cost({}, self.rate))
        self.assertIsNone(token_cost({'prompt_tokens': 100}, self.rate))
        self.assertIsNone(token_cost({'prompt_tokens': 100, 'completion_tokens': 10}, None))

    def test_invalid_usage_rejected(self):
        for usage in ({'prompt_tokens': -1, 'completion_tokens': 4},
                      {'prompt_tokens': 1, 'completion_tokens': 4, 'prompt_tokens_details': {'cached_tokens': 2}}):
            with self.assertRaises(ValueError):
                token_cost(usage, self.rate)


if __name__ == '__main__':
    unittest.main()
