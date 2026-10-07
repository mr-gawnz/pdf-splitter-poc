import streamlit as st

from splitter import split_pdf_bytes

st.set_page_config(page_title="PDF Half Splitter POC", page_icon="✂️", layout="centered")

st.title("PDF Half Splitter POC")
st.write(
    "Splits landscape spreads vertically without rendering them to images. "
    "The POC changes PDF page boxes so vectors, text, links and optional-content "
    "layers have the best chance of remaining intact."
)

uploaded = st.file_uploader("Choose a PDF", type=["pdf"])

col1, col2 = st.columns(2)
with col1:
    only_landscape = st.checkbox("Split only landscape pages", value=True)
with col2:
    order_label = st.selectbox("Page order", ["Left → Right", "Right → Left"])

if uploaded is not None:
    st.caption(f"Input: {uploaded.name} - {uploaded.size / 1024:.1f} KB")

    if st.button("Split PDF", type="primary", use_container_width=True):
        try:
            result, stats = split_pdf_bytes(
                uploaded.getvalue(),
                only_landscape=only_landscape,
                order="left-right" if order_label == "Left → Right" else "right-left",
            )
        except Exception as exc:
            st.error(f"Could not split the PDF: {exc}")
        else:
            base = uploaded.name.rsplit(".", 1)[0]
            output_name = f"{base}_split.pdf"
            st.success(
                f"Done. {stats.split_pages} page(s) split; "
                f"{stats.untouched_pages} page(s) left unchanged."
            )
            st.download_button(
                "Download split PDF",
                data=result,
                file_name=output_name,
                mime="application/pdf",
                use_container_width=True,
            )
            st.info(
                "POC note: this deliberately avoids flattening or rendering. "
                "Please test the result in Acrobat with the Layers panel and link tool."
            )
