import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

def download_stock_data(ticker, start_date, end_date):
    """Download stock data from Yahoo Finance and return as a DataFrame."""
    return yf.download(ticker, start=start_date, end=end_date)

def plot_stock_prices(data, stocks_to_show):
    """Plot stock prices based on selected stocks."""
    fig = go.Figure()
    
    if stocks_to_show in ["Both", "BBRI"]:
        fig.add_trace(go.Scatter(x=data.index, y=data['BBRI'], mode='lines', name='BBRI', line=dict(color='blue')))
    
    if stocks_to_show in ["Both", "IHSG"]:
        fig.add_trace(go.Scatter(x=data.index, y=data['IHSG'], mode='lines', name='IHSG', line=dict(color='orange')))

    fig.update_layout(
        title="BBRI and IHSG Stock Prices",
        xaxis_title="Date",
        yaxis_title="Stock Price (IDR)",
        hovermode="x unified",
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_daily_changes(data, view_option, stocks_to_show):
    """Plot daily changes (difference or percentage change) based on selected stocks."""
    fig = go.Figure()

    if view_option == "Difference":
        if stocks_to_show in ["Both", "BBRI"]:
            fig.add_trace(go.Scatter(x=data.index, y=data['BBRI Diff'], mode='lines', name='BBRI Diff', line=dict(color='blue')))
        if stocks_to_show in ["Both", "IHSG"]:
            fig.add_trace(go.Scatter(x=data.index, y=data['IHSG Diff'], mode='lines', name='IHSG Diff', line=dict(color='orange')))
        title = "BBRI and IHSG Daily Difference"
        yaxis_title = "Difference (IDR)"
    
    elif view_option == "Percentage Change":
        if stocks_to_show in ["Both", "BBRI"]:
            fig.add_trace(go.Scatter(x=data.index, y=data['BBRI % Change'], mode='lines', name='BBRI % Change', line=dict(color='blue')))
        if stocks_to_show in ["Both", "IHSG"]:
            fig.add_trace(go.Scatter(x=data.index, y=data['IHSG % Change'], mode='lines', name='IHSG % Change', line=dict(color='orange')))
        title = "BBRI and IHSG Percentage Change"
        yaxis_title = "Percentage Change (%)"
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=yaxis_title,
        hovermode="x unified",
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

def app():
    st.title("Stock Price Information")

    # Define the stock tickers
    tickers = {
        "BBRI": "BBRI.JK",
        "IHSG": "^JKSE"
    }

    # Set the date range for querying data
    start_date = st.date_input("Start date", pd.to_datetime("2018-01-01"))
    end_date = st.date_input("End date", pd.to_datetime("today"))

    # Fetch data only if not already in session state
    if "combined_data" not in st.session_state:
        if st.button("Get Stock Prices"):
            st.session_state.bbr_data = download_stock_data(tickers["BBRI"], start_date, end_date)
            st.session_state.ihsg_data = download_stock_data(tickers["IHSG"], start_date, end_date)

            # Combine data into a single DataFrame and store it in session state
            combined_data = pd.DataFrame({
                "BBRI": st.session_state.bbr_data['Close'],
                "IHSG": st.session_state.ihsg_data['Close']
            })

            # Calculate difference and percentage change
            combined_data['BBRI Diff'] = combined_data['BBRI'].diff()
            combined_data['IHSG Diff'] = combined_data['IHSG'].diff()
            combined_data['BBRI % Change'] = combined_data['BBRI'].pct_change() * 100
            combined_data['IHSG % Change'] = combined_data['IHSG'].pct_change() * 100
            
            st.session_state.combined_data = combined_data

    # Ensure that data has been loaded
    if "combined_data" in st.session_state:
        combined_data = st.session_state.combined_data

        # Dropdown for stock prices visualization
        st.subheader("Stock Prices Visualization")
        stock_price_filter = st.selectbox(
            "Select stock(s) to display for stock prices:",
            ("Both", "BBRI", "IHSG")
        )

        plot_stock_prices(combined_data, stock_price_filter)

        # Dropdown for daily changes visualization
        st.subheader("Daily Changes Visualization")
        daily_change_filter = st.selectbox(
            "Select stock(s) to display for daily changes:",
            ("Both", "BBRI", "IHSG")
        )
        daily_change_view = st.selectbox(
            "Select the view for daily changes:",
            ("Difference", "Percentage Change")
        )

        plot_daily_changes(combined_data, daily_change_view, daily_change_filter)

# Call the function to display the page
app()