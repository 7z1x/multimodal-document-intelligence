# Langfuse Setup

Stage 14 selalu menyimpan trace internal ke PostgreSQL dan `storage/audit-logs`. Langfuse adalah exporter opsional; kegagalannya tidak menggagalkan RAG request.

## Opsi Gratis

- Self-host Langfuse memakai deployment resmi: <https://langfuse.com/self-hosting>
- Atau gunakan Langfuse Cloud Hobby untuk development.

Jangan menambahkan stack Langfuse ke `docker-compose.yml` project secara parsial. Langfuse v4 self-hosted juga membutuhkan worker, ClickHouse, Redis/Valkey, dan object storage; gunakan Compose resmi mereka agar versinya tetap konsisten.

## Konfigurasi Project

Setelah membuat project dan memperoleh project keys, isi `.env` lokal:

```dotenv
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=lf_pk_replace_me
LANGFUSE_SECRET_KEY=lf_sk_replace_me
LANGFUSE_BASE_URL=http://localhost:3001
LANGFUSE_TIMEOUT_SECONDS=5
```

Jangan mengisi key tersebut pada `.env.example` atau melakukan commit `.env`.

Status exporter terlihat pada API/UI:

- `sent`: SDK selesai mengirim batch trace.
- `disabled`: integrasi sengaja dimatikan.
- `misconfigured`: integrasi aktif tetapi key belum lengkap.
- `failed`: server atau exporter gagal; pipeline utama tetap berjalan.

`sent` adalah konfirmasi SDK menyelesaikan flush, bukan bukti independen bahwa dashboard telah diperiksa. Verifikasi trace di dashboard Langfuse sebelum menyatakan observability eksternal siap production.
