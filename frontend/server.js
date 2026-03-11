const express = require('express');
const path = require('path');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3000;
const AI_API_URL = process.env.AI_API_URL || 'http://api-ai:8000';

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'ai-code-reviewer-frontend' });
});

// Proxy → API AI
app.post('/api/review', async (req, res) => {
    try {
        const response = await axios.post(
            `${AI_API_URL}/review`,
            req.body,
            { timeout: 120000 }
        );
        res.json(response.data);
    } catch (err) {
        res.status(503).json({
            error: 'AI service unavailable',
            detail: err.message
        });
    }
});

app.get('/api/languages', async (req, res) => {
    try {
        const response = await axios.get(`${AI_API_URL}/languages`);
        res.json(response.data);
    } catch (err) {
        res.status(503).json({ error: 'AI service unavailable' });
    }
});

app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`AI Code Reviewer frontend running on port ${PORT}`);
});

module.exports = app;