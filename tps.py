import altair as alt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, ttest_ind
import streamlit as st


@st.cache
def load_data():
    q = "8d4271e8-3ec6-43f2-9235-1b06737c46b8"
    url = f"https://api.flipsidecrypto.com/api/v2/queries/{q}/data/latest"
    df = pd.read_json(url)

    # create rolling averages and TPS averages
    for i in ["TX_COUNT", "SUCCESS", "FAILS"]:
        df[f"{i}_per_second"] = df[i] / 60

    for i in [
        "TX_COUNT_per_second",
        "SUCCESS_per_second",
        "SUCCESS_RATE",
        "FAILS_per_second",
    ]:
        df[f"{i}_5_min_avg"] = df[i].rolling(5).mean()
        df[f"{i}_hourly_avg"] = df[i].rolling(60).mean()
        df[f"{i}_6_hr_avg"] = df[i].rolling(60 * 6).mean()
        df[f"{i}_daily_avg"] = df[i].rolling(60 * 24).mean()
        df[f"{i}_weekly_avg"] = df[i].rolling(60 * 24 * 7).mean()
    return df


df = load_data()

st.title("Solana TPS")
st.caption(
    """
One of Solana's main features is its speed compared to other blockchains.
Blockchain performance is usually measured in Transactions per Second (TPS).
Measure the TPS of Solana in February (non votes) and 'Successful TPS' per day and create a chart showing how TPS has fluctuated during that time period.
"""
)

st.subheader("Average TPS")
f"""
The transactions per second were analyzed for the month of February.
- The average transaction rate was **{df.TX_COUNT_per_second.mean():.1f} ± {df.TX_COUNT_per_second.std()/np.sqrt(len(df)):.1f} TPS**.
- The average **successful** transaction rate was **{df.SUCCESS_per_second.mean():.1f} ± {df.SUCCESS_per_second.std()/np.sqrt(len(df)):.1f} TPS**.
- The **average success rate** was **{df.SUCCESS_RATE.mean()*100:.1f} ± {df.SUCCESS_RATE.std()/np.sqrt(len(df))*100:.2f}%**.

Below is the hourly and daily rolling averages of TPS and Successful TPS, which is explained in more detail in the Daily TPS section.
"""

# Overall TPS
chart_data = df[
    [
        "TX_COUNT_per_second_hourly_avg",
        "TX_COUNT_per_second_daily_avg",
        "SUCCESS_per_second_hourly_avg",
        "SUCCESS_per_second_daily_avg",
    ]
]
chart_data = chart_data.rename(
    columns={
        "TX_COUNT_per_second_hourly_avg": "Hourly Average, TPS",
        "TX_COUNT_per_second_daily_avg": "Daily Average, TPS",
        "SUCCESS_per_second_hourly_avg": "Hourly Average, Successful TPS",
        "SUCCESS_per_second_daily_avg": "Daily Average, Successful TPS",
    }
)
chart_data.index = df.DATETIME
st.line_chart(chart_data)

f"""
Over this time period, the success rate seems to be fairly constant.
While the average succses rate per minute shows some variation, ranging from {df.SUCCESS_RATE.min()*100:.1f}% to {df.SUCCESS_RATE.max()*100:.1f}%, the hourly average never drops below 
{df.SUCCESS_RATE_hourly_avg.min()*100:.1f}%.
This seems to suggest that recent instability in Solana has been at least some what alleviated.
"""
# Success Rate
chart_data = df[
    [
        "SUCCESS_RATE",
        "SUCCESS_RATE_hourly_avg",
        "SUCCESS_RATE_daily_avg",
    ]
]
chart_data = chart_data.rename(
    columns={
        "SUCCESS_RATE": "Success Rate",
        "SUCCESS_RATE_hourly_avg": "Hourly Average, Success Rate",
        "SUCCESS_RATE_daily_avg": "Daily Average, Success Rate",
    }
)
chart_data.index = df.DATETIME
st.line_chart(chart_data)

# Combined, daily
st.subheader("Daily TPS")

