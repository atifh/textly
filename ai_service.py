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
    
    def fix_text(self, text: str, provider: str = 'openai') -> str:
        """
        Fix text in the provided text while maintaining tone
        
        Args:
            text: The text to fix
            provider: 'openai' or 'claude'
        
        Returns:
            Corrected text
        """
        if provider == 'openai':
            return self._fix_text_openai(text)
        elif provider == 'claude':
            return self._fix_text_claude(text)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    def _fix_text_openai(self, text: str) -> str:
        """Fix text using OpenAI GPT"""
        if not self.openai_client:
            raise Exception("OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
        
        prompt = f"""Please fix the grammar and spelling in the following text while maintaining the original tone and style. 
        Only make necessary corrections and preserve the author's voice and intent.
        
        Original text:
        {text}
        
        Corrected text:"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful grammar correction assistant. Fix only grammar and spelling errors while preserving the original tone, style, and meaning of the text. Return only the corrected text without any additional commentary."},
                    {"role": "user", "content": text}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _fix_text_claude(self, text: str) -> str:
        """Fix text using Anthropic Claude"""
        if not self.anthropic_client:
            raise Exception("Anthropic API key not configured. Please set ANTHROPIC_API_KEY environment variable.")
        
        prompt = f"""Please fix the grammar and spelling in the following text while maintaining the original tone and style. 
        Only make necessary corrections and preserve the author's voice and intent.
        
        Return only the corrected text without any additional commentary or explanations.
        
        Text to correct:
        {text}"""
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text.strip()
        
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    def get_available_providers(self) -> list:
        """Return list of available AI providers based on configured API keys"""
        providers = []
        
        if self.openai_client:
            providers.append('openai')
        
        if self.anthropic_client:
            providers.append('claude')
        
        return providers