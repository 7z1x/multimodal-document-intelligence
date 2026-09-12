# Product Requirements Document (PRD)

## Project Name
**Multimodal Document Intelligence with Agentic RAG**

## Status
Approved Baseline; Implemented Through Stage 14 Evaluation and Observability

---

## 1. Problem Statement & Target Users

### 1.1 Masalah Bisnis
Staf finance, operations, dan procurement menghabiskan waktu signifikan setiap hari untuk memproses faktur/invoice vendor. Sebagian besar invoice diterima dalam format tidak terstruktur: PDF digital native, PDF hasil scan berkualitas rendah, atau foto/gambar scan (JPG/PNG).

Tantangan utama yang dihadapi:
- **Beban Kerja Manual & Lambat (Hipotesis Masalah):** Pemrosesan manual dapat memerlukan waktu dan rentan kesalahan; dampak aktual belum diukur melalui user research.
- **Tingginya Risiko Human Error:** Kesalahan membaca angka nol, salah memetakan baris tabel multi-halaman, atau salah mengenali mata uang dapat menyebabkan keterlambatan pembayaran dan kesalahan pembukuan.
- **Sulitnya Verifikasi & Tanya Jawab:** Saat staf finance perlu memverifikasi klausul pembayaran, syarat termin (payment terms), atau perbandingan biaya tertentu, mereka harus membaca ulang seluruh halaman secara manual.
- **Krisis Kepercayaan pada AI Tradisional (Hallucination):** Solusi LLM umum sering menghasilkan jawaban yang meyakinkan tetapi salah (halusinasi), tanpa sitasi halaman atau bukti potongan teks yang dapat diverifikasi langsung oleh manusia.

### 1.2 Target Pengguna
- **Finance & Accounts Payable (AP) Specialists:** Memverifikasi kesesuaian nilai invoice, tanggal jatuh tempo, dan rincian pajak sebelum proses pembayaran.
- **Operations & Procurement Officers:** Memeriksa kesesuaian unit barang, deskripsi spesifikasi, dan diskon yang disepakati dengan vendor.
- **Internal Audit & Compliance:** Menelusuri bukti dokumen asli melalui sitasi halaman dan potongan teks asli tanpa membuka arsip fisik secara manual.

---

## 2. Batas Ruang Lingkup MVP (Minimum Viable Product Scope)

Untuk memastikan pengiriman yang terarah, stabil, dan dapat diuji secara terukur, batas ruang lingkup MVP ditetapkan secara ketat:

### 2.1 Scope yang Didukung
- **Satu Dokumen per Sesi:** Pemrosesan dan analisis difokuskan pada 1 dokumen invoice dalam satu waktu. Tidak mendukung penggabungan analisis lintas-dokumen secara bersamaan pada MVP.
- **Format Berkas:** PDF (digital native & scanned PDF), JPG, dan PNG.
- **Batas Halaman:** Maksimal 10 halaman per dokumen. Dokumen di atas 10 halaman ditolak pada tahap validasi.
- **Batas Ukuran Berkas:** Maksimal 15 MB per dokumen.
- **Fokus Dokumen Tunggal:** Eksklusif untuk dokumen jenis **Invoice / Faktur Komersial / Faktur Pajak**.
- **Dataset Sintetis & Aman:** Hanya menggunakan dokumen sintetis atau dokumen sampel berlisensi publik yang bebas dari data pribadi (PII) atau rahasia finansial perusahaan nyata.
- **Penyimpanan Lokal:** File upload dan artefak pemrosesan disimpan pada direktori lokal host/container selama tahap MVP.

