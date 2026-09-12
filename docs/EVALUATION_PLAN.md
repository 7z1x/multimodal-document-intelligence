# Comprehensive Evaluation Plan & Benchmarks

## Project Name
**Multimodal Document Intelligence with Agentic RAG**

## Status
Stage 13 Runtime Implemented; Full Dataset Baseline Still Not Measured

---

## 1. Filosofi & Prinsip Evaluasi

Evaluasi pada sistem AI ekstraksi dokumen dan RAG tidak boleh diperlakukan sebagai opini subjektif atau skor hitam-putih tunggal. Sistem ini memproses dokumen finansial di mana kesalahan angka atau halusinasi terminologi dapat berakibat fatal.

> [!IMPORTANT]
> **Pernyataan Penafian Target Evaluasi (Provisional Target Disclaimer):**
> Seluruh nilai numerik untuk akurasi, latensi, penggunaan token, dan estimasi biaya yang dicantumkan dalam dokumen ini berstatus:
> **"initial engineering target — provisional, subject to baseline measurement"**
> Angka-angka ini:
> 1. **Bukan hasil aktual** dari pengujian yang telah selesai.
> 2. **Bukan klaim performa** dari sistem yang berjalan.
> 3. **Akan ditinjau ulang** setelah pengujian baseline resmi dijalankan pada konfigurasi hardware dan dataset nyata.
>
> Dokumen ini secara tegas memisahkan tiga status data metrik:
> - **Measured Result:** Hasil pengujian aktual pada sistem berjalan (saat ini berstatus **not measured** atau kosong).
> - **Provisional Target:** Target rancangan rekayasa awal (*initial engineering target — provisional, subject to baseline measurement*).
> - **Final Acceptance Threshold:** Ambang batas minimal yang wajib dipenuhi sistem sebelum dinyatakan layak rilis (passing gate).

Prinsip dasar evaluasi yang diterapkan:
1. **Pemisahan Tegas antara Metrik Deterministik dan LLM-as-Judge:**
   - Metrik deterministik dihitung dengan algoritma matematika pasti (string matching, edit distance, perbandingan angka, pengukuran waktu sistem).
   - Metrik LLM-as-judge digunakan hanya untuk kualitas semantik naratif (kepatuhan klaim fakta dan kemiripan makna).
2. **Larangan Menyebut Skor sebagai "Probability of Truth":**
   - Skor dari model LLM-as-judge (skala 0.0 hingga 1.0) adalah indikator kepatuhan heuristik terhadap prompt evaluasi, **BUKAN** probabilitas kebenaran objektif di dunia nyata.
3. **Bebas dari Angka Evaluasi Palsu (Zero Fabricated Data):**
   - Kolom hasil aktual (*measured result*) wajib tetap bernilai **not measured** hingga benchmark baseline sungguhan dieksekusi.

---

## 2. Dataset Ground Truth

Evaluasi benchmark dilakukan terhadap dataset terstandarisasi yang disimpan di `datasets/ground-truth/`:

### 2.1 Komposisi Dataset
- **Sumber Dokumen:** Dokumen invoice sintetis (dibuat menggunakan generator dokumen otomatis) dan invoice berlisensi publik bebas royalti (seperti DocVQA/FUNSD subsets atau invoice template open-source).
- **Keamanan & Privasi:** 100% bebas dari data identitas pribadi (PII) nyata, nomor rekening bank asli, atau nama perusahaan rahasia.
- **Variasi Format:**
  - Kategori A (Digital Native PDF): Dokumen digital sempurna dengan teks vektor.
  - Kategori B (Scanned Clean): Dokumen dipindai dengan resolusi 300 DPI tegak lurus.
  - Kategori C (Scanned Noisy / Skewed): Dokumen dengan rotasi 2-5 derajat, watermark, atau bayangan ringan.
  - Kategori D (Complex Tables): Invoice dengan tabel rincian item multi-halaman atau multi-kolom tanpa garis batas tegas.

