export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return new Response("OK");
  },
};

interface Env {
  OPENAI_API_KEY: string;
  ANTHROPIC_API_KEY: string;
}
