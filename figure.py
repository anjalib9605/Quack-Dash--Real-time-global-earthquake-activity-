import plotly.express as px
import pandas as pd

# ==========================================================
# Figure Builder
# ==========================================================

def create_figure(data):

    daily = (
        data.groupby("date")
            .size()
            .reset_index(name="Earthquake Count")
    )

    latest = daily["date"].max()
    start = latest - pd.Timedelta(days=30)

    fig = px.line(
      daily,
      x="date",
      y="Earthquake Count",
      title="Daily Earthquake Count",
      markers=True
    )

    fig.update_traces(

      line=dict(
          color="royalblue",
          width=2
      ),

      hovertemplate=
      "<b>%{x|%d %b %Y}</b><br>"
      "Earthquakes: %{y}"
      "<extra></extra>"
    )

    fig.update_layout(

        template="plotly_dark",

        hovermode="x unified",

        title_x=0.5,

        autosize=True,

        margin=dict(
            l=40,
            r=30,
            t=60,
            b=40
        ),

        modebar=dict(
            orientation="h"
        )

    )

    fig.update_xaxes(
      rangeslider_visible=True
    )

    return fig