### 2.2 Anotasi Golden Ground Truth
Setiap dokumen memiliki berkas anotasi pasangan JSON (`<doc_id>.ground_truth.json`):
- `golden_fields`: Nilai ground-truth untuk seluruh field skema invoice (nomor invoice, tanggal, vendor, buyer, daftar item, subtotal, pajak, total).
- `golden_qa_pairs`: Kumpulan 5-10 pertanyaan per invoice yang mencakup:
  - Pertanyaan langsung (contoh: "Berapa tanggal jatuh tempo invoice ini?").
  - Pertanyaan kalkulatif/agregasi (contoh: "Berapa total harga untuk barang item X?").
  - Pertanyaan terminologi/klausul (contoh: "Apa rekening bank tujuan transfer?").
  - Pertanyaan tidak terjawab / jebakan (contoh: "Siapa nama pengemudi kurir pengiriman?") untuk menguji kemampuan abstention.
- `golden_citations`: Daftar nomor halaman dan teks kutipan persis yang membuktikan jawaban pada pertanyaan di atas.

---

## 3. Definisi Metrik Evaluasi

Setiap metrik memuat tiga tingkatan status: **Measured Result**, **Provisional Target**, dan **Final Acceptance Threshold**.

---

### 3.1 Metrik OCR (Optical Character Recognition)

#### A. Character Error Rate (CER)
- **Tipe:** Deterministik.
- **Tujuan:** Mengukur kesalahan transkripsi karakter pada hasil ekstraksi teks dibandingkan teks ground-truth.
- **Formula (Plain Text):**
  `CER = (Substitutions + Insertions + Deletions) / Total Karakter Referensi`
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):**
    - Dokumen PDF Digital: CER <= 0.01 (Akurasi >= 99%)
    - Dokumen Scanned Clean: CER <= 0.03 (Akurasi >= 97%)
    - Dokumen Scanned Noisy: CER <= 0.08 (Akurasi >= 92%)
  - **Final Acceptance Threshold:**
    - Dokumen PDF Digital: CER <= 0.02
    - Dokumen Scanned Clean: CER <= 0.05
    - Dokumen Scanned Noisy: CER <= 0.12

#### B. Word Error Rate (WER)
- **Tipe:** Deterministik.
- **Tujuan:** Mengukur kesalahan transkripsi pada level kata lengkap.
- **Formula (Plain Text):**
  `WER = (Substitutions + Insertions + Deletions) / Total Kata Referensi`
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):**
    - Dokumen Scanned Clean: WER <= 0.05
    - Dokumen Scanned Noisy: WER <= 0.12
  - **Final Acceptance Threshold:**
    - Dokumen Scanned Clean: WER <= 0.08
    - Dokumen Scanned Noisy: WER <= 0.18

---

### 3.2 Metrik Ekstraksi Field Terstruktur (Field Extraction Accuracy)

#### A. Exact Match (EM) untuk Field Kritis
- **Tipe:** Deterministik.
- **Tujuan:** Memastikan kesesuaian 100% tanpa toleransi untuk identifikasi dokumen.
- **Cakupan Field:** `invoice_number`, `invoice_date` (ISO-8601), `currency`.
- **Formula:**
  `Field_EM = Jumlah Field Cocok Persis / Total Jumlah Field yang Diuji`
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):** Field_EM >= 0.95
  - **Final Acceptance Threshold:** Field_EM >= 0.90

#### B. Normalized Fuzzy Match untuk Entitas Teks
- **Tipe:** Deterministik (Levenshtein Distance dinormalisasi).
- **Tujuan:** Menoleransi variasi kecil seperti spasi ganda atau kapitalisasi pada teks panjang.
- **Cakupan Field:** `vendor_name`, `vendor_address`, `buyer_name`, `item_description`.
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):** Similarity Score >= 0.90
  - **Final Acceptance Threshold:** Similarity Score >= 0.82

#### C. Numeric Tolerance Match untuk Nilai Moneter
- **Tipe:** Deterministik.
- **Tujuan:** Memeriksa kesesuaian nilai finansial dengan toleransi pembulatan nominal mata uang (maksimal selisih 0.01 unit).
- **Cakupan Field:** `subtotal`, `tax_amount`, `total_amount`, `line_items[].unit_price`, `line_items[].line_total`.
- **Formula:**
  `Kondisi Cocok: Absolut(Nilai Prediksi - Nilai Ground Truth) <= 0.01`
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):** Numeric Match Rate >= 0.98
  - **Final Acceptance Threshold:** Numeric Match Rate >= 0.95

