const request = require('supertest');
const app = require('./server');

describe('AI Code Reviewer Frontend', () => {
  test('GET /health returns healthy', async () => {
    const res = await request(app).get('/health');
    expect(res.statusCode).toBe(200);
    expect(res.body.status).toBe('healthy');
    expect(res.body.service).toBe('ai-code-reviewer-frontend');
  });
});