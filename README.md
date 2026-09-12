# Multimodal Document Intelligence with Agentic RAG

Sistem kecerdasan dokumen multimodal yang dirancang untuk membantu staf finance dan operations memproses invoice dalam format PDF (digital native & scan) dan gambar (JPG/PNG). Sistem mengintegrasikan OCR berbasis layout (PaddleOCR PP-StructureV3), ekstraksi data terstruktur ke skema JSON tervalidasi, grounded Document RAG, dan alur agen cerdas (LangGraph) untuk verifikasi sitasi halaman serta potongan bukti dokumen.

---

## Status Project

> [!IMPORTANT]
> **Status: MVP complete — Stage 1–14 verified**
> Pipeline produk, quality gates, benchmark sintetis, fresh container startup, dan pengiriman trace eksternal sudah diverifikasi. Batas dataset kecil tetap dicatat agar hasil portfolio tidak dilebih-lebihkan.

### Yang sudah diverifikasi

- UI upload untuk PDF/JPG/PNG dengan batas awal 15 MB.
- API `POST /api/v1/documents` dan status dokumen.
- Validasi streaming, magic bytes, kecocokan ekstensi, isi file, batas 10 halaman, dan batas resolusi gambar.
- Penyimpanan menggunakan nama UUID; lokasi internal file tidak dikirim pada respons publik.
- SQLAlchemy model dan migration Alembic awal untuk tabel `documents`.
- Ekstraksi teks native PDF dan rendering fallback 300 DPI untuk halaman scan.
- Adapter lazy PaddleOCR PP-StructureV3 beserta penyimpanan teks, confidence, blok, layout, dan tabel per halaman.
- Structured extraction melalui baseline heuristik transparan atau Muse Spark melalui OpenCode, dengan skema Pydantic, evidence per field, dan pemeriksaan `subtotal + tax == total`.
- API process/pages/extraction dan UI ringkasan hasil invoice.
- Recursive page/table-aware chunking menggunakan LangChain text splitters.
- PostgreSQL full-text retrieval dengan GIN index, relevance score, fallback lexical portabel, dan isolasi wajib `document_id`.
- LangGraph workflow terbatas: query rewrite, retrieval, Muse Spark reranking, sufficiency gate, generation, verifikasi sitasi, maksimal dua attempt, lalu abstain aman.
- Audit menyimpan retrieval score, rerank score, final relevance, citation support score, error verifikasi, latency, dan node trace.
- UI tanya jawab, verified citations, score breakdown, serta halaman audit `/audit/{document_id}`.
- Evaluation batch dengan citation match, ID-ranked context precision, Hit@K, abstention correctness, latency gate, serta Muse LLM-as-judge untuk faithfulness dan answer correctness opsional.
- Structured trace event, trace ID per RAG run, latency setiap node, JSONL audit log teredaksi, dan exporter Langfuse SDK v4 yang tidak memblokir pipeline ketika dinonaktifkan/down.
- Frontend lint, TypeScript type-check, dan production build.
- Kontrak OpenAPI dan schema invoice ter-versioning serta diperiksa otomatis terhadap drift.
- Backend Ruff, MyPy, 32 automated tests (termasuk PostgreSQL integration test), dan migration PostgreSQL sampai `20260912_0005 (head)`.
- Baseline sintetis nyata pada PostgreSQL: field exact accuracy, mathematical validation, Hit@1/3/5, context precision, citation page accuracy, dan citation support semuanya `1.0` pada 1 invoice/3 query. Clean-scan PaddleOCR di GitHub Actions memperoleh CER/WER `0.0` dan confidence `0.9781` pada 1 sampel. Keduanya regression smoke kecil, bukan klaim performa produksi.
- RAG live smoke menghasilkan jawaban dengan dua sitasi terverifikasi dan trace `5f418ed12891492ea398fd08a1d47750`; trace yang sama dibaca kembali dari server Langfuse dengan satu observation.

### Batas verifikasi saat ini

