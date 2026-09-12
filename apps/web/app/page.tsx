import { DocumentUpload } from "@/features/documents/document-upload";

const capabilities = [
  { label: "Document intake", state: "Ready", tone: "ready" },
  { label: "PaddleOCR", state: "Ready", tone: "ready" },
  { label: "Agentic RAG", state: "Ready", tone: "ready" },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f4f1e8] text-[#17221b]">
      <div className="mx-auto max-w-6xl px-6 py-8 md:px-10 md:py-12">
        <header className="flex items-center justify-between border-b border-[#17221b]/15 pb-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#55705d]">
              Multimodal Document Intelligence
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              Invoice workspace
            </h1>
          </div>
          <span className="rounded-full border border-[#55705d]/30 bg-white/60 px-3 py-1.5 text-xs font-medium">
            Agentic RAG · Stage 9
          </span>
        </header>

        <section className="grid gap-8 py-10 lg:grid-cols-[1.08fr_0.92fr] lg:items-start">
          <div className="pt-4">
            <p className="text-sm font-medium text-[#b0512d]">Evidence before answers</p>
            <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.08] tracking-[-0.035em] md:text-6xl">
              Turn difficult invoices into verifiable information.
            </h2>
            <p className="mt-6 max-w-xl text-base leading-7 text-[#4d5b51] md:text-lg">
              Upload one PDF or image. Every file is validated before it enters the
              document intelligence pipeline.
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              {capabilities.map((capability) => (
                <div
                  className="flex items-center gap-2 rounded-full border border-[#17221b]/15 bg-white/50 px-3 py-2 text-xs"
                  key={capability.label}
                >
                  <span
                    className={`h-2 w-2 rounded-full ${
                      capability.tone === "ready" ? "bg-[#4a7658]" : "bg-[#c8bda5]"
                    }`}
                  />
                  <span className="font-medium">{capability.label}</span>
                  <span className="text-[#6d776f]">{capability.state}</span>
                </div>
              ))}
            </div>
          </div>

          <DocumentUpload />
        </section>
      </div>
    </main>
  );
}