---

### 3.3 Metrik Retrieval (Pencarian Konteks Dokumen)

#### A. Retrieval Hit@K (Hit@1, Hit@3, Hit@5)
- **Tipe:** Deterministik.
- **Tujuan:** Mengukur apakah chunk yang memuat jawaban ground-truth berada dalam K peringkat teratas hasil full-text retrieval.
- **Formula:**
  `Hit@K = Jumlah Kueri dengan Potongan Relevan di Top-K / Total Kueri yang Diuji`
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):**
    - Hit@1 >= 0.75
    - Hit@3 >= 0.88
    - Hit@5 >= 0.95
  - **Final Acceptance Threshold:**
    - Hit@1 >= 0.65
    - Hit@3 >= 0.80
    - Hit@5 >= 0.90

#### B. Context Precision & Context Recall
- **Tipe:** Context Precision berbasis ID bersifat deterministik; Context Recall dataset-level masih direncanakan untuk benchmark offline.
- **Context Precision:** Mengukur proporsi informasi relevan yang berada di peringkat paling atas di antara seluruh chunk yang ditarik.
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):** Context Precision >= 0.85
  - **Final Acceptance Threshold:** Context Precision >= 0.75
- **Context Recall:** Mengukur apakah seluruh informasi pendukung dari jawaban emas berhasil terambil oleh retrieval.
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):** Context Recall >= 0.90
  - **Final Acceptance Threshold:** Context Recall >= 0.80

---

### 3.4 Metrik Sitasi & Kejujuran Jawaban (Citation & Groundedness)

#### A. Citation Correctness (Halaman & Bukti Teks)
- **Tipe:** Deterministik.
- **Tujuan:** Menguji apakah penanda sitasi `[Hal X: "Kutipan"]` merujuk pada halaman yang benar dan teks kutipan benar-benar ada dalam dokumen asli (bukan kutipan fiktif).
- **Formula:**
  `Citation Page Accuracy = Jumlah Sitasi dengan Halaman Benar / Total Sitasi Dihasilkan`
  `Citation Text Support = Jumlah Kutipan Teks yang Ditemukan di Halaman Terkait / Total Sitasi`
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):**
    - Citation Page Accuracy >= 0.95
    - Citation Text Support >= 0.92
  - **Final Acceptance Threshold:**
    - Citation Page Accuracy >= 0.88
    - Citation Text Support >= 0.85

#### B. Faithfulness (Muse/OpenCode Structured Judge)
- **Tipe:** LLM-as-judge.
- **Tujuan:** Mengukur apakah semua klaim fakta dalam jawaban yang dihasilkan model didukung langsung oleh konteks yang ditarik (mendeteksi halusinasi).
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):** Faithfulness Score >= 0.90
  - **Final Acceptance Threshold:** Faithfulness Score >= 0.82

#### C. Answer Correctness (Muse/OpenCode Structured Judge)
- **Tipe:** LLM-as-judge.
- **Tujuan:** Menilai akurasi semantik jawaban model dibandingkan dengan jawaban emas ground-truth.
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):** Answer Correctness Score >= 0.88
  - **Final Acceptance Threshold:** Answer Correctness Score >= 0.80

#### D. Abstention Correctness (Kemampuan Menolak Menjawab)
- **Tipe:** Deterministik.
- **Tujuan:** Mengukur ketepatan model untuk menjawab secara eksplisit bahwa informasi tidak ditemukan ketika pertanyaan berada di luar isi dokumen (pertanyaan unanswerable).
- **Formula:**
  `Abstention Accuracy = Jumlah Pertanyaan Luar yang Dijawab 'Tidak Ditemukan' / Total Pertanyaan Luar`
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):** Abstention Accuracy >= 0.95
  - **Final Acceptance Threshold:** Abstention Accuracy >= 0.90

---

### 3.5 Metrik Performa, Biaya & Agen

