const assert = require('assert');
const http = require('http');
const { app } = require('../server');

const server = app.listen(0, () => {
  const { port } = server.address();

  const req = http.request(
    {
      hostname: '127.0.0.1',
      port,
      path: '/cart/add',
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    },
    (res) => {
      let body = '';
      res.on('data', (chunk) => {
        body += chunk;
      });
      res.on('end', () => {
        assert.strictEqual(res.statusCode, 302);

        const cartReq = http.request(
          {
            hostname: '127.0.0.1',
            port,
            path: '/cart',
            method: 'GET',
            headers: {
              Cookie: res.headers['set-cookie'][0]
            }
          },
          (cartRes) => {
            let cartBody = '';
            cartRes.on('data', (chunk) => {
              cartBody += chunk;
            });
            cartRes.on('end', () => {
              assert.ok(cartBody.includes('Organic Turmeric Powder'));
              console.log('Cart flow test passed');
              server.close();
            });
          }
        );

        cartReq.on('error', (error) => {
          console.error(error);
          server.close();
          process.exitCode = 1;
        });

        cartReq.end();
      });
    }
  );

  req.on('error', (error) => {
    console.error(error);
    server.close();
    process.exitCode = 1;
  });

  req.write('productId=1');
  req.end();
});
