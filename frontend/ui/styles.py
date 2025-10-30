from __future__ import annotations

import streamlit as st


def inject_core_css() -> None:
    st.markdown(
        """
        <style>
            .main .block-container {
                padding-bottom: 2rem;
                max-width: 100%;
            }
            .chat-messages {
                min-height: 400px;
                max-height: 70vh;
                overflow-y: auto;
                padding: 1rem 0;
            }
            .input-section {
                background: white;
                padding: 1rem 0;
                margin-top: 1rem;
            }
            .chat-container {
                height: 100%;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