### 2.2 Non-Goals (Di Luar Ruang Lingkup MVP)
- **Multi-Document Comparison:** Tidak mendukung perbandingan otomatis antara invoice dengan Purchase Order (PO) atau Good Receipt (GR) 3-way matching pada tahap ini.
- **Dokumen Non-Invoice:** Tidak mendukung dokumen legal panjang (kontrak perjanjian ratusan halaman), slip gaji, struk kasir termal (thermal receipts), bank statement, atau dokumen tulisan tangan penuh.
- **Integrasi ERP Langsung:** Tidak ada integrasi dua arah langsung ke sistem ERP seperti SAP, Oracle NetSuite, Xero, atau QuickBooks pada MVP.
- **Multi-Tenant User Management & RBAC:** Tidak menyediakan sistem hierarki organisasi, billing pelanggan SaaS, atau izin akses bertingkat pada MVP.
- **Cloud Distributed Storage / Managed Search:** Tidak mengandalkan S3 atau managed search/vector service berbayar; file dan indeks retrieval MVP memakai storage lokal serta PostgreSQL.
- **Model Fine-Tuning:** Tidak melakukan fine-tuning model LLM atau OCR; seluruh ekstraksi mengandalkan pre-trained weights dan zero/few-shot schema prompting.

---

## 3. Fitur Utama & Non-Goals

### 3.1 Fitur Utama (MVP Capabilities)
1. **Document Ingestion & Validation:** Validasi berkas berbasis MIME type dan magic bytes (mencegah manipulasi ekstensi palsu), pengecekan batas ukuran (maksimal 15 MB), dan pembatasan jumlah halaman (maksimal 10 halaman).
2. **Dual-Path Text Extraction:** Jalur ekstraksi teks terstandarisasi:
   - Menggunakan `pypdf` untuk inspeksi metadata berkas dan ekstraksi teks dasar pada dokumen PDF digital.
   - Menggunakan `pypdfium2` untuk merender halaman PDF menjadi gambar beresolusi tinggi ketika OCR dibutuhkan.
   - Menggunakan `PaddleOCR PP-StructureV3` untuk deteksi layout, pemisahan tabel, dan pengenalan teks optik pada dokumen hasil scan atau gambar (JPG/PNG).
   - Catatan lingkup: Pustaka pihak ketiga seperti Docling tidak dimasukkan ke dalam ruang lingkup MVP.
3. **Structured Invoice Extraction:** Mengurai konten teks/tabel hasil ekstraksi ke dalam format JSON terstruktur yang divalidasi oleh skema Pydantic (Nomor Invoice, Tanggal, Vendor, Pembeli, Rincian Line Items, Pajak, Subtotal, dan Total).
4. **Grounded Document RAG:** Tanya jawab invoice tunggal menggunakan LangChain chunking, PostgreSQL full-text retrieval, dan filter wajib `document_id`.
5. **Verifiable Citations:** Setiap jawaban Q&A wajib menyertakan sitasi halaman dan potongan kutipan teks asli (bounding box / text snippet) agar staf finance dapat langsung memverifikasi kebenaran jawaban pada dokumen asli.
6. **Agentic Workflow (LangGraph):** Workflow agen terbatas dengan state machine yang mencakup:
   - Query rewrite untuk memperjelas istilah akuntansi/finance.
   - Retrieval ulang bersyarat jika dokumen yang ditarik tidak relevan atau tidak memadai.
   - Evaluasi verifikasi sitasi sebelum jawaban diserahkan kepada pengguna.
7. **Observability & Audit Trail:** Trace ID, latency dan status node disimpan secara internal; Langfuse self-hosted adalah exporter opsional. Token/cost hanya dicatat ketika metadata usage tersedia dari provider.
8. **Evaluation Framework:** Pipeline pengujian komprehensif yang membedakan secara tegas antara metrik deterministik (string exact match, CER/WER, kalkulasi numerik) dan metrik LLM-as-judge (faithfulness, answer correctness).

---

## 4. User Flow

