import pandas as pd
import os
from dash import Dash, html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from figure import create_figure
from sqlalchemy import create_engine
from dotenv import load_dotenv
from update_data import update_dataset
from dash.exceptions import PreventUpdate
from functools import lru_cache
from zoneinfo import ZoneInfo

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# ==========================================================
# Load Dataset
# ==========================================================

engine = create_engine(DATABASE_URL)

import time

@lru_cache(maxsize=1)
def load_data():

    t0 = time.time()

    df = pd.read_sql(
        """ SELECT
        time,
        date,
        latitude,
        longitude,
        depth,
        mag,
        place,
        country
    FROM earthquakes""", engine
    )

    print(f"Read SQL in {time.time() - t0:.2f} sec")

    t1 = time.time()

    df["time"] = pd.to_datetime(df["time"])
    df["date"] = pd.to_datetime(df["date"])

    print(f"Converted dates in {time.time() - t1:.2f} sec")

    print(f"Total load time: {time.time() - t0:.2f} sec")

    return df


def get_last_updated():

    latest = pd.read_sql(
        "SELECT MAX(time) AS latest FROM earthquakes",
        engine
    )["latest"][0]

    print("Latest from DB:", latest)

    latest = (
        pd.to_datetime(latest)
        .tz_localize("UTC")
        .tz_convert(ZoneInfo("Asia/Kolkata"))
    )

    print("Converted:", latest)

    return latest.strftime("%d %b %Y • %I:%M %p IST")

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

def serve_layout():
  
  df = load_data()

  return dbc.Container(

    fluid=True,

    children=[

        dbc.Row(

            [

                dbc.Col(

                    html.Div([

                        html.H2(
                            "Quack 🌍 Dash",
                            style={
                                "marginTop": "15px",
                                "marginBottom": "5px"
                            }
                        ),

                        html.P(
                            "Real-time global earthquake activity | USGS data",
                            style={
                                "color": "#b0b0b0",
                                "fontSize": "16px"
                            }
                        )

                    ]),

                    width=9

                ),

                dbc.Col(

                    [

                        dbc.Button(

                            "🔄 Fetch Latest Data",

                            id="refresh-data",

                            color="primary",

                            style={
                                "marginTop": "20px",
                                "width": "225px"
                            }

                        ),

                        html.Div(

                            f"🕒 Last Update: {get_last_updated()}",

                            id="last-updated",

                            style={
                                "marginTop": "8px",
                                "width": "225px",
                                "textAlign": "right",
                                "fontSize": "12px",
                                "color": "#b0b0b0"
                            }

                        )

                    ],

                    width=3,

                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "flex-end"
                    }

                )

            ],

            align="center"

        ),
        dbc.Row(

            dbc.Col(

                html.Div(
                    id="refresh-message",
                    style={
                        "marginBottom": "15px",
                        "color": "#90ee90",
                        "fontWeight": "bold"
                    }
                )

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

app.layout = serve_layout


def filter_data(df, start_date, end_date, min_mag, region):

    filtered = df.copy()

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

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

def update_graph(start_date, end_date, min_mag, region):

    if start_date is None or end_date is None:
        raise PreventUpdate

    df = load_data()

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
    if start_date is None or end_date is None:
        raise PreventUpdate
    
    if clickData is None:
        return (
            "Click a point on the graph",
            "",
            []
        )
    
    df = load_data()

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

@app.callback(
    Output("refresh-message", "children"),
    Output("last-updated", "children"),
    Input("refresh-data", "n_clicks"),
    prevent_initial_call=True
)
def refresh_database(n):

    try:

        inserted = update_dataset()

        latest = pd.read_sql(
            "SELECT MAX(time) AS latest FROM earthquakes",
            engine
        )

        print(latest)

        if inserted == 0:
            return (
                "ℹ No new earthquakes found.",
                f"🕒Last Update: {get_last_updated()}"
            )

        load_data.cache_clear()

        return (
            f"✔ Added {inserted} new earthquake(s). Refresh the page to view them.",
            f"🕒Last Update: {get_last_updated()}"
        )

    except Exception as e:
        return (
            f"❌ Update failed: {e}",
            f"🕒Last Update: {get_last_updated()}"
        )

# ==========================================================
# Run
# ==========================================================

if __name__ == "__main__":
    app.run(debug=False)