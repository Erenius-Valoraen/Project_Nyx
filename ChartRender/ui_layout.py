import streamlit as st

def setup_page():
    st.set_page_config(
        page_title="Trading Dashboard",
        page_icon="📈",
        layout="wide",
    )


def render_sidebar():
    with st.sidebar:
        st.title("📊 Trading Dashboard")
        st.markdown("---")

        st.subheader("Navigation")
        st.radio("Go to:", [" Charts", " Watchlist", "Bots", "⚙ Settings"])

        st.markdown("---")
        st.subheader("View Options")
        st.checkbox("Dark Mode")
        st.checkbox("Compact View")

        st.markdown("---")
        st.caption("v1.0 • UI placeholder")


def render_header():
    st.title("📈 TradingView Chart Viewer")
    st.write("A sleek interface for viewing stock candlestick charts fetched using your API.")
    st.markdown("---")


def render_chart_settings():
    with st.expander("Chart Settings (UI only, non-functional)", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.text_input("Symbol", "RELIANCE")
            st.selectbox("Interval", ["1 Minute", "5 Minute", "15 Minute", "1 Hour"])

        with c2:
            st.date_input("From Date")
            st.time_input("From Time")

        with c3:
            st.date_input("To Date")
            st.time_input("To Time")


def render_chart_container(chart_callable):
    st.markdown("### 📊 Candlestick Chart")

    chart_container = st.container()
    with chart_container:
        st.markdown(
            """
            <div style="
                background-color: #ffffff10;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            ">
            """,
            unsafe_allow_html=True
        )

        chart_callable()   # render your TradingView chart

        st.markdown("</div>", unsafe_allow_html=True)