```
[User Mengunggah Dokumen (PDF/JPG/PNG)]
                  │
                  ▼
   [Validasi File: Magic Bytes, Ukuran, Halaman]
                  │
          Lolos? ─┼─ Tidak ──> [Tampilkan Pesan Error Validasi]
                  │
                  ▼ Ya
     [Penyimpanan File ke Storage Lokal]
                  │
                  ▼
  [Dual-Path Extraction: Native Text vs PaddleOCR PP-StructureV3]
                  │
                  ▼
       [Parsing Layout & Tabel Dokumen]
                  │
                  ▼
  [Structured Extraction ke Skema JSON (Pydantic)]
                  │
                  ▼
  [Chunking Halaman/Tabel + PostgreSQL Full-Text Index]
                  │
                  ▼
[Tampilan Dashboard: Ringkasan Invoice & Pratinjau Dokumen]
                  │
                  ▼
      [User Mengajukan Pertanyaan Finansial]
                  │
                  ▼
  [Agentic Loop: Query Rewrite -> Retrieval -> Generation]
                  │
                  ▼
       [Verifikasi Sitasi Bukti Dokumen]
                  │
        Valid? ───┼─ Tidak ──> [Self-Correction / Re-retrieval / Abstain]
                  │
                  ▼ Ya
[Sajikan Jawaban Bersama Sitasi Halaman & Snippet Bukti]
```

### Langkah Interaksi Pengguna:
1. **Upload Dokumen:** Pengguna menyerahkan satu berkas invoice melalui drag-and-drop di web UI.
2. **Validasi & Status Pemrosesan:** Web UI menampilkan status pemrosesan secara near-real-time status via polling (frontend secara berkala melakukan polling HTTP ke endpoint status dengan interval yang dapat dikonfigurasi; WebSocket tidak digunakan pada MVP).
3. **Review Hasil Ekstraksi:** Pengguna melihat form ringkasan invoice terstruktur berdampingan dengan preview dokumen asli. Jika ada field yang ragu atau bernilai kosong, pengguna mendapatkan penanda visual.
4. **Tanya Jawab Dokumen (Q&A):** Pengguna mengetikkan pertanyaan bebas mengenai invoice (contoh: "Berapa persen tarif PPN yang dikenakan dan apa syarat pembayarannya?").
5. **Verifikasi Bukti:** Pengguna menerima jawaban disertai chip sitasi (misal: `[Hal 2: "Syarat Pembayaran: Net 30 hari"]`). Mengklik chip sitasi akan mengarahkan preview dokumen ke halaman dan paragraf terkait.

---

## 5. Functional Requirements

| ID | Modul | Deskripsi Kebutuhan Fungsional |
|---|---|---|
| **FR-01** | Ingestion | Sistem harus memvalidasi magic bytes berkas untuk memastikan berkas adalah PDF, JPG, atau PNG valid sebelum diproses. |
| **FR-02** | Ingestion | Sistem harus menolak dokumen yang memiliki lebih dari 10 halaman atau ukuran berkas lebih dari 15 MB dengan pesan error informatif. |
| **FR-03** | Ingestion | Sistem harus menyimpan berkas yang lolos validasi ke penyimpanan lokal dengan nama berkas acak (UUIDv4) untuk mencegah penimpaan berkas. |
| **FR-04** | Ingestion / OCR | Sistem harus mengekstrak teks native dari PDF menggunakan pypdf terlebih dahulu, dan merender halaman via pypdfium2 untuk diproses oleh PaddleOCR PP-StructureV3 jika dokumen berupa gambar atau teks sparse (scanned). Pustaka Docling tidak digunakan pada MVP. |
| **FR-05** | OCR / Layout | Sistem harus mengekstrak struktur tabel invoice (baris, kolom, header, sel) menggunakan kemampuan layout PP-StructureV3. |
| **FR-06** | Extraction | Sistem harus mengekstrak informasi invoice ke dalam skema Pydantic standar: nomor invoice, tanggal invoice, tanggal jatuh tempo, identitas vendor, identitas pembeli, item baris (kuantitas, deskripsi, harga satuan, total baris), subtotal, pajak, dan total akhir. |
| **FR-07** | Extraction | Sistem harus menjalankan validasi kalkulasi matematis dasar secara deterministik: subtotal + total pajak = total tagihan (dengan toleransi pembulatan mata uang). |
| **FR-08** | Retrieval | Sistem harus memecah dokumen menjadi chunk berbasis halaman/tabel dan mengindeks kontennya dengan PostgreSQL GIN full-text index beserta `document_id` dan `page_number`. |
| **FR-09** | Agent / RAG | Sistem harus menyediakan alur tanya jawab berbasis LangGraph yang mencakup: query rewriting, penarikan dokumen terindeks, dan verifikasi kecukupan konteks. |
| **FR-10** | Generation | Sistem harus menghasilkan jawaban yang menyertakan sitasi eksplisit berupa nomor halaman dan potongan kutipan teks pendukung dari dokumen asli. |
| **FR-11** | Generation | Sistem harus melakukan abstention (menjawab "Informasi tidak ditemukan dalam dokumen") jika konteks yang ditarik tidak memuat jawaban yang ditanyakan, alih-alih mengarang jawaban. |
| **FR-12** | Observability| Sistem harus mengirimkan log trace setiap pemanggilan LLM, retrieval, dan node agent ke instance Langfuse self-hosted. |

