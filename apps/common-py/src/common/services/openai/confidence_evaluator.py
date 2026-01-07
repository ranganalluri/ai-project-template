"""OpenAI confidence evaluator for extracted schema values.

Based on Microsoft's content-processing-solution-accelerator implementation:
https://github.com/microsoft/content-processing-solution-accelerator/blob/main/src/ContentProcessor/src/libs/pipeline/handlers/logics/evaluate_handler/openai_confidence_evaluator.py
"""

import logging
import math
from typing import Any

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore

logger = logging.getLogger(__name__)


class OpenAIConfidenceEvaluator:
    """Evaluates confidence for extracted field values based on logprobs from OpenAI Responses API."""

    def __init__(self, model: str = "gpt-4o"):
        """Initialize the confidence evaluator.

        Args:
            model: The model name used for encoding (default: "gpt-4o")
        """
        self.model = model
        self._encoding = None

    def _get_encoding(self):
        """Get or create tiktoken encoding for the model."""
        if tiktoken is None:
            logger.warning("tiktoken not available, confidence evaluation will be limited")
            return None

        if self._encoding is None:
            try:
                self._encoding = tiktoken.encoding_for_model(self.model)
            except (KeyError, ValueError):
                # Fallback to cl100k_base if model not found
                self._encoding = tiktoken.get_encoding("cl100k_base")
                logger.debug(f"Using fallback encoding cl100k_base for model {self.model}")

        return self._encoding

    def _extract_tokens_and_logprobs(self, logprobs: list[Any]) -> tuple[list[str], list[float | None]]:
        """Extract tokens and logprobs from logprobs list.

        Handles both dict and object types (like Logprob objects from OpenAI SDK).

        Args:
            logprobs: List of token logprobs from the response.

        Returns:
            Tuple of (tokens list, token_logprobs list)
        """
        tokens = []
        token_logprobs = []
        for token_logprob in logprobs:
            if isinstance(token_logprob, dict):
                tokens.append(token_logprob.get("token", ""))
                token_logprobs.append(token_logprob.get("logprob"))
            elif hasattr(token_logprob, "token"):
                # Handle Logprob objects - access attributes directly
                tokens.append(getattr(token_logprob, "token", ""))
                token_logprobs.append(getattr(token_logprob, "logprob", None))
            else:
                # Skip if we can't extract token/logprob
                tokens.append("")
                token_logprobs.append(None)
        return tokens, token_logprobs

    def _build_token_offsets(self, tokens: list[str]) -> list[tuple[int, int]]:
        """Build token offsets mapping tokens to character positions.

        Args:
            tokens: List of token strings.

        Returns:
            List of (start, end) character position tuples for each token.
        """
        encoding = self._get_encoding()
        if encoding is None:
            # Fallback: estimate positions based on token lengths
            token_offsets = []
            current_pos = 0
            for token in tokens:
                token_offsets.append((current_pos, current_pos + len(token)))
                current_pos += len(token)
            return token_offsets

        token_offsets = []
        current_pos = 0
        for token in tokens:
            try:
                token_bytes = encoding.encode(token, disallowed_special=())
                token_str = encoding.decode(token_bytes)
                token_length = len(token_str)
                token_offsets.append((current_pos, current_pos + token_length))
                current_pos += token_length
            except Exception:
                # If encoding fails, estimate token length
                token_offsets.append((current_pos, current_pos + len(token)))
                current_pos += len(token)

        return token_offsets

    def evaluate_confidence(
        self,
        extract_result: dict[str, Any],
        generated_text: str,
        logprobs: list[Any],
    ) -> dict[str, Any]:
        """
        Evaluate confidence for each field value in the extracted result based on logprobs.

        Args:
            extract_result: The extraction result dictionary.
            generated_text: The original text from the response.
            logprobs: List of token logprobs from the response (can be dicts or Logprob objects).

        Returns:
            dict: The confidence evaluation of the extraction result with confidence scores
                  for each field and an "_overall" key with the average confidence.
        """
        confidence = {}

        if not logprobs:
            confidence["_overall"] = 0.0
            return confidence

        encoding = self._get_encoding()
        if encoding is None:
            logger.warning("tiktoken not available, using simplified confidence calculation")
            confidence["_overall"] = 0.5  # Default confidence
            return confidence

        # Extract tokens and logprobs
        tokens, token_logprobs = self._extract_tokens_and_logprobs(logprobs)

        # Build token offsets
        token_offsets = self._build_token_offsets(tokens)

        substr_offset = 0

        def find_token_indices(substring: str, start_char: int) -> list[int]:
            """Find the indices of tokens that contain a given substring.

            Args:
                substring: The substring to search for.
                start_char: The starting character position of the substring.

            Returns:
                list: The list of token indices that contain the substring.
            """
            substring_length = len(substring)
            end_char = start_char + substring_length
            indices = []
            for idx, (start, end) in enumerate(token_offsets):
                if start >= end_char:
                    break
                if end > start_char:
                    indices.append(idx)
            return indices

        def evaluate_field_value_confidence(value: Any) -> dict[str, Any] | list[Any]:
            """Evaluate confidence for a field value based on the logprobs of the response.

            Args:
                value: The value to evaluate.

            Returns:
                dict or list: The confidence evaluation of the value.
            """
            nonlocal substr_offset

            if isinstance(value, dict):
                # Recursively evaluate confidence for nested values
                return {key: evaluate_field_value_confidence(val) for key, val in value.items()}
            elif isinstance(value, list):
                # Evaluate confidence for each item in the list
                return [evaluate_field_value_confidence(item) for item in value]
            else:
                value_str = str(value)

                try:
                    # Find the start index of the value in the generated text
                    start_index = generated_text.index(value_str, substr_offset)
                    substr_offset = start_index + len(value_str)
                except ValueError:
                    return {"confidence": 0.0, "value": value}

                # Find all the token indices that cover the value string
                token_indices = find_token_indices(value_str, start_index)

                if not token_indices:
                    return {"confidence": 0.0, "value": value}

                # Get the logprobs for the tokens that cover the value string
                value_logprobs = []
                for idx in token_indices:
                    if idx < len(token_logprobs):
                        logprob = token_logprobs[idx]
                        if logprob is not None:
                            value_logprobs.append(logprob)

                if not value_logprobs:
                    return {"confidence": 0.0, "value": value}

                # Ensure that only likely tokens are considered for confidence calculation
                filtered_logprobs = [logprob for logprob in value_logprobs if logprob > -9999.0]

                if not filtered_logprobs:
                    return {"confidence": 0.0, "value": value}

                # Calculate the average log probability of the likely tokens
                avg_logprob = sum(filtered_logprobs) / len(filtered_logprobs)

                # Convert the average log probability to a confidence score
                conf_score = math.exp(avg_logprob)

                # Clamp the confidence score to the range [0.0, 1.0]
                conf_score = min(max(conf_score, 0.0), 1.0)

                return {"confidence": conf_score, "value": value}

        # Evaluate confidence for each field
        for field, value in extract_result.items():
            confidence[field] = evaluate_field_value_confidence(value)

        # Calculate overall confidence
        confidence_scores = self._get_confidence_values(confidence)

        if confidence_scores:
            confidence["_overall"] = sum(confidence_scores) / len(confidence_scores)
        else:
            confidence["_overall"] = 0.0

        return confidence

    def _get_confidence_values(self, conf_dict: dict[str, Any]) -> list[float]:
        """Recursively extract all confidence values from the confidence dictionary.

        Args:
            conf_dict: The confidence dictionary.

        Returns:
            list: List of all confidence values found in the dictionary.
        """
        values = []
        for key, val in conf_dict.items():
            if key == "_overall":
                continue
            if isinstance(val, dict):
                if "confidence" in val:
                    values.append(val["confidence"])
                else:
                    values.extend(self._get_confidence_values(val))
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and "confidence" in item:
                        values.append(item["confidence"])
        return values