daily_df = df.copy().resample("D", on="DATETIME")
mean_daily = daily_df.mean()[
    ["TX_COUNT_per_second", "SUCCESS_per_second", "SUCCESS_RATE"]
]
mean_daily["date"] = mean_daily.index
mean_daily = mean_daily.rename(
    columns={
        "TX_COUNT_per_second": "Mean TPS",
        "SUCCESS_RATE": "Mean Success Rate",
        "SUCCESS_per_second": "Mean Successful TPS",
    }
)

tps_c, tps_p = spearmanr(mean_daily["Mean TPS"], mean_daily["Mean Successful TPS"])
rate_c, rate_p = spearmanr(mean_daily["Mean TPS"], mean_daily["Mean Success Rate"])

f"""
Breaking it down by day, the Success Rate has been fairly constant (
{mean_daily["Mean Success Rate"].mean()*100:.1f} ± {mean_daily["Mean Success Rate"].std()/np.sqrt(len(mean_daily))*100:.2f}%).

However, there is a noticable decrease in TPS starting around February 18th.
Transactions dropped below the overall daily mean for February ({mean_daily["Mean TPS"].mean():.1f} TPS), with no change in success rate.
This drop may be worth investigating, however it aligns with a holiday weekend in the United States (President's Day).
There may be a larger number of users not interacting with the Solana blockchain due to this, and larger market conditions (downturn in market, uncertainty about news related to Russian and Ukraine, etc).

There is a strong correlation between TPS and Successful TPS (Spearman correlation coeffecient {tps_c:.2f}, pvalue={tps_p:.2f}), which is not correlated with Success Rate ({rate_c:.2f}, pvalue={rate_p:.2f}).
This suggests that Success Rate doesn't clearly influence the TPS of Solana during this period, it just acts to scale the number of transactions that succeed.
"""

base = alt.Chart(mean_daily).encode(alt.X("date:T", axis=alt.Axis(title=None)))
bar = base.mark_bar().encode(alt.Y("Mean TPS:Q", title=""))
bar2 = base.mark_bar().encode(
    alt.Y("Mean Successful TPS:Q", title="Transactions per Second"),
    color=alt.value("green"),
)
rule = alt.Chart(mean_daily).mark_rule(color="orange").encode(y="mean(Mean TPS):Q")
line = base.mark_line(color="red").encode(y="Mean Success Rate:Q")
hover = alt.selection_single(
    fields=["date"],
    nearest=True,
    on="mouseover",
    empty="none",
)
tooltips = (
    alt.Chart(mean_daily)
    .mark_rule()
    .encode(
        x="date",
        opacity=alt.condition(hover, alt.value(0.3), alt.value(0)),
        tooltip=[
            alt.Tooltip("date", title="Date"),
            alt.Tooltip("Mean TPS", title="Daily average TPS"),
            alt.Tooltip("Mean Successful TPS", title="Daily average successful TPS"),
            alt.Tooltip("Mean Success Rate", title="Daily average Success Rate"),
        ],
    )
    .add_selection(hover)
)

chart = alt.layer((bar + bar2 + rule + tooltips), line).resolve_scale(y="independent")

st.altair_chart(chart.interactive(), use_container_width=True)

st.subheader("Methods")
"""
Data was obtained from [this query](https://app.flipsidecrypto.com/velocity/queries/8d4271e8-3ec6-43f2-9235-1b06737c46b8) on Flipside Crypto.
All transactions in February were grouped by minute, to get the number of transactions per minute, as well as the successful transactions per minute.
There values were divided by 60 to get the TPS.
Additionally *Success Rate* was calculated (`successful_transactions / total transactions`), as were the hourly and daily rolling averages.

Note that transactions were grouped by minute instead of second to reduce dataset size (it would be 1.8 million rows, while Flipside has a limit of 100k rows per query).
This should not effect analysis on the scale we are working at (daily or hourly).
TPS and successful TPS would be the same, while the Success Rate would be calculated on a per-second rate, instead of per-minute.


The DataFrame used for this is analysis is below.
"""
st.dataframe(df)