---

## 6. Non-Functional Requirements

### 6.1 Performa & Latensi (NFR-01)

> [!NOTE]
> Seluruh target latensi di bawah ini merupakan **initial engineering target — provisional, subject to baseline measurement**. Angka-angka ini **bukan hasil aktual**, **bukan klaim performa**, dan akan ditinjau ulang setelah baseline resmi dijalankan pada hardware serta dataset nyata.

| Komponen Alur | Measured Result | Provisional Target (initial engineering target — provisional, subject to baseline measurement) | Final Acceptance Threshold |
|---|---|---|---|
| **Ekstraksi Dokumen Native (1-3 Halaman)** | not measured | <= 8 detik | <= 12 detik |
| **Ekstraksi Dokumen Scan/OCR (CPU Mode, 1 Halaman)** | not measured | <= 20 detik | <= 30 detik |
| **Ekstraksi Dokumen Scan/OCR (GPU Accelerated, 1 Halaman)** | not measured | <= 5 detik | <= 8 detik |
| **Latensi Tanya Jawab (RAG Q&A First Token / Response)** | not measured | <= 4 detik | <= 6 detik |

### 6.2 Determinisme & Akurasi (NFR-02)
- Seluruh validasi field numerik (perhitungan total, pajak, dan tanggal) harus diperiksa menggunakan fungsi logika deterministik murni, bukan semata-mata mengandalkan estimasi LLM.
- Format tanggal harus dinormalisasi secara deterministik ke standar ISO-8601 (`YYYY-MM-DD`).

### 6.3 Keamanan Dokumen & Privasi (NFR-03)
- Direktori penyimpanan dokumen fisik harus terisolasi di luar root publik web server.
- Sistem harus menolak percobaan path traversal pada parameter berkas.
- Sistem wajib menyaring (redact) informasi sensitif pribadi sebelum menulis log audit sistem.
- Teks dari dokumen yang diproses harus diperlakukan sebagai data yang tidak terpercaya (untrusted data) untuk mencegah serangan indirect prompt injection.

### 6.4 Keandalan & Robustness (NFR-04)
- Jika proses OCR gagal pada halaman tertentu, sistem harus mencatat error per halaman dan tetap memproses halaman lainnya yang berhasil tanpa membuat seluruh pipeline crash.
- Sistem harus mengembalikan kode status HTTP standar (400, 422, 500) dengan payload JSON terstruktur saat terjadi kesalahan.

### 6.5 Maintainability & Clean Architecture (NFR-05)
- Modul logika bisnis (domain) tidak boleh bergantung pada framework HTTP (FastAPI route handler atau Request object).
- Seluruh kontrak skema data antara API dan frontend harus didefinisikan secara deklaratif menggunakan TypeScript interfaces dan Pydantic models yang selaras.

---

## 7. Acceptance Criteria

Setiap fitur dalam ruang lingkup MVP dianggap diterima apabila memenuhi kriteria berikut:

1. **AC-01 (Validasi Upload):**
   - Mengunggah file PDF/JPG/PNG asli valid <= 10 halaman menghasilkan status HTTP 200/201 dan dokumen tersimpan.
   - Mengunggah file executable (.exe) yang diganti namanya menjadi .pdf ditolak oleh validator magic bytes dengan status HTTP 400.
   - Mengunggah file PDF 11 halaman ditolak dengan pesan error batasan halaman dengan status HTTP 422.
