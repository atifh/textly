interface Env {
  OPENAI_API_KEY: string;
  ANTHROPIC_API_KEY: string;
}

interface ProcessRequest {
  text: string;
  mode: string;
  provider: "openai" | "claude";
}

const MODE_LABELS: Record<string, string> = {
  fix: "Corrected Text",
  rewrite_formal: "Formal Version",
  rewrite_casual: "Casual Version",
  summarize: "Summary",
  expand: "Expanded Text",
  sentiment: "Sentiment Analysis",
};

interface PromptConfig {
  system: string;
  user: string;
  maxTokens: number;
  temperature: number;
}

function getPrompt(text: string, mode: string): PromptConfig {
  const highTemp = 0.3;
  const lowTemp = 0.1;
  const highTokens = 1500;
  const lowTokens = 1000;

  const prompts: Record<string, PromptConfig> = {
    fix: {
      system:
        "You are a helpful grammar correction assistant. Fix only grammar and spelling errors while preserving the original tone, style, and meaning of the text. Return only the corrected text without any additional commentary.",
      user: text,
      maxTokens: lowTokens,
      temperature: lowTemp,
    },
    rewrite_formal: {
      system:
        "You are a professional writing assistant. Convert the given text to a formal, professional tone while maintaining the original meaning and key information. Use proper business language, avoid contractions, and ensure professional vocabulary.",
      user: `Convert this text to formal/professional tone:\n\n${text}`,
      maxTokens: lowTokens,
      temperature: highTemp,
    },
    rewrite_casual: {
      system:
        "You are a friendly writing assistant. Convert the given text to a casual, conversational tone while maintaining the original meaning and key information. Use contractions, informal language, and a friendly approach.",
      user: `Convert this text to casual/conversational tone:\n\n${text}`,
      maxTokens: lowTokens,
      temperature: highTemp,
    },
    summarize: {
      system:
        "You are a summarization expert. Create a concise summary that captures the main points and key information from the original text. Maintain the essential meaning while significantly reducing length.",
      user: `Summarize the following text, keeping the key points:\n\n${text}`,
      maxTokens: lowTokens,
      temperature: lowTemp,
    },
    expand: {
      system:
        "You are a professional writing assistant. Expand the given text to be more detailed, comprehensive, and professional while maintaining the original meaning and tone. Add relevant context, examples, or elaboration where appropriate.",
      user: `Expand this text to be more detailed and professional:\n\n${text}`,
      maxTokens: highTokens,
      temperature: highTemp,
    },
    sentiment: {
      system:
        "You are a sentiment analysis expert. Analyze the emotional tone of the given text and classify it as: Positive, Negative, or Neutral. Also provide a brief explanation of the key emotional indicators you identified. Format your response as: 'Sentiment: [Classification]\\nAnalysis: [Brief explanation]'",
      user: `Analyze the sentiment of this text:\n\n${text}`,
      maxTokens: highTokens,
      temperature: lowTemp,
    },
  };

  if (!prompts[mode]) throw new Error(`Unsupported mode: ${mode}`);
  return prompts[mode];
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return new Response("OK");
  },
};
