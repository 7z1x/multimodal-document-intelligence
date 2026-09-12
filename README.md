# Multimodal Document Intelligence with Agentic RAG

Sistem kecerdasan dokumen multimodal yang dirancang untuk membantu staf finance dan operations memproses invoice dalam format PDF (digital native & scan) dan gambar (JPG/PNG). Sistem mengintegrasikan OCR berbasis layout (PaddleOCR PP-StructureV3), ekstraksi data terstruktur ke skema JSON tervalidasi, grounded Document RAG, dan alur agen cerdas (LangGraph) untuk verifikasi sitasi halaman serta potongan bukti dokumen.

---

## Status Project

> [!IMPORTANT]
> **Status: Stage 12 — Reranked, Grounded, and Citation-Verified RAG**
> Intake, parsing/OCR, structured extraction, full-text retrieval, Muse Spark reranking/generation, bounded LangGraph agent, deterministic citation verification, audit persistence, API, dan UI sudah diimplementasikan. Evaluation runtime dan observability Langfuse masih tahap berikutnya.

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
- Frontend lint, TypeScript type-check, dan production build.
- Backend Ruff, MyPy, 22 automated tests, dan migration SQL preview.

### Batas verifikasi saat ini

- PostgreSQL terdeteksi pada port lokal 5432, tetapi migration project belum diterapkan karena kredensial development `mdi` belum tersedia (`InvalidPasswordError`). Docker Desktop/Compose juga tidak tersedia pada environment pemeriksaan.
- Extra PaddleOCR, import, dan smoke inference PP-StructureV3 sudah diverifikasi pada CPU Windows: 5 blok teks terbaca dengan confidence rata-rata `0.9882` pada invoice sintetis. Cold start setelah model tercache sekitar 75 detik; benchmark dataset/p95 belum tersedia.
- PaddlePaddle 3.3.1 CPU mengalami regresi oneDNN/PIR pada environment ini. Adapter menonaktifkan MKL-DNN dan modul formula/chart/seal yang tidak diperlukan invoice; inferensi kemudian berhasil.
- Jawaban RAG membutuhkan `opencode serve` dan akses internet. Muse Spark berjalan online; tidak ada model LLM/embedding yang dimuat di laptop.
- Teks pertanyaan dan chunk relevan dikirim ke provider OpenCode, sehingga dokumen sensitif memerlukan persetujuan pengguna dan pemeriksaan kebijakan provider.
- Baseline heuristik belum mengekstrak line item kompleks; gunakan backend OpenCode untuk layout invoice yang bervariasi.
- Live PostgreSQL belum diuji karena kredensial development lokal masih ditolak; migration SQL dan query contract tersedia.
- Evaluation runtime, Ragas benchmark, dan Langfuse belum diimplementasikan.

---

## Ruang Lingkup Produk

- **Validasi Berkas Ketat:** Pemeriksaan magic bytes, pembatasan ukuran berkas (maksimal 15 MB), dan batasan dokumen maksimal 10 halaman per sesi.
- **Dual-Path Text Extraction:** Jalur ekstraksi cepat native PDF dengan fallback otomatis ke PaddleOCR PP-StructureV3 untuk dokumen hasil scan dan gambar.
- **Ekstraksi Invoice Terstruktur:** Pemetaan data faktur ke skema Pydantic terstandarisasi lengkap dengan validasi matematika deterministik (subtotal + pajak == total).
- **Grounded Document RAG:** Tanya jawab invoice tunggal menggunakan LangChain chunking, PostgreSQL full-text retrieval, dan Muse Spark melalui OpenCode.
- **Sitasi Terverifikasi (Verifiable Citations):** Penyajian nomor halaman dan potongan teks bukti asli dokumen untuk setiap klaim jawaban.
- **Agentic Workflow dengan LangGraph:** State machine untuk penulisan ulang kueri (query rewrite), retrieval ulang saat konteks tidak mencukupi, dan verifikasi sitasi otomatis.
- **Observabilitas Menyeluruh:** Pelacakan latency, jumlah token, dan estimasi biaya per pemanggilan melalui Langfuse self-hosted.
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
│       │   ├── evaluation/    # Metric runners (deterministik & Ragas)
│       │   └── observability/ # Tracing decorator & klien Langfuse
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

Alur API Stage 8–12:

```text
POST /api/v1/documents/{id}/index
POST /api/v1/documents/{id}/search
POST /api/v1/documents/{id}/ask
GET  /api/v1/documents/{id}/rag-runs
```

Pemeriksaan project:

```powershell
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```
