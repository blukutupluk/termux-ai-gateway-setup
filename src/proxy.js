import { getNextActiveKey, markKeyCooldown, markKeyDisabled } from './store.js';

const PROVIDER_CONFIG = {
  openrouter: {
    baseUrl: 'https://openrouter.ai/api/v1',
    chatEndpoint: '/chat/completions'
  },
  groq: {
    baseUrl: 'https://api.groq.com/openai/v1',
    chatEndpoint: '/chat/completions'
  },
  deepseek: {
    baseUrl: 'https://api.deepseek.com/v1',
    chatEndpoint: '/chat/completions'
  },
  gemini: {
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
    chatEndpoint: '/chat/completions'
  },
  together: {
    baseUrl: 'https://api.together.xyz/v1',
    chatEndpoint: '/chat/completions'
  }
};

export function formatProviderRequest(provider, apiKey, body) {
  const config = PROVIDER_CONFIG[provider];
  if (!config) {
    throw new Error(`Unsupported provider: ${provider}`);
  }

  const url = `${config.baseUrl}${config.chatEndpoint}`;
  const headers = {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
    'Accept': body.stream ? 'text/event-stream' : 'application/json'
  };

  return {
    url,
    headers,
    payload: body
  };
}

async function fetchWithRetry(provider, body, isStream, res, attempt = 0, triedKeyIds = new Set()) {
  const maxAttempts = 3;
  const keyRecord = getNextActiveKey(provider);

  if (!keyRecord) {
    const error = new Error('No active API keys available');
    error.statusCode = 429;
    error.retryAfter = 60;
    throw error;
  }

  // Avoid retrying the same key
  if (triedKeyIds.has(keyRecord.id)) {
    if (attempt >= maxAttempts) {
      const error = new Error('All available keys exhausted');
      error.statusCode = 429;
      error.retryAfter = 60;
      throw error;
    }
    // Try to get next key
    return fetchWithRetry(provider, body, isStream, res, attempt + 1, triedKeyIds);
  }

  triedKeyIds.add(keyRecord.id);

  const { url, headers, payload } = formatProviderRequest(provider, keyRecord.key, body);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });

    if (response.status === 429 || response.status === 401 || response.status === 403) {
      // Rate limited or invalid key - mark and retry
      if (response.status === 429) {
        markKeyCooldown(keyRecord.id, 60000);
      } else {
        markKeyDisabled(keyRecord.id, `HTTP ${response.status}`);
      }

      if (attempt + 1 < maxAttempts) {
        return fetchWithRetry(provider, body, isStream, res, attempt + 1, triedKeyIds);
      } else {
        const error = new Error('All available keys exhausted');
        error.statusCode = 429;
        error.retryAfter = 60;
        throw error;
      }
    }

    if (isStream) {
      // Stream the response directly
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        res.write(chunk);
      }
      res.end();
    } else {
      const data = await response.json();
      res.json(data);
    }
  } catch (err) {
    if (err.statusCode) throw err;
    // Network error - mark cooldown and retry
    markKeyCooldown(keyRecord.id, 30000);
    if (attempt + 1 < maxAttempts) {
      return fetchWithRetry(provider, body, isStream, res, attempt + 1, triedKeyIds);
    }
    throw err;
  }
}

export async function forwardRequest({ provider, body, isStream, res }) {
  await fetchWithRetry(provider, body, isStream, res);
}