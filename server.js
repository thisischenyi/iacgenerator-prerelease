const http = require('http');

const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain');
  res.end('Hello from Node.js!\n');
});

server.listen(8666, '127.0.0.1', () => {
  console.log('Node.js server running on http://localhost:8666/');
});