import path from "node:path";
import { fileURLToPath } from "node:url";
import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import multer from "multer";
import { proxyJson, proxyMultipartGenerate } from "./pythonProxy.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");

dotenv.config({ path: path.join(repoRoot, ".env") });
dotenv.config();

const PORT = Number(process.env.PORT || 3001);
const DATA_DIR = path.resolve(repoRoot, process.env.DATA_DIR || "data");
const artifactsDir = path.join(DATA_DIR, "artifacts");

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 15 * 1024 * 1024 },
});

const app = express();

app.use(
  cors({
    origin: ["http://127.0.0.1:5173", "http://localhost:5173"],
  })
);

app.get("/api/health", (req, res) => proxyJson(req, res, { pathOverride: "/health" }));

app.get("/api/trends", (req, res) => proxyJson(req, res));
app.get("/api/trends/:id", (req, res) => proxyJson(req, res));
app.post("/api/trends/refresh", (req, res) => proxyJson(req, res, { method: "POST", body: null }));
app.post("/api/trends/:id/build-preset", (req, res) =>
  proxyJson(req, res, { method: "POST", body: null })
);

app.get("/api/presets", (req, res) => proxyJson(req, res));
app.get("/api/presets/:id", (req, res) => proxyJson(req, res));

app.post("/api/generate", (req, res) => {
  upload.single("face")(req, res, (err) => {
    if (err) {
      const detail = err instanceof Error ? err.message : String(err);
      res.status(400).json({ error: "upload_failed", detail });
      return;
    }
    void proxyMultipartGenerate(req, res);
  });
});

app.get("/api/jobs/:id", (req, res) => proxyJson(req, res));

/** Matches shared contract GET /artifacts/{name} (filename under data/artifacts/). */
app.get("/api/artifacts/:name", (req, res) => {
  const name = req.params.name || "";
  if (!name || name.includes("..") || name.includes("/") || name.includes("\\")) {
    res.status(400).json({ error: "invalid_path" });
    return;
  }
  const filePath = path.join(artifactsDir, name);
  if (!filePath.startsWith(artifactsDir)) {
    res.status(400).json({ error: "invalid_path" });
    return;
  }
  res.sendFile(filePath, (err) => {
    if (err) {
      res.status(404).json({ error: "artifact_not_found", detail: name });
    }
  });
});

app.use((_req, res) => {
  res.status(404).json({ error: "not_found" });
});

app.listen(PORT, () => {
  console.log(`[node-api] listening on http://127.0.0.1:${PORT}`);
  console.log(`[node-api] PYTHON_BASE_URL=${process.env.PYTHON_BASE_URL || "http://127.0.0.1:8000"}`);
  console.log(`[node-api] artifacts=${artifactsDir}`);
});
