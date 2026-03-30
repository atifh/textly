interface Env {
  OPENAI_API_KEY: string;
  ANTHROPIC_API_KEY: string;
  PASSPHRASE: string;
  TOKEN_SECRET: string;
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

async function callOpenAI(env: Env, text: string, mode: string): Promise<string> {
  const prompt = getPrompt(text, mode);

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: prompt.system },
        { role: "user", content: prompt.user },
      ],
      max_tokens: prompt.maxTokens,
      temperature: prompt.temperature,
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`OpenAI API error: ${err}`);
  }

  const data = (await response.json()) as { choices: { message: { content: string } }[] };
  return data.choices[0].message.content.trim();
}

async function callAnthropic(env: Env, text: string, mode: string): Promise<string> {
  const prompt = getPrompt(text, mode);

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-haiku-4-5-20251001",
      max_tokens: prompt.maxTokens,
      system: prompt.system,
      messages: [{ role: "user", content: prompt.user }],
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Anthropic API error: ${err}`);
  }

  const data = (await response.json()) as { content: { text: string }[] };
  return data.content[0].text.trim();
}

const TOKEN_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

async function generateToken(secret: string): Promise<{ token: string; expiresAt: number }> {
  const expiresAt = Date.now() + TOKEN_EXPIRY_MS;
  const payload = String(expiresAt);
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
  const token = btoa(String.fromCharCode(...new Uint8Array(signature))) + "." + payload;
  return { token, expiresAt };
}

async function verifyToken(token: string, secret: string): Promise<boolean> {
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [sigB64, payload] = parts;
  const expiresAt = Number(payload);
  if (isNaN(expiresAt) || Date.now() > expiresAt) return false;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  );
  let sigBytes: Uint8Array;
  try {
    sigBytes = Uint8Array.from(atob(sigB64), (c) => c.charCodeAt(0));
  } catch {
    return false;
  }
  return crypto.subtle.verify("HMAC", key, sigBytes, new TextEncoder().encode(payload));
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);
    const pathname = url.pathname.replace(/\/+/g, "/");

    if (pathname === "/api/process" && request.method === "POST") {
      let body: ProcessRequest;
      try {
        body = (await request.json()) as ProcessRequest;
      } catch {
        return Response.json(
          { error: "Invalid JSON body." },
          { status: 400, headers: corsHeaders }
        );
      }

      try {
        const { text, mode, provider } = body;

        if (!text || !text.trim()) {
          return Response.json(
            { error: "Please enter some text to process." },
            { status: 400, headers: corsHeaders }
          );
        }

        if (text.trim().length > 10000) {
          return Response.json(
            { error: "Text exceeds maximum length of 10,000 characters." },
            { status: 400, headers: corsHeaders }
          );
        }

        if (!MODE_LABELS[mode]) {
          return Response.json(
            { error: `Unsupported mode: ${mode ?? "missing"}` },
            { status: 400, headers: corsHeaders }
          );
        }

        let result: string;
        if (provider === "openai") {
          result = await callOpenAI(env, text.trim(), mode);
        } else if (provider === "claude") {
          result = await callAnthropic(env, text.trim(), mode);
        } else {
          return Response.json(
            { error: `Unsupported provider: ${provider ?? "missing"}` },
            { status: 400, headers: corsHeaders }
          );
        }

        return Response.json(
          {
            success: true,
            original_text: text.trim(),
            processed_text: result,
            provider,
            mode,
            mode_label: MODE_LABELS[mode],
          },
          { headers: corsHeaders }
        );
      } catch (err) {
        return Response.json(
          { error: (err as Error).message },
          { status: 500, headers: corsHeaders }
        );
      }
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders });
  },
};
