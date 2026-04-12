import { app } from './server.js';

const PORT = Number(process.env.PORT || 8787);

app.listen(PORT, () => {
  console.log(`[server] Listening on http://localhost:${PORT}`);
});