#### A. Latensi (Response Time)
- **Tipe:** Deterministik (diukur dalam milidetik / detik pada environment benchmark standar).
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):**
    - Validasi File: p95 <= 500 ms
    - Native Text Extraction (PDF digital): p95 <= 2 detik
    - PaddleOCR PP-StructureV3 (CPU mode, 1 halaman): p95 <= 15 detik
    - Ingestion & full-text indexing: p95 <= 3 detik
    - Q&A Retrieval + Reranking: p95 <= 1.5 detik
    - End-to-End Q&A Generation: p95 <= 4 detik
  - **Final Acceptance Threshold:**
    - Validasi File: p95 <= 1000 ms
    - Native Text Extraction (PDF digital): p95 <= 4 detik
    - PaddleOCR PP-StructureV3 (CPU mode, 1 halaman): p95 <= 25 detik
    - Ingestion & full-text indexing: p95 <= 5 detik
    - Q&A Retrieval + Reranking: p95 <= 2.5 detik
    - End-to-End Q&A Generation: p95 <= 6 detik

#### B. Penggunaan Token & Estimasi Biaya
- **Tipe:** Deterministik (dihitung berdasarkan metadata penggunaan API LLM).
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):**
    - Rata-rata Token Masukan per Dokumen: <= 3000 tokens
    - Rata-rata Token Keluaran per Pertanyaan: <= 350 tokens
    - Biaya ekstraksi per invoice 1-3 halaman <= USD 0.03
    - Biaya per kueri tanya jawab <= USD 0.005
  - **Final Acceptance Threshold:**
    - Biaya ekstraksi per invoice 1-3 halaman <= USD 0.06
    - Biaya per kueri tanya jawab <= USD 0.01

#### C. Agent Tool-Selection Accuracy
- **Tipe:** Deterministik.
- **Tujuan:** Mengukur apakah node agen pada LangGraph mengambil rute transisi yang tepat (kapan memicu query rewrite, kapan melakukan retrieval ulang, dan kapan langsung menjawab).
- **Status Metrik:**
  - **Measured Result:** not measured
  - **Provisional Target (initial engineering target — provisional, subject to baseline measurement):** Tool Selection Accuracy >= 0.92
  - **Final Acceptance Threshold:** Tool Selection Accuracy >= 0.85

---

## 4. Matriks Ringkasan Klasifikasi Metrik

