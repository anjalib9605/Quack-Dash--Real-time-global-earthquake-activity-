import pandas as pd
import os
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
from figure import create_figure
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# ==========================================================
# Load Dataset
# ==========================================================

engine = create_engine(DATABASE_URL)

df = pd.read_sql(
    "SELECT * FROM earthquakes",
    engine
)

df["time"] = pd.to_datetime(df["time"])
df["date"] = pd.to_datetime(df["date"])

# ==========================================================
# Dash App
# ==========================================================

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY]
)
server = app.server

# ==========================================================
# Layout
# ==========================================================

app.layout = dbc.Container(

    fluid=True,

    children=[

        dbc.Row(

            dbc.Col(
                html.Div([
                    html.H2(
                        "Quack 🌍 Dash",
                        style={
                            "textAlign": "center",
                            "marginTop": "15px",
                            "marginBottom": "20px"
                        }
                    ),
                    html.P(
                        "Real-time global earthquake activity | USGS data",
                        style={
                            "textAlign": "center",
                            "color": "#b0b0b0",
                            "fontSize": "16px",
                            "marginBottom": "20px"
                        }
                    )
                ])
            )

        ),

        dbc.Card(

            dbc.CardBody(

                dbc.Row([

                    dbc.Col(

                      [

                          html.Label("Date Range"),

                          dcc.DatePickerRange(

                              id="date-range",

                              start_date=df["date"].min().date(),

                              end_date=df["date"].max().date(),

                              display_format="DD MMM YYYY"

                          )

                      ],

                      width=5

                  ),

                    dbc.Col([

                        html.Label("Minimum Magnitude"),

                        dcc.Dropdown(

                            id="mag-filter",
                            className="filter-dropdown",

                            options=[

                                {"label":"All","value":0},

                                {"label":"4+","value":4},

                                {"label":"5+","value":5},

                                {"label":"6+","value":6},

                                {"label":"7+","value":7},

                                {"label":"8+","value":8}

                            ],

                            value=0,

                            clearable=False

                        )

                    ], width=3),

                    dbc.Col(

                      [

                          html.Label("Region"),

                          dcc.Dropdown(

                              id="region-filter",
                              className="filter-dropdown",

                              options=[
                                {"label":"All","value":"ALL"}
                            ] + [
                                {"label":c,"value":c}
                                for c in sorted(df["country"].unique())
                            ],

                              value="ALL",

                              clearable=False

                          )

                      ],

                      width=3

                  ), 

                ])

            ),

            style={"marginBottom":"20px"}

        ),

        dbc.Card(

          dbc.CardBody(

              dcc.Graph(
                  clickData=None,

                  id="earthquake-graph",

                  style={"height":"70vh"},

                  config={

                      "displaylogo":False,

                      "scrollZoom":True,

                      "responsive":True,

                      "doubleClick":"reset"

                  }

              )

          ),

          style={"marginBottom":"15px"}

      ),
      dbc.Card(

        dbc.CardBody([

            html.H4("Selected Day"),

            html.H5(
                "Click a point on the graph",
                id="selected-date"
            ),

            html.H6(
                "",
                id="selected-summary"
            )

        ]),

        style={"marginBottom":"15px"}

    ),

    dbc.Card(

      dbc.CardBody([

          dash_table.DataTable(

              id="earthquake-table",

              columns=[

                  {"name":"Time","id":"time"},

                  {"name":"Place","id":"place"},

                  {"name":"Magnitude","id":"mag"},

                  {"name":"Depth (km)","id":"depth"},

                  {"name":"Latitude","id":"latitude"},

                  {"name":"Longitude","id":"longitude"}

              ],

              data=[],

              page_size=12,

              sort_action="native",

              style_table={

                  "overflowX":"auto"

              },

              style_header={

                  "backgroundColor":"#2c2c2c",

                  "color":"white",

                  "fontWeight":"bold"

              },

              style_cell={

                  "backgroundColor":"#1e1e1e",

                  "color":"white",

                  "textAlign":"left"

              }

          )

      ])

  )

    ]

)


def filter_data(df, start_date, end_date, min_mag, region):

    filtered = df.copy()

    filtered = filtered[
        (filtered["date"] >= start_date) &
        (filtered["date"] <= end_date)
    ]

    filtered = filtered[
        filtered["mag"] >= min_mag
    ]

    if region != "ALL":
        filtered = filtered[
            filtered["country"] == region
        ]

    return filtered

@app.callback(

  Output("earthquake-graph","figure"),
  Input("date-range","start_date"),
  Input("date-range","end_date"),
  Input("mag-filter","value"),
  Input("region-filter","value")

)

def update_graph(start_date,end_date,min_mag,region):

    filtered = filter_data(
        df,
        start_date,
        end_date,
        min_mag,
        region
    )

    return create_figure(filtered)


@app.callback(

    Output("selected-date","children"),
    Output("selected-summary","children"),
    Output("earthquake-table","data"),

    Input("date-range","start_date"),
    Input("date-range","end_date"),
    Input("mag-filter","value"),
    Input("region-filter","value"),
    Input("earthquake-graph","clickData")

)

def update_table(start_date, end_date, min_mag, region, clickData):
    if clickData is None:
        return (
            "Click a point on the graph",
            "",
            []
        )
    # Apply the same filters as the graph
    filtered = filter_data(
        df,
        start_date,
        end_date,
        min_mag,
        region
    )

    selected_date = pd.to_datetime(

        clickData["points"][0]["x"]

    ).floor("D")

    selected = filtered[

        filtered["date"] == selected_date

    ].copy()

    if selected.empty:
        return (
            selected_date.strftime("%d %b %Y"),
            "No earthquakes found.",
            []
        )

    selected["time"] = selected["time"].dt.strftime("%H:%M:%S")

    max_mag = selected["mag"].max()

    summary = (

        f"{len(selected)} earthquakes | "

        f"Maximum Magnitude: {max_mag:.1f}"

    )

    return (

        selected_date.strftime("%d %b %Y"),

        summary,

        selected[

            [
                "time",
                "place",
                "mag",
                "depth",
                "latitude",
                "longitude"
            ]

        ].to_dict("records")

    )

# ==========================================================
# Run
# ==========================================================

if __name__ == "__main__":
    app.run(debug=False)