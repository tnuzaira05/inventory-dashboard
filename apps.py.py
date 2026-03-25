import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Inventory Turnover & Stockout Risk", layout="wide")

st.title("Inventory Turnover & Stockout Risk Dashboard")
st.write("This dashboard analyzes product movement, turnover, and stockout risk from uploaded sales data.")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    required_cols = ['Product Name', 'Product Category', 'Units Sold', 'Unit Price', 'Date']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Missing required columns: {missing_cols}")
    else:
        df['Date'] = pd.to_datetime(df['Date'])
        df['Revenue'] = df['Units Sold'] * df['Unit Price']
        df['Month'] = df['Date'].dt.to_period('M').astype(str)

        st.subheader("Raw Data Preview")
        st.dataframe(df.head())

        monthly_sales = df.groupby(['Product Name', 'Product Category', 'Month'])['Units Sold'].sum().reset_index()

        product_metrics = monthly_sales.groupby(['Product Name', 'Product Category'])['Units Sold'].agg(
            Total_Units_Sold='sum',
            Avg_Monthly_Units='mean',
            Demand_Variability='std'
        ).reset_index()

        product_metrics['Demand_Variability'] = product_metrics['Demand_Variability'].fillna(0)
        product_metrics['Inventory_Turnover_Proxy'] = (
            product_metrics['Total_Units_Sold'] / product_metrics['Avg_Monthly_Units']
        )

        avg_threshold = product_metrics['Avg_Monthly_Units'].quantile(0.75)
        var_threshold = product_metrics['Demand_Variability'].quantile(0.75)

        product_metrics['Stockout_Risk'] = product_metrics.apply(
            lambda row: 'High Risk'
            if row['Avg_Monthly_Units'] >= avg_threshold and row['Demand_Variability'] >= var_threshold
            else 'Low/Medium Risk',
            axis=1
        )

        slow_threshold = product_metrics['Inventory_Turnover_Proxy'].quantile(0.25)

        product_metrics['Movement_Class'] = product_metrics['Inventory_Turnover_Proxy'].apply(
            lambda x: 'Slow Moving' if x <= slow_threshold else 'Normal/Fast Moving'
        )

        overall_turnover = round(product_metrics['Inventory_Turnover_Proxy'].mean(), 2)
        high_risk_count = (product_metrics['Stockout_Risk'] == 'High Risk').sum()
        slow_moving_count = (product_metrics['Movement_Class'] == 'Slow Moving').sum()

        st.subheader("Key Performance Indicators")
        col1, col2, col3 = st.columns(3)
        col1.metric("Overall Turnover Proxy", overall_turnover)
        col2.metric("High Stockout Risk Products", int(high_risk_count))
        col3.metric("Slow Moving Products", int(slow_moving_count))

        st.subheader("Filter by Product Category")
        categories = ['All'] + sorted(df['Product Category'].dropna().unique().tolist())
        selected_category = st.selectbox("Select Category", categories)

        if selected_category != 'All':
            filtered_metrics = product_metrics[product_metrics['Product Category'] == selected_category]
        else:
            filtered_metrics = product_metrics.copy()

        st.subheader("Top 10 Products by Inventory Turnover Proxy")
        top_turnover = filtered_metrics.sort_values(by='Inventory_Turnover_Proxy', ascending=False).head(10)

        fig1, ax1 = plt.subplots(figsize=(10, 5))
        ax1.bar(top_turnover['Product Name'], top_turnover['Inventory_Turnover_Proxy'])
        ax1.set_xlabel("Product Name")
        ax1.set_ylabel("Inventory Turnover Proxy")
        ax1.set_title("Top 10 Products by Inventory Turnover Proxy")
        plt.xticks(rotation=75)
        plt.tight_layout()
        st.pyplot(fig1)

        st.subheader("Stockout Risk by Demand Level and Variability")
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        for risk in filtered_metrics['Stockout_Risk'].unique():
            subset = filtered_metrics[filtered_metrics['Stockout_Risk'] == risk]
            ax2.scatter(subset['Avg_Monthly_Units'], subset['Demand_Variability'], label=risk)
        ax2.set_xlabel("Average Monthly Units")
        ax2.set_ylabel("Demand Variability")
        ax2.set_title("Stockout Risk Scatter Plot")
        ax2.legend()
        plt.tight_layout()
        st.pyplot(fig2)

        st.subheader("Slow Moving Products")
        slow_products = filtered_metrics[filtered_metrics['Movement_Class'] == 'Slow Moving'] \
            .sort_values(by='Inventory_Turnover_Proxy', ascending=True)
        st.dataframe(slow_products.head(10))

        st.subheader("Interpretation")
        st.write(
            "Products with high average monthly demand and high demand variability are flagged as high stockout risk. "
            "Products with low turnover proxy are classified as slow moving. "
            "This helps managers identify which items may require tighter replenishment planning and which items may need inventory reduction or promotional action."
        )
