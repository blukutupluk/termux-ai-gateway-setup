import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';

const OPENCODE_CONFIG_DIR = path.join(os.homedir(), '.config', 'opencode');
const OPENCODE_CONFIG_FILE = path.join(OPENCODE_CONFIG_DIR, 'opencode.json');

export function generateOpenCodeConfig(baseUrl = 'http://localhost:3000') {
  return {
    provider: {
      'local-manager': {
        type: 'openai',
        options: {
          baseURL: `${baseUrl.replace(/\/$/, '')}/v1`,
          apiKey: 'local-manager'
        },
        models: ['openrouter/*', 'groq/*', 'deepseek/*', 'gemini/*', 'together/*']
      }
    }
  };
}

export async function integrateOpenCode(baseUrl = 'http://localhost:3000') {
  try {
    await fs.mkdir(OPENCODE_CONFIG_DIR, { recursive: true });

    let existingConfig = { provider: {} };
    try {
      const data = await fs.readFile(OPENCODE_CONFIG_FILE, 'utf8');
      existingConfig = JSON.parse(data);
    } catch (err) {
      // Config doesn't exist yet, start fresh
    }

    // Backup existing config
    const backupPath = `${OPENCODE_CONFIG_FILE}.backup.${Date.now()}`;
    await fs.writeFile(backupPath, JSON.stringify(existingConfig, null, 2), 'utf8');

    // Merge with local-manager provider
    const newProviderConfig = generateOpenCodeConfig(baseUrl);
    const mergedConfig = {
      ...existingConfig,
      provider: {
        ...existingConfig.provider,
        ...newProviderConfig.provider
      }
    };

    await fs.writeFile(OPENCODE_CONFIG_FILE, JSON.stringify(mergedConfig, null, 2), 'utf8');

    console.log('✅ OpenCode configuration updated successfully!');
    console.log(`📁 Backup saved to: ${backupPath}`);
    console.log(`🔗 Provider 'local-manager' added pointing to ${baseUrl}/v1`);
    console.log('');
    console.log('You can now use "local-manager" as a provider in OpenCode.');

    return true;
  } catch (err) {
    console.error('❌ Failed to update OpenCode configuration:', err.message);
    throw err;
  }
}

// CLI execution
if (import.meta.url === `file://${process.argv[1]}`) {
  const baseUrl = process.argv[2] || 'http://localhost:3000';
  await integrateOpenCode(baseUrl);
}