- PostgreSQL development khusus project berjalan pada port lokal `55432`; `.env` lokal tidak dilacak Git. Engine Docker lokal tidak aktif, tetapi fresh Compose build, migration, API health, dan web health sudah lulus di CI run `34703835790`.
- Extra PaddleOCR, import, dan smoke inference PP-StructureV3 sudah diverifikasi. Cloud benchmark clean-scan lulus pada run `34704232528` dengan cold-run sekitar 58 detik; noisy dataset dan p95 belum tersedia.
- PaddlePaddle 3.3.1 CPU mengalami regresi oneDNN/PIR pada environment ini. Adapter menonaktifkan MKL-DNN dan modul formula/chart/seal yang tidak diperlukan invoice; inferensi kemudian berhasil.
- Jawaban RAG membutuhkan `opencode serve` dan akses internet. Muse Spark berjalan online; tidak ada model LLM/embedding yang dimuat di laptop.
- Teks pertanyaan dan chunk relevan dikirim ke provider OpenCode, sehingga dokumen sensitif memerlukan persetujuan pengguna dan pemeriksaan kebijakan provider.
- Baseline heuristik belum mengekstrak line item kompleks; gunakan backend OpenCode untuk layout invoice yang bervariasi.
- Token/cost tetap `not reported` jika provider OpenCode tidak mengirim metadata usage; sistem tidak mengarang nilainya.
- Ragas `0.4.3` tidak dipakai pada runtime karena konflik aktual dengan `langchain-community 0.4.2`; metrik deterministik dihitung internal dan semantic judge memakai Muse/OpenCode. Hasil baseline kecil ada di `docs/BASELINE_RESULTS.md`; benchmark 50+ invoice dan OCR noisy tetap belum diukur.
- Ekspor Langfuse default nonaktif pada konfigurasi contoh, tetapi live smoke telah berhasil memakai konfigurasi `.env` lokal. Audit database dan JSONL tetap aktif saat Langfuse dimatikan atau gagal.

---

## Ruang Lingkup Produk

- **Validasi Berkas Ketat:** Pemeriksaan magic bytes, pembatasan ukuran berkas (maksimal 15 MB), dan batasan dokumen maksimal 10 halaman per sesi.
- **Dual-Path Text Extraction:** Jalur ekstraksi cepat native PDF dengan fallback otomatis ke PaddleOCR PP-StructureV3 untuk dokumen hasil scan dan gambar.
- **Ekstraksi Invoice Terstruktur:** Pemetaan data faktur ke skema Pydantic terstandarisasi lengkap dengan validasi matematika deterministik (subtotal + pajak == total).
- **Grounded Document RAG:** Tanya jawab invoice tunggal menggunakan LangChain chunking, PostgreSQL full-text retrieval, dan Muse Spark melalui OpenCode.
- **Sitasi Terverifikasi (Verifiable Citations):** Penyajian nomor halaman dan potongan teks bukti asli dokumen untuk setiap klaim jawaban.
- **Agentic Workflow dengan LangGraph:** State machine untuk penulisan ulang kueri (query rewrite), retrieval ulang saat konteks tidak mencukupi, dan verifikasi sitasi otomatis.
- **Observabilitas Fail-Safe:** Trace ID, latency node, audit PostgreSQL/JSONL teredaksi, dan ekspor opsional ke Langfuse; token/cost hanya dicatat bila provider melaporkannya.
- **Pipeline Evaluasi Ganda:** Pengujian performa komprehensif memisahkan metrik deterministik (CER, WER, Hit@K, Exact Match) dan metrik LLM-as-judge (Faithfulness, Answer Correctness).

---

## Struktur Repository

```
multimodal-document-intelligence/
├── apps/
│   └── web/                   # Frontend Web Application (Next.js & TypeScript)
├── services/
│   └── api/
│       ├── app/
│       │   ├── core/          # Konfigurasi, middleware, & penanganan exception
│       │   ├── db/            # Koneksi database & session PostgreSQL
│       │   ├── documents/     # Domain entitas & siklus hidup dokumen
│       │   ├── ingestion/     # Validasi berkas fisik & dual-path coordinator
│       │   ├── ocr/           # Adapter PaddleOCR PP-StructureV3 & layout parsing
│       │   ├── extraction/    # Skema Pydantic invoice & ekstraksi terstruktur
│       │   ├── retrieval/     # Chunking & PostgreSQL full-text retrieval
│       │   ├── generation/    # Prompt templates & sintesis jawaban bersitasi
│       │   ├── agents/        # LangGraph state machine & verification nodes
│       │   ├── evaluation/    # Metric runners deterministik & Muse judge
│       │   └── observability/ # Redacted audit log & klien Langfuse
│       └── tests/             # Automated test suite (pytest)
├── contracts/                 # Skema kontrak API & interface bersama
├── datasets/
│   ├── samples/               # Berkas invoice sampel sintetis / lisensi publik
│   └── ground-truth/          # Golden labels & pasangan QA ground truth
├── storage/                   # Penyimpanan berkas lokal sementara (runtime MVP)
├── infra/
│   └── docker/                # Dockerfile & Docker Compose multi-service
├── scripts/                   # Skrip operasional & utilitas benchmark
├── docs/                      # Dokumentasi teknis & arsitektur proyek
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DATA_FLOW.md
│   ├── EVALUATION_PLAN.md
│   └── SECURITY.md
├── .gitignore                 # Konfigurasi pengecualian version control
└── README.md                  # Ikhtisar proyek & indeks dokumentasi
```

