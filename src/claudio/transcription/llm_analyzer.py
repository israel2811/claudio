"""
LLM Analyzer Module.

Analyzes transcribed content using Large Language Models:
- Content summarization
- Key phrase extraction
- Sentiment analysis
- Topic classification
- Intent detection
- Multi-language understanding
"""

import json
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import warnings

from claudio.transcription.transcriber import TranscriptionResult


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    HUGGINGFACE = "huggingface"


@dataclass
class AnalysisResult:
    """Result of LLM analysis."""

    summary: Optional[str] = None
    key_phrases: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    sentiment: Optional[Dict[str, float]] = None
    entities: List[Dict[str, str]] = field(default_factory=list)
    intent: Optional[str] = None
    language: str = "en"
    raw_response: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationAnalysis:
    """Analysis of a conversation with multiple speakers."""

    speaker_summaries: Dict[int, str]  # speaker_id -> summary
    overall_summary: str
    main_topics: List[str]
    key_points: List[str]
    action_items: List[str]
    sentiment_by_speaker: Dict[int, Dict[str, float]]
    conversation_flow: List[Dict[str, Any]]


class LLMAnalyzer:
    """
    LLM-based content analyzer.

    Analyzes transcribed speech using various LLM providers
    to extract meaning, sentiment, and insights.
    """

    # Prompts for different analysis tasks
    ANALYSIS_PROMPTS = {
        "summary": """Summarize the following transcription concisely, capturing the main points:

Text: {text}

Summary:""",

        "key_phrases": """Extract the most important key phrases from this transcription. Return as a JSON list.

Text: {text}

Key phrases (JSON list):""",

        "topics": """Identify the main topics discussed in this transcription. Return as a JSON list.

Text: {text}

Topics (JSON list):""",

        "sentiment": """Analyze the sentiment of this transcription. Return as JSON with keys: positive, negative, neutral (values 0-1).

Text: {text}

Sentiment (JSON):""",

        "entities": """Extract named entities (people, organizations, locations, etc.) from this text. Return as JSON list of {{"entity": "...", "type": "..."}}.

Text: {text}

Entities (JSON list):""",

        "intent": """What is the primary intent or purpose of this speech? Provide a brief description.

Text: {text}

Intent:""",

        "full_analysis": """Analyze the following transcription and provide:
1. A brief summary (2-3 sentences)
2. Key phrases (list of 5-10 important phrases)
3. Main topics (list of topics discussed)
4. Sentiment (positive/negative/neutral with confidence)
5. Key entities mentioned (people, places, organizations)

Return your analysis as JSON with keys: summary, key_phrases, topics, sentiment, entities.

Text: {text}

Analysis (JSON):""",

        "conversation_analysis": """Analyze this multi-speaker conversation:

{conversation}

Provide:
1. Overall summary
2. Summary for each speaker
3. Main topics discussed
4. Key points and conclusions
5. Action items or next steps (if any)
6. Sentiment for each speaker

Return as JSON with keys: overall_summary, speaker_summaries, topics, key_points, action_items, sentiment_by_speaker.

Analysis (JSON):""",
    }

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.LOCAL,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ):
        """
        Initialize LLMAnalyzer.

        Args:
            provider: LLM provider to use.
            model: Model name (provider-specific).
            api_key: API key for cloud providers.
            temperature: Generation temperature.
            max_tokens: Maximum tokens in response.
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._client = None

    def _get_client(self):
        """Initialize and return the appropriate client."""
        if self._client is not None:
            return self._client

        if self.provider == LLMProvider.OPENAI:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
                self.model = self.model or "gpt-4o-mini"
            except ImportError:
                raise RuntimeError("OpenAI package not installed")

        elif self.provider == LLMProvider.ANTHROPIC:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
                self.model = self.model or "claude-3-haiku-20240307"
            except ImportError:
                raise RuntimeError("Anthropic package not installed")

        elif self.provider == LLMProvider.HUGGINGFACE:
            try:
                from transformers import pipeline
                self._client = pipeline(
                    "text-generation",
                    model=self.model or "microsoft/phi-2",
                    device_map="auto",
                )
            except ImportError:
                raise RuntimeError("Transformers package not installed")

        elif self.provider == LLMProvider.LOCAL:
            # Try to use a local model
            self._client = self._setup_local_model()

        return self._client

    def _setup_local_model(self):
        """Setup a local LLM model."""
        try:
            # Try llama.cpp
            from llama_cpp import Llama

            # Look for common model paths
            model_paths = [
                "models/llama-2-7b-chat.gguf",
                "models/mistral-7b-instruct.gguf",
                "~/.cache/llama/model.gguf",
            ]

            for path in model_paths:
                expanded = Path(path).expanduser()
                if expanded.exists():
                    return Llama(model_path=str(expanded), n_ctx=4096)

            warnings.warn("No local model found, using simple heuristic analysis")
            return None

        except ImportError:
            warnings.warn("llama-cpp-python not installed, using heuristic analysis")
            return None

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with a prompt."""
        client = self._get_client()

        if client is None:
            # Fallback to heuristic analysis
            return self._heuristic_analysis(prompt)

        if self.provider == LLMProvider.OPENAI:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content

        elif self.provider == LLMProvider.ANTHROPIC:
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        elif self.provider == LLMProvider.HUGGINGFACE:
            response = client(
                prompt,
                max_new_tokens=self.max_tokens,
                temperature=self.temperature,
                do_sample=True,
            )
            return response[0]["generated_text"][len(prompt):]

        elif self.provider == LLMProvider.LOCAL:
            response = client(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            return response["choices"][0]["text"]

        return ""

    def _heuristic_analysis(self, prompt: str) -> str:
        """Simple heuristic analysis when no LLM is available."""
        # Extract text from prompt
        import re
        text_match = re.search(r'Text: (.+?)(?:\n\n|$)', prompt, re.DOTALL)
        if not text_match:
            return "{}"

        text = text_match.group(1)
        words = text.split()

        # Simple analysis
        result = {
            "summary": " ".join(words[:50]) + "..." if len(words) > 50 else text,
            "key_phrases": self._extract_key_phrases_simple(text),
            "topics": self._extract_topics_simple(text),
            "sentiment": {"positive": 0.5, "negative": 0.3, "neutral": 0.2},
            "entities": [],
        }

        return json.dumps(result)

    def _extract_key_phrases_simple(self, text: str) -> List[str]:
        """Simple key phrase extraction."""
        import re
        # Remove common words and extract longer phrases
        words = re.findall(r'\b\w{4,}\b', text.lower())

        # Count word frequency
        freq = {}
        for word in words:
            freq[word] = freq.get(word, 0) + 1

        # Return top words
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:10]]

    def _extract_topics_simple(self, text: str) -> List[str]:
        """Simple topic extraction."""
        # Very basic topic detection based on keywords
        topics = []
        text_lower = text.lower()

        topic_keywords = {
            "business": ["meeting", "project", "deadline", "budget", "client"],
            "technology": ["software", "computer", "system", "data", "code"],
            "personal": ["family", "home", "friend", "weekend", "vacation"],
            "finance": ["money", "payment", "cost", "price", "investment"],
            "health": ["doctor", "health", "medical", "treatment", "hospital"],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)

        return topics if topics else ["general"]

    def analyze(
        self,
        text: Union[str, TranscriptionResult],
        analysis_type: str = "full_analysis",
    ) -> AnalysisResult:
        """
        Analyze text using LLM.

        Args:
            text: Text or TranscriptionResult to analyze.
            analysis_type: Type of analysis to perform.

        Returns:
            AnalysisResult with analysis results.
        """
        if isinstance(text, TranscriptionResult):
            text_content = text.text
            language = text.language
        else:
            text_content = text
            language = "en"

        if not text_content or len(text_content.strip()) < 10:
            return AnalysisResult(language=language)

        prompt_template = self.ANALYSIS_PROMPTS.get(
            analysis_type,
            self.ANALYSIS_PROMPTS["full_analysis"]
        )
        prompt = prompt_template.format(text=text_content)

        response = self._call_llm(prompt)

        # Parse response
        result = self._parse_response(response, analysis_type)
        result.language = language
        result.raw_response = response

        return result

    def _parse_response(
        self,
        response: str,
        analysis_type: str,
    ) -> AnalysisResult:
        """Parse LLM response into AnalysisResult."""
        result = AnalysisResult()

        # Try to extract JSON from response
        try:
            # Find JSON in response
            import re
            json_match = re.search(r'\{[^{}]*\}|\[[^\[\]]*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                if isinstance(data, dict):
                    result.summary = data.get("summary")
                    result.key_phrases = data.get("key_phrases", [])
                    result.topics = data.get("topics", [])
                    result.sentiment = data.get("sentiment")
                    result.entities = data.get("entities", [])
                    result.intent = data.get("intent")
                elif isinstance(data, list):
                    # Response is just a list
                    if analysis_type == "key_phrases":
                        result.key_phrases = data
                    elif analysis_type == "topics":
                        result.topics = data
                    elif analysis_type == "entities":
                        result.entities = data

        except json.JSONDecodeError:
            # Response is plain text
            if analysis_type == "summary":
                result.summary = response.strip()
            elif analysis_type == "intent":
                result.intent = response.strip()

        return result

    def summarize(
        self,
        text: Union[str, TranscriptionResult],
        max_length: int = 200,
    ) -> str:
        """
        Summarize text content.

        Args:
            text: Text to summarize.
            max_length: Maximum summary length (approximate).

        Returns:
            Summary string.
        """
        result = self.analyze(text, "summary")
        summary = result.summary or result.raw_response

        if summary and len(summary) > max_length:
            summary = summary[:max_length].rsplit(' ', 1)[0] + "..."

        return summary

    def extract_key_information(
        self,
        text: Union[str, TranscriptionResult],
    ) -> Dict[str, Any]:
        """
        Extract key information from text.

        Args:
            text: Text to analyze.

        Returns:
            Dictionary with key information.
        """
        result = self.analyze(text, "full_analysis")

        return {
            "summary": result.summary,
            "key_phrases": result.key_phrases,
            "topics": result.topics,
            "sentiment": result.sentiment,
            "entities": result.entities,
        }

    def analyze_conversation(
        self,
        speaker_transcripts: Dict[int, List[Dict[str, Any]]],
    ) -> ConversationAnalysis:
        """
        Analyze a multi-speaker conversation.

        Args:
            speaker_transcripts: Dictionary mapping speaker_id to list of utterances.

        Returns:
            ConversationAnalysis with detailed analysis.
        """
        # Format conversation for analysis
        conversation_text = []
        for speaker_id, utterances in sorted(speaker_transcripts.items()):
            for utt in utterances:
                conversation_text.append(
                    f"Speaker {speaker_id}: {utt['text']}"
                )

        formatted = "\n".join(conversation_text)

        prompt = self.ANALYSIS_PROMPTS["conversation_analysis"].format(
            conversation=formatted
        )

        response = self._call_llm(prompt)

        # Parse response
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {}
        except json.JSONDecodeError:
            data = {}

        # Build speaker summaries
        speaker_summaries = {}
        for speaker_id in speaker_transcripts.keys():
            speaker_summaries[speaker_id] = data.get(
                "speaker_summaries", {}
            ).get(str(speaker_id), f"Speaker {speaker_id} participated in the conversation.")

        # Build sentiment by speaker
        sentiment_by_speaker = {}
        for speaker_id in speaker_transcripts.keys():
            sentiment_by_speaker[speaker_id] = data.get(
                "sentiment_by_speaker", {}
            ).get(str(speaker_id), {"positive": 0.5, "negative": 0.3, "neutral": 0.2})

        # Build conversation flow
        flow = []
        for speaker_id, utterances in sorted(speaker_transcripts.items()):
            for utt in utterances:
                flow.append({
                    "speaker": speaker_id,
                    "text": utt["text"],
                    "start": utt.get("start", 0),
                    "end": utt.get("end", 0),
                })
        flow.sort(key=lambda x: x["start"])

        return ConversationAnalysis(
            speaker_summaries=speaker_summaries,
            overall_summary=data.get("overall_summary", ""),
            main_topics=data.get("topics", []),
            key_points=data.get("key_points", []),
            action_items=data.get("action_items", []),
            sentiment_by_speaker=sentiment_by_speaker,
            conversation_flow=flow,
        )

    def translate_summary(
        self,
        text: str,
        target_language: str,
    ) -> str:
        """
        Translate a summary to another language.

        Args:
            text: Text to translate.
            target_language: Target language code.

        Returns:
            Translated text.
        """
        prompt = f"""Translate the following text to {target_language}:

{text}

Translation:"""

        response = self._call_llm(prompt)
        return response.strip()

    def detect_sensitive_content(
        self,
        text: Union[str, TranscriptionResult],
    ) -> Dict[str, Any]:
        """
        Detect potentially sensitive content in transcription.

        Args:
            text: Text to analyze.

        Returns:
            Dictionary with sensitivity flags and details.
        """
        if isinstance(text, TranscriptionResult):
            text_content = text.text
        else:
            text_content = text

        prompt = f"""Analyze this text for sensitive content categories:
- Personal information (names, addresses, phone numbers, IDs)
- Financial information (account numbers, credit cards)
- Health information
- Profanity or offensive language
- Confidential business information

Text: {text_content}

Return JSON with keys: has_sensitive (bool), categories (list), details (dict).

Analysis (JSON):"""

        response = self._call_llm(prompt)

        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        return {
            "has_sensitive": False,
            "categories": [],
            "details": {},
        }
