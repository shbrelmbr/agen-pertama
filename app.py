import io
import streamlit as st
from crewai.project.crew_loader import load_crew
from pypdf import PdfReader
from docx import Document
from PIL import Image
from fpdf import FPDF

st.set_page_config(page_title="AI Agent Saya", page_icon="🤖", layout="wide")

st.title("🤖 AI Agent Saya")
st.caption("Sistem multi-agent dengan Chief of Staff dan 6 spesialis")


@st.cache_resource
def get_crew():
    crew, _ = load_crew("crew.jsonc")
    return crew


if "history" not in st.session_state:
    st.session_state.history = []
if "selected_idx" not in st.session_state:
    st.session_state.selected_idx = None


# ============== EKSTRAKSI FILE ==============
def extract_pdf(file_bytes):
    reader = PdfReader(io.BytesIO(file_bytes))
    max_pages = min(50, len(reader.pages))  # ← Naikkan dari 10 ke 50
    text = "\n\n".join(reader.pages[i].extract_text() or "" for i in range(max_pages))
    if len(reader.pages) > 50:
        text += f"\n\n[... Dokumen asli memiliki {len(reader.pages)} halaman, hanya 50 halaman pertama dianalisis ...]"
    return text


def extract_docx(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    if len(text) > 30000:
        text = text[:30000] + "\n\n[... Dokumen terlalu panjang, dipotong pada 30.000 karakter ...]"
    return text


def extract_image_info(file_bytes, filename):
    try:
        img = Image.open(io.BytesIO(file_bytes))
        info = (
            f"[GAMBAR: {filename}]\n"
            f"- Format: {img.format}\n"
            f"- Ukuran: {img.size[0]}x{img.size[1]} piksel\n"
            f"- Mode warna: {img.mode}\n"
            f"- Catatan: analisis gambar penuh belum didukung; hanya metadata yang tersedia."
        )
        return info
    except Exception as e:
        return f"[GAMBAR: {filename} — tidak dapat dibaca: {e}]"


def make_pdf(text):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    clean = text.replace("**", "").replace("##", "").replace("#", "").replace("*", "-")
    clean = clean.encode("latin-1", "replace").decode("latin-1")

    for line in clean.split("\n"):
        # Pecah baris panjang di batas kata
        while len(line) > 80:
            cut = line.rfind(" ", 0, 80)
            if cut < 20:
                cut = 80  # Tidak ada spasi, potong paksa
            pdf.multi_cell(0, 5, line[:cut].rstrip() or " ")
            line = line[cut:].lstrip()

        if line.strip():
            pdf.multi_cell(0, 5, line)
        else:
            pdf.ln(3)

    return bytes(pdf.output())


# ============== SIDEBAR ==============
with st.sidebar:
    st.header("👥 Tim Agen")
    st.markdown("""
    - 🎯 **Chief of Staff** — Manajer
    - 🔍 **Asisten Riset** — Riset
    - ✍️ **Penulis** — Menulis
    - 💚 **Hidup & Sosial** — Konseling
    - 💰 **Finance** — Keuangan
    - 💼 **Pekerjaan** — Karir
    - ⚔️ **Challenger** — Kritikus
    """)
    st.divider()
    st.header("📚 Riwayat")
    if not st.session_state.history:
        st.caption("_Belum ada riwayat._")
    else:
        if st.button("🗑️ Hapus Semua", use_container_width=True):
            st.session_state.history = []
            st.session_state.selected_idx = None
            st.rerun()
        st.caption("Klik untuk melihat hasil:")
        for i in range(len(st.session_state.history) - 1, -1, -1):
            item = st.session_state.history[i]
            nomor = i + 1
            judul = item["topik"][:32] + ("..." if len(item["topik"]) > 32 else "")
            label = f"#{nomor} · {judul}"
            if st.session_state.selected_idx == i:
                st.button(f"▶ {label}", key=f"r_{i}", use_container_width=True, type="primary")
            else:
                if st.button(label, key=f"r_{i}", use_container_width=True):
                    st.session_state.selected_idx = i
                    st.rerun()


with st.spinner("Memuat agen..."):
    crew = get_crew()


# ============== HALAMAN UTAMA ==============
if st.session_state.selected_idx is not None:
    idx = st.session_state.selected_idx
    item = st.session_state.history[idx]

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader(f"📄 Percakapan #{idx + 1}")
        st.caption(f"Topik: {item['topik']}")
        if item.get("attachments"):
            st.caption(f"📎 Lampiran: {', '.join(item['attachments'])}")
    with col2:
        if st.button("✖️ Tutup", use_container_width=True):
            st.session_state.selected_idx = None
            st.rerun()

    st.divider()
    st.markdown(item["hasil"])
    st.divider()

    col_md, col_pdf = st.columns(2)
    with col_md:
        st.download_button(
            "💾 Export Markdown (.md)",
            data=item["hasil"],
            file_name=f"hasil_{idx+1}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_pdf:
        try:
            pdf_bytes = make_pdf(item["hasil"])
            st.download_button(
                "💾 Export PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"hasil_{idx+1}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.button("💾 Export PDF (error)", disabled=True, use_container_width=True)
            st.caption(f"PDF error: {e}")

else:
    st.subheader("💬 Ajukan Pertanyaan Baru")

    topik = st.text_area(
        "Topik atau pertanyaan Anda:",
        placeholder="Contoh: Cara mengatur keuangan untuk freelancer",
        height=120,
        key="input_topik",
    )

    uploaded_files = st.file_uploader(
        "📎 Lampirkan dokumen (PDF, DOCX, atau gambar):",
        type=["pdf", "docx", "png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        help="PDF/DOCX: teks diekstrak. Gambar: hanya metadata dasar.",
    )

    tombol = st.button("🚀 Kirim", type="primary")

    if tombol:
        if not topik.strip():
            st.warning("⚠️ Silakan isi topik terlebih dahulu.")
        else:
            attachment_text = ""
            attachment_names = []

            if uploaded_files:
                for f in uploaded_files:
                    attachment_names.append(f.name)
                    b = f.read()
                    if f.name.lower().endswith(".pdf"):
                        try:
                            attachment_text += f"\n\n=== PDF: {f.name} ===\n" + extract_pdf(b)
                        except Exception as e:
                            st.warning(f"Gagal baca PDF {f.name}: {e}")
                    elif f.name.lower().endswith(".docx"):
                        try:
                            attachment_text += f"\n\n=== DOCX: {f.name} ===\n" + extract_docx(b)
                        except Exception as e:
                            st.warning(f"Gagal baca DOCX {f.name}: {e}")
                    elif f.name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                        attachment_text += "\n\n" + extract_image_info(b, f.name)

            full_input = topik
            if attachment_text:
                full_input = f"{topik}\n\n=== DOKUMEN REFERENSI ==={attachment_text}"

            with st.spinner("Chief of Staff sedang mengatur tim... Ini bisa memakan 1-3 menit."):
                try:
                    result = crew.kickoff(inputs={"topik": full_input})
                    st.session_state.history.append({
                        "topik": topik,
                        "attachments": attachment_names,
                        "hasil": str(result),
                    })
                    st.session_state.selected_idx = len(st.session_state.history) - 1
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    st.info("Jika error terkait 'rate limit', tunggu 1 menit lalu coba lagi.")