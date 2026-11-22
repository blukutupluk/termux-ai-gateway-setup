import express from 'express';
import { getKeys, addKey, updateKey, deleteKey, markKeyCooldown, markKeyDisabled } from '../store.js';

const router = express.Router();

// GET /api/keys - List all keys
router.get('/keys', (req, res) => {
  const keys = getKeys();
  // Don't expose the actual API key in list view
  const safeKeys = keys.map(k => ({
    ...k,
    key: k.key ? '••••••••' + k.key.slice(-4) : ''
  }));
  res.json(safeKeys);
});

// POST /api/keys - Add new key
router.post('/keys', (req, res) => {
  const { provider, name, key } = req.body;
  
  if (!provider || !key) {
    return res.status(400).json({ error: 'Provider and key are required' });
  }

  const newKey = addKey({ provider, name, key });
  res.status(201).json({
    ...newKey,
    key: '••••••••' + newKey.key.slice(-4)
  });
});

// PUT /api/keys/:id - Update key
router.put('/keys/:id', (req, res) => {
  const { id } = req.params;
  const updates = req.body;
  
  // Don't allow updating the key value through this endpoint
  delete updates.key;
  delete updates.id;
  delete updates.createdAt;
  
  const updated = updateKey(id, updates);
  if (!updated) {
    return res.status(404).json({ error: 'Key not found' });
  }
  
  res.json({
    ...updated,
    key: '••••••••' + updated.key.slice(-4)
  });
});

// DELETE /api/keys/:id - Delete key
router.delete('/keys/:id', (req, res) => {
  const { id } = req.params;
  const deleted = deleteKey(id);
  if (!deleted) {
    return res.status(404).json({ error: 'Key not found' });
  }
  res.status(204).send();
});

// GET /api/stats - Get statistics
router.get('/stats', (req, res) => {
  const keys = getKeys();
  const stats = {
    totalKeys: keys.length,
    activeKeys: keys.filter(k => k.status === 'active').length,
    cooldownKeys: keys.filter(k => k.status === 'cooldown').length,
    disabledKeys: keys.filter(k => k.status === 'disabled').length,
    providers: {},
    totalSuccessCount: keys.reduce((sum, k) => sum + (k.successCount || 0), 0),
    totalErrorCount: keys.reduce((sum, k) => sum + (k.errorCount || 0), 0)
  };

  for (const key of keys) {
    if (!stats.providers[key.provider]) {
      stats.providers[key.provider] = { total: 0, active: 0, cooldown: 0, disabled: 0 };
    }
    stats.providers[key.provider].total++;
    stats.providers[key.provider][key.status]++;
  }

  res.json(stats);
});

export default router;