---

## Dokumentasi Arsitektur

Spesifikasi teknis lengkap telah didokumentasikan secara terperinci dalam berkas-berkas berikut:

1. [docs/PRD.md](docs/PRD.md)
   *Product Requirements Document:* Masalah bisnis, target pengguna, batasan ruang lingkup MVP, user flow, functional & non-functional requirements, acceptance criteria, dan risiko utama.
2. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
   *System Architecture:* Tanggung jawab setiap direktori modul, batas frontend-backend, prinsip Clean Architecture, aturan arah ketergantungan, diagram Mermaid, dan alasan pemilihan teknologi.
3. [docs/DATA_FLOW.md](docs/DATA_FLOW.md)
   *Data Flow & Pipeline:* Penjelasan 14 tahap pemrosesan dokumen mulai dari upload hingga audit logging, lengkap dengan input, output, failure modes, dan status data tersimpan.
4. [docs/EVALUATION_PLAN.md](docs/EVALUATION_PLAN.md)
   *Evaluation Plan & Benchmarks:* Definisi metrik deterministik (CER, WER, Hit@K, Citation Accuracy, Latency, Cost) versus LLM-as-judge (Faithfulness, Answer Correctness), tanpa angka pengujian palsu.
5. [docs/SECURITY.md](docs/SECURITY.md)
   *Security Model & Policies:* Kebijakan verifikasi magic bytes, batas ukuran berkas & halaman, pencegahan path traversal, isolasi upload, proteksi indirect prompt injection, dan log data scrubbing.
6. [docs/LANGFUSE_SETUP.md](docs/LANGFUSE_SETUP.md)
   *Observability Setup:* Cara mengaktifkan exporter Langfuse tanpa memasukkan secret ke Git dan batas verifikasi status trace.
7. [docs/BASELINE_RESULTS.md](docs/BASELINE_RESULTS.md)
   *Measured Baseline:* Hasil regression benchmark sintetis yang benar-benar dijalankan.
8. [docs/OCR_BASELINE_RESULTS.md](docs/OCR_BASELINE_RESULTS.md)
   *OCR Baseline:* CER/WER clean-scan dari PaddleOCR aktual yang dijalankan di GitHub Actions.

---

## Menjalankan Fondasi Lokal

Prasyarat: Node.js, pnpm 11, uv, Python 3.12, PostgreSQL 16, dan OpenCode yang sudah login.

```powershell
pnpm install
uv sync --python 3.12 --directory services/api
Copy-Item .env.example .env
Copy-Item apps/web/.env.example apps/web/.env.local
pnpm api:migrate
opencode serve --hostname 127.0.0.1 --port 4096
```

Pada terminal backend:

```powershell
pnpm api:dev
```

Pada terminal kedua:

```powershell
pnpm --filter web dev
```

Default `EXTRACTION_BACKEND=heuristic` berjalan tanpa LLM. Untuk ekstraksi invoice melalui Muse Spark, ubah menjadi `EXTRACTION_BACKEND=opencode`. Agent RAG selalu menggunakan model `opencode/muse-spark-1.3-contributor-free` dari server OpenCode. Semua coding tools dinonaktifkan pada session inference aplikasi.

Alur API Stage 8–14:

```text
POST /api/v1/documents/{id}/index
POST /api/v1/documents/{id}/search
POST /api/v1/documents/{id}/ask
GET  /api/v1/documents/{id}/rag-runs
POST /api/v1/documents/{id}/rag-runs/{run_id}/evaluate
GET  /api/v1/documents/{id}/evaluations
GET  /api/v1/documents/{id}/trace-events
```

Langfuse bersifat opsional. Aktifkan `LANGFUSE_ENABLED=true` dan isi key project serta `LANGFUSE_BASE_URL` pada `.env` lokal. Tanpa konfigurasi tersebut, trace tetap disimpan pada PostgreSQL dan `storage/audit-logs/*.jsonl` dengan email, nomor panjang, token, password, dan secret disensor.

Pemeriksaan project:

```powershell
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm contracts:check
pnpm security:check
pnpm benchmark
```

Fresh container startup (LLM online hanya dibutuhkan ketika endpoint Q&A dipakai):

```powershell
docker compose up --detach --build --wait
```

Compose menjalankan PostgreSQL, migration one-shot, API, dan web secara berurutan dengan healthcheck. Kredensial database default hanya untuk stack development lokal dan dapat diganti melalui environment variable.