2. **AC-02 (Ekstraksi Invoice Terstruktur):**
   - Dokumen sampel invoice standar berhasil diekstrak menjadi objek JSON yang memenuhi skema Pydantic tanpa error validasi tipe data.
   - Perhitungan total invoice diverifikasi secara deterministik terhadap daftar line items dan pajak.
3. **AC-03 (Tanya Jawab & Grounded Citations):**
   - Pengguna mengajukan pertanyaan mengenai item pada invoice, sistem menjawab dengan benar dan menyertakan nomor halaman serta teks kutipan yang ada pada dokumen tersebut.
   - Jika pengguna menanyakan data yang tidak tercantum dalam invoice (contoh: "Siapa nama anjing peliharaan vendor?"), sistem wajib menolak menjawab (abstain) dan menyatakan data tidak tersedia.
4. **AC-04 (Tracing & Observability):**
   - Setiap sesi Q&A menghasilkan trace internal dan audit JSONL teredaksi. Jika Langfuse dikonfigurasi, trace agent dikirim ke dashboard; token/cost boleh kosong ketika provider tidak melaporkannya.

---

## 8. Risiko Utama & Strategi Mitigasi

| Risiko | Dampak | Probabilitas | Strategi Mitigasi |
|---|---|---|---|
| **Variasi Layout Invoice Sangat Tinggi** | Ekstraksi field tabel menjadi berantakan atau kolom tertukar. | Tinggi | Gunakan PP-StructureV3 untuk memisahkan tabel sebelum ekstraksi teks; validasi hasil via Pydantic validator bertingkat. |
| **Beban Komputasi OCR pada CPU** | Latensi pemrosesan tinggi bila dijalankan di server tanpa GPU. | Tinggi | Implementasikan dual-path extraction (utamakan parser native PDF); jalankan proses OCR secara async/background task jika diperlukan. |
| **Indirect Prompt Injection dari Dokumen** | Dokumen jahat memuat teks instruksi tersembunyi yang membajak LLM. | Sedang | Pisahkan instruksi sistem dari teks dokumen menggunakan pembatas (delimiters) yang ketat; tegaskan bahwa teks dokumen hanya boleh diperlakukan sebagai data pasif. |
| **Sitasi Melenceng (Citation Drift)** | Sitasi mengarahkan ke halaman atau potongan teks yang salah. | Sedang | Tambahkan node verifikasi sitasi deterministik pada LangGraph untuk memeriksa keberadaan string kutipan di halaman rujukan sebelum menyajikan jawaban. |
| **Halusinasi Nilai Angka Finansial** | Kesalahan nominal angka fatal bagi staf akuntansi. | Sedang | Terapkan aturan deterministik: jika field numerik hasil ekstraksi tidak lolos uji penjumlahan matematika, beri tanda status `unverified/warning` pada UI. |

---

## 9. Definition of Done (DoD)

Tahap pengembangan MVP dianggap selesai (Done) hanya jika:
- [x] Seluruh skema contracts (Pydantic models) terdokumentasi dan divalidasi oleh automated unit tests.
- [x] Seluruh unit tests dan integration tests pada `services/api/tests/` berhasil lolos (100% pass) menggunakan pytest.
- [x] Regression gate deterministik pada dataset sintetis mencapai target untuk clean-scan CER/WER, native field extraction, Hit@K, context precision, serta citation support. Dataset produksi/noisy tetap batas evaluasi lanjutan, bukan klaim MVP ini.
- [ ] Trace eksekusi berhasil terkirim dan terlihat pada instance Langfuse self-hosted tanpa error koneksi.
- [x] Automated repository scan tidak menemukan secret aktual atau path absolut lokal di dalam basis kode. Kredensial Compose default adalah development-only, bukan production secret.
- [x] Automated repository scan membatasi dokumen commit hanya ke dataset sintetis berlisensi CC0.
- [x] Konfigurasi Docker Compose berhasil dibangun dari nol di CI; migration, health API, dan health web lulus pada run `34703835790`.