| Nama Metrik | Kategori Evaluasi | Metode Pengukuran | Bersifat Deterministik? | Measured Result | Provisional Target (initial engineering target — provisional, subject to baseline measurement) | Final Acceptance Threshold |
|---|---|---|---|---|---|---|
| **Character Error Rate (CER - Digital)** | OCR / Text | Levenshtein Character Distance | Ya (Deterministik) | not measured | CER <= 0.01 | CER <= 0.02 |
| **Character Error Rate (CER - Scan Clean)**| OCR / Text | Levenshtein Character Distance | Ya (Deterministik) | 0.0000 (synthetic n=1) | CER <= 0.03 | CER <= 0.05 |
| **Character Error Rate (CER - Scan Noisy)**| OCR / Text | Levenshtein Character Distance | Ya (Deterministik) | not measured | CER <= 0.08 | CER <= 0.12 |
| **Word Error Rate (WER - Scan Clean)** | OCR / Text | Levenshtein Word Distance | Ya (Deterministik) | 0.0000 (synthetic n=1) | WER <= 0.05 | WER <= 0.08 |
| **Word Error Rate (WER - Scan Noisy)** | OCR / Text | Levenshtein Word Distance | Ya (Deterministik) | not measured | WER <= 0.12 | WER <= 0.18 |
| **Field Exact Match (EM)** | Structured Extraction | String Case-Sensitive Comparison | Ya (Deterministik) | 1.0000 (synthetic n=1) | EM >= 0.95 | EM >= 0.90 |
| **Field Normalized Fuzzy Match** | Structured Extraction | Levenshtein Distance Normalized | Ya (Deterministik) | not measured | Score >= 0.90 | Score >= 0.82 |
| **Numeric Tolerance Match** | Structured Extraction | Absolute Difference (selisih <= 0.01) | Ya (Deterministik) | not measured | Rate >= 0.98 | Rate >= 0.95 |
| **Mathematical Validation** | Structured Extraction | Aturan: Subtotal + Pajak == Total | Ya (Deterministik) | 1.0000 (synthetic n=1) | Rate == 1.00 | Rate >= 0.98 |
| **Retrieval Hit@1** | Retrieval | Metadata Chunk Matching | Ya (Deterministik) | 1.0000 (synthetic q=3) | Hit@1 >= 0.75 | Hit@1 >= 0.65 |
| **Retrieval Hit@3** | Retrieval | Metadata Chunk Matching | Ya (Deterministik) | 1.0000 (synthetic q=3) | Hit@3 >= 0.88 | Hit@3 >= 0.80 |
| **Retrieval Hit@5** | Retrieval | Metadata Chunk Matching | Ya (Deterministik) | 1.0000 (synthetic q=3) | Hit@5 >= 0.95 | Hit@5 >= 0.90 |
| **Context Precision** | Retrieval | Ranked ID Average Precision | Ya (Deterministik) | 1.0000 (synthetic q=3) | Score >= 0.85 | Score >= 0.75 |
| **Context Recall** | Retrieval | Offline Ground-Truth Coverage | Ya (Deterministik) | not measured | Score >= 0.90 | Score >= 0.80 |
| **Citation Page Accuracy** | Citations | Integer Comparison Page Number | Ya (Deterministik) | 1.0000 (synthetic q=3) | Accuracy >= 0.95 | Accuracy >= 0.88 |
| **Citation Text Support** | Citations | Substring Search & Normalized Fuzzy | Ya (Deterministik) | 1.0000 (synthetic q=3) | Support >= 0.92 | Support >= 0.85 |
| **Faithfulness** | Generation / Groundedness | Muse Structured LLM-as-Judge | Tidak (LLM-as-judge) | not measured | Score >= 0.90 | Score >= 0.82 |
| **Answer Correctness** | Generation / Groundedness | Muse Structured LLM-as-Judge | Tidak (LLM-as-judge) | not measured | Score >= 0.88 | Score >= 0.80 |
| **Abstention Accuracy** | Generation / Safety | String Pattern Match ("Tidak Ditemukan")| Ya (Deterministik) | not measured | Accuracy >= 0.95 | Accuracy >= 0.90 |
| **Native Extraction Latency** | Performance | System Clock Timer (p95) | Ya (Deterministik) | not measured | p95 <= 2 detik | p95 <= 4 detik |
| **PaddleOCR CPU Latency** | Performance | System Clock Timer (p95, 1 hal) | Ya (Deterministik) | not measured | p95 <= 15 detik | p95 <= 25 detik |
| **End-to-End Q&A Latency** | Performance | System Clock Timer (p95) | Ya (Deterministik) | not measured | p95 <= 4 detik | p95 <= 6 detik |
| **Cost per Invoice Extraction** | Resource / Cost | Token Counter & Model Price Sheet | Ya (Deterministik) | not measured | <= USD 0.03 | <= USD 0.06 |
| **Cost per Q&A Query** | Resource / Cost | Token Counter & Model Price Sheet | Ya (Deterministik) | not measured | <= USD 0.005 | <= USD 0.01 |
| **Agent Routing Accuracy** | Agentic Workflow | State Graph Transition Comparison | Ya (Deterministik) | not measured | Accuracy >= 0.92 | Accuracy >= 0.85 |

---

## 5. Protokol Pelaksanaan Evaluasi

1. **Automated Regression Test (CI):**
   - Setiap perubahan menjalankan dataset sintetis yang tersedia (saat ini 1 invoice/3 query); target berikutnya memperluas subset CI menjadi 10 invoice.
2. **Periodic Golden Evaluation (Offline):**
   - Dijalankan secara menyeluruh pada dataset ground-truth penuh (50+ invoice dengan variasi kategori A-D).
   - Menghasilkan laporan evaluasi terstruktur dalam format JSON dan Markdown di direktori `storage/eval-reports/`.
3. **Penyimpanan Trace Evaluasi di Langfuse:**
   - Setiap sesi evaluasi otomatis diberi tag `environment: "evaluation"` dan `run_id` khusus agar dapat dianalisis secara visual dan dibandingkan antar-versi model di dashboard Langfuse.
