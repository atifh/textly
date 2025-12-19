import os
from openai import OpenAI
import anthropic
from typing import Optional

class AIService:
    """Service class to handle AI API calls for grammar correction"""
    
    def __init__(self):
        """Initialize AI clients"""
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize OpenAI client if API key is available
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Initialize Anthropic client if API key is available
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
    
    def process_text(self, text: str, mode: str = 'fix', provider: str = 'openai') -> str:
        """
        Process text based on the specified mode
        
        Args:
            text: The text to process
            mode: Processing mode ('fix', 'rewrite_formal', 'rewrite_casual', 'summarize', 'expand', 'sentiment')
            provider: 'openai' or 'claude'
        
        Returns:
            Processed text or analysis result
        """
        if provider == 'openai':
            return self._process_text_openai(text, mode)
        elif provider == 'claude':
            return self._process_text_claude(text, mode)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    def fix_text(self, text: str, provider: str = 'openai') -> str:
        """
        Fix text in the provided text while maintaining tone (backward compatibility)
        
        Args:
            text: The text to fix
            provider: 'openai' or 'claude'
        
        Returns:
            Corrected text
        """
        return self.process_text(text, 'fix', provider)
    
    def _process_text_openai(self, text: str, mode: str) -> str:
        """Process text using OpenAI GPT based on mode"""
        if not self.openai_client:
            raise Exception("OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
        
        # Define prompts and system messages for different modes
        prompts = {
            'fix': {
                'system': "You are a helpful grammar correction assistant. Fix only grammar and spelling errors while preserving the original tone, style, and meaning of the text. Return only the corrected text without any additional commentary.",
                'user': text
            },
            'rewrite_formal': {
                'system': "You are a professional writing assistant. Convert the given text to a formal, professional tone while maintaining the original meaning and key information. Use proper business language, avoid contractions, and ensure professional vocabulary.",
                'user': f"Convert this text to formal/professional tone:\n\n{text}"
            },
            'rewrite_casual': {
                'system': "You are a friendly writing assistant. Convert the given text to a casual, conversational tone while maintaining the original meaning and key information. Use contractions, informal language, and a friendly approach.",
                'user': f"Convert this text to casual/conversational tone:\n\n{text}"
            },
            'summarize': {
                'system': "You are a summarization expert. Create a concise summary that captures the main points and key information from the original text. Maintain the essential meaning while significantly reducing length.",
                'user': f"Summarize the following text, keeping the key points:\n\n{text}"
            },
            'expand': {
                'system': "You are a professional writing assistant. Expand the given text to be more detailed, comprehensive, and professional while maintaining the original meaning and tone. Add relevant context, examples, or elaboration where appropriate.",
                'user': f"Expand this text to be more detailed and professional:\n\n{text}"
            },
            'sentiment': {
                'system': "You are a sentiment analysis expert. Analyze the emotional tone of the given text and classify it as: Positive, Negative, or Neutral. Also provide a brief explanation of the key emotional indicators you identified. Format your response as: 'Sentiment: [Classification]\\nAnalysis: [Brief explanation]'",
                'user': f"Analyze the sentiment of this text:\n\n{text}"
            }
        }
        
        if mode not in prompts:
            raise ValueError(f"Unsupported processing mode: {mode}")
        
        prompt_config = prompts[mode]
        max_tokens = 1500 if mode in ['expand', 'sentiment'] else 1000
        temperature = 0.3 if mode in ['rewrite_formal', 'rewrite_casual', 'expand'] else 0.1
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt_config['system']},
                    {"role": "user", "content": prompt_config['user']}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _fix_text_openai(self, text: str) -> str:
        """Fix text using OpenAI GPT (backward compatibility)"""
        return self._process_text_openai(text, 'fix')
    
    def _process_text_claude(self, text: str, mode: str) -> str:
        """Process text using Anthropic Claude based on mode"""
        if not self.anthropic_client:
            raise Exception("Anthropic API key not configured. Please set ANTHROPIC_API_KEY environment variable.")
        
        # Define prompts for different modes
        prompts = {
            'fix': f"""Please fix the grammar and spelling in the following text while maintaining the original tone and style. 
            Only make necessary corrections and preserve the author's voice and intent.
            
            Return only the corrected text without any additional commentary or explanations.
            
            Text to correct:
            {text}""",
            
            'rewrite_formal': f"""Convert the following text to a formal, professional tone while maintaining the original meaning and key information. 
            Use proper business language, avoid contractions, and ensure professional vocabulary.
            
            Return only the rewritten text without any additional commentary.
            
            Text to convert:
            {text}""",
            
            'rewrite_casual': f"""Convert the following text to a casual, conversational tone while maintaining the original meaning and key information. 
            Use contractions, informal language, and a friendly approach.
            
            Return only the rewritten text without any additional commentary.
            
            Text to convert:
            {text}""",
            
            'summarize': f"""Create a concise summary that captures the main points and key information from the following text. 
            Maintain the essential meaning while significantly reducing length.
            
            Return only the summary without any additional commentary.
            
            Text to summarize:
            {text}""",
            
            'expand': f"""Expand the following text to be more detailed, comprehensive, and professional while maintaining the original meaning and tone. 
            Add relevant context, examples, or elaboration where appropriate.
            
            Return only the expanded text without any additional commentary.
            
            Text to expand:
            {text}""",
            
            'sentiment': f"""Analyze the emotional tone of the following text and classify it as: Positive, Negative, or Neutral. 
            Also provide a brief explanation of the key emotional indicators you identified. 
            
            Format your response as:
            Sentiment: [Classification]
            Analysis: [Brief explanation]
            
            Text to analyze:
            {text}"""
        }
        
        if mode not in prompts:
            raise ValueError(f"Unsupported processing mode: {mode}")
        
        max_tokens = 1500 if mode in ['expand', 'sentiment'] else 1000
        temperature = 0.3 if mode in ['rewrite_formal', 'rewrite_casual', 'expand'] else 0.1
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompts[mode]}
                ]
            )
            
            return response.content[0].text.strip()
        
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    def _fix_text_claude(self, text: str) -> str:
        """Fix text using Anthropic Claude (backward compatibility)"""
        return self._process_text_claude(text, 'fix')
    
    def get_available_providers(self) -> list:
        """Return list of available AI providers based on configured API keys"""
        providers = []
        
        if self.openai_client:
            providers.append('openai')
        
        if self.anthropic_client:
            providers.append('claude')
        
        return providers