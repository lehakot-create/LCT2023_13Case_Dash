import os

import dash
from dash import dcc
from dash import html
from dash import dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash.dependencies import Input, Output, State
from clickhouse_driver import Client
from sqlalchemy import create_engine, Table, MetaData
from datetime import date, datetime
from dotenv import load_dotenv


load_dotenv('.env')

DB_USER = os.environ.get('POSTGRES_USER')
DB_PASS = os.environ.get('POSTGRES_PASS')
DB_HOST = os.environ.get('POSTGRES_HOST')
DB_NAME = os.environ.get('POSTGRES_DB')
DB_PORT = os.environ.get('POSTGRES_PORT')

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    )

client = Client(host='0.0.0.0',
                settings={'use_numpy': True}
                )

# Инициализируем приложение
app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.COSMO])



#  Селекторы
city = pd.read_sql('select * from bookings.airports_data', con=engine)
city['city'] = city['city'].apply(lambda d: d['ru'])
city_list = sorted(city['city'].to_list())


departure_city_selector = dcc.Dropdown(
    id='departure-city-select',
    options=city_list,
    value=['Москва'],
    multi=True
    )

arrival_city_selector = dcc.Dropdown(
    id='arrival-city-select',
    options=city_list,
    value=['Санкт-Петербург'],
    multi=True
    )


calendar_selector = dcc.DatePickerRange(
                    id='calendar-select',
                    display_format='DD-MM-YYYY',
                    # end_date_placeholder_text='M-D-Y-Q',
                    start_date=date(2016,1,1),
                    end_date=date(2017,12,31)
                    #    start_date_placeholder_text="Start Period",
                    #    end_date_placeholder_text="End Period",
                    #    calendar_orientation='vertical',
)

# TABS КОНТЕНТ

tab_1_content = [dbc.Row([
                dbc.Col(html.Div(id='chart-coef-filling'), md=6, width={'size':6}),
                dbc.Col(html.Div(id='chart-coef-filling_box'), md=6, width={'size':6})
            ]),]

tab_2_content = [ dbc.Row(
                 dbc.Col(id='table-filling')
                 )]


# LAYOUT

app.layout = html.Div(
    dbc.Row([
        # Боковая панель
        dbc.Col([
            html.H1('Кола')
        ], width={'size': 1}, style={'margin-left': 10, 'margin-top': 10,}),
        #  Основной экран
        dbc.Col([
            # Фильтры
            dbc.Row([
                dbc.Col(html.Div('Город вылета:'),  width={'size': 1}, style={'margin': 10, }),
                dbc.Col(departure_city_selector,  width={'size': 2},  style={'margin': 10,}),
                dbc.Col(html.Div('Город прилета:'),  width={'size': 1}, style={'margin': 10,}),
                dbc.Col(arrival_city_selector,  width={'size': 2}, style={'margin': 10,}),
                dbc.Col(calendar_selector,  style={'margin': 10,})
            ]),
            dbc.Row([
                dbc.Col(dbc.Button('Применить фильтры', id='apply-filters', n_clicks=0, class_name='me-2'))
            ]),
            # Графики
            dbc.Tabs([
                dbc.Tab(tab_1_content, label = 'Графики'),
                dbc.Tab(tab_2_content, label = 'Таблица')
            ], style={'margin-top': 20,})
            # dbc.Row([
            #     dbc.Col(html.Div(id='chart-coef-filling'), md=6, width={'size':6}),
            #     dbc.Col(html.Div(id='chart-coef-filling_box'), md=6, width={'size':6})
            # ]),
            # dbc.Row(
            #      dbc.Col(id='table-filling')
            #      )
        ])
    ])



)


#  Таблица вылетов-прилетов
query = """WITH tpassenger_count as (
    SELECT flight_id, COUNT(*) as passenger_count
    FROM bookings.ticket_flights
    GROUP BY flight_id
),
tseats_count as (
    SELECT aircraft_code, COUNT (*) as seats_count
    FROM bookings.seats
    GROUP BY aircraft_code)
SELECT * FROM bookings.flights
LEFT JOIN tpassenger_count ON flights.flight_id = tpassenger_count.flight_id
LEFT JOIN tseats_count ON flights.aircraft_code = tseats_count.aircraft_code"""

df_flight = pd.read_sql(query, con=engine)
df_flight['year'] = df_flight['scheduled_departure'].dt.year
df_flight['month'] = df_flight['scheduled_departure'].dt.month
df_flight['day'] = df_flight['scheduled_departure'].dt.day
df_flight['weekday'] = df_flight['scheduled_departure'].dt.weekday+1
df_flight['date'] = df_flight['scheduled_departure'].dt.date
df_flight = df_flight.dropna(axis=0)
df_flight = df_flight.merge(city[['airport_code', 'city']], how='left', left_on='departure_airport', right_on='airport_code').\
         merge(city[['airport_code', 'city']], how='left', left_on='arrival_airport', right_on='airport_code')
df_flight = df_flight.rename(columns={'city_x': 'departure_city', 'city_y': 'arrival_city'})
df_flight = df_flight.drop(['airport_code_x', 'airport_code_y'], axis=1)
df_flight['coef_seats'] = round(df_flight['passenger_count'] / df_flight['seats_count'], 2)


@app.callback(
    [Output(component_id='chart-coef-filling', component_property='children'),
     Output(component_id='chart-coef-filling_box', component_property='children'),
     Output(component_id='table-filling', component_property='children')],
    [Input(component_id='apply-filters', component_property='n_clicks')],
    [State(component_id='departure-city-select', component_property='value'),
     State(component_id='arrival-city-select', component_property='value'),
     State('calendar-select', 'start_date'),
     State('calendar-select', 'end_date'),
     ]
    )
def update_chart_sumsales_dayweek(n, departure_city, arrival_city, start_date, end_date):

    chart_data = df_flight[  (df_flight['departure_city'].isin(departure_city))
                          &  (df_flight['arrival_city'].isin(arrival_city))
                          &  (df_flight['date'].between(datetime.strptime(start_date, '%Y-%m-%d').date(),
                                                        datetime.strptime(end_date, '%Y-%m-%d').date()))
                    ]

    if chart_data.shape[0] == 0:
        return html.Div('Пожалуйста, выберите фильтры для графика', style={'margin-top': 30}), html.Div(), html.Div()

    # График 1

    fig_1 = px.histogram(chart_data, x="coef_seats", title="Гистограмма распределения коэффициента заполнения салона самолета",
                       nbins=40,
                       labels={'coef_seats': 'Коэффициент заполнения самолета пассажирами',  'count':'Количество рейсов',})

    html_1 = [dcc.Graph(figure=fig_1)]

    # График 2

    fig_2 = px.box(chart_data, x="weekday", y="coef_seats", notched=True, title="Коэффициент заполнения салона самолета по дням недели")

    html_2 = [dcc.Graph(figure=fig_2)]

    # Таблица

    table_1 = dash_table.DataTable(chart_data.to_dict('records'),
                         [{"name": i, "id": i} for i in chart_data.columns],
                         page_size=30,
                         filter_action='native',
                         )

    html_3 = dbc.Container([
        dbc.Label('Таблица полетов:'),
        table_1,
    ], style={'margin-top': 30})

    return html_1, html_2, html_3


if __name__ == '__main__':
    app.run_server(debug=True,
                   host='0.0.0.0')  # Run the Dash app
