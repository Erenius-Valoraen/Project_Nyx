import pandas as pd
import plotly.graph_objects as go
from lightweight_charts import Chart
from lightweight_charts.widgets import StreamlitChart
from pprint import pp
class CandlestickChart:
    def __init__(self, data, symbol=None):
        self.data = data
        self.symbol = symbol

    def process_data(self):
        # We filter out the last column (Volume) since it wasn't requested in the columns list.
        data_filtered = [row[:5] for row in self.data]

        # Define the column names
        columns = ['date', 'open', 'high', 'low', 'close']

        # Create the DataFrame
        df = pd.DataFrame(data_filtered, columns=columns)

        # Convert the 'date' column to datetime format, which automatically handles the '+05:30' timezone offset.
        df['date'] = pd.to_datetime(df['date'])
        df['date'] = df['date'].dt.strftime('%Y-%m-%d %H:%M')

        return df

    def render(self):
        df = self.process_data()
        pp(df)

        chart = StreamlitChart(width=900, height=600, toolbox=True)
        chart.legend(True)
        chart.topbar.textbox('symbol', self.symbol or 'Chart')
        chart.set(df)
        chart.load()



        # chart = Chart()
        # chart.set(df)
        # chart.show(block=True)

        # fig = go.Figure(data=[go.Candlestick(
        #     x=df['date'],
        #     open=df['open'],
        #     high=df['high'],
        #     low=df['low'],
        #     close=df['close']
        # )])

        # fig.update_layout(
        #     title='Candlestick Chart',
        #     yaxis_title='Price',
        #     xaxis_title='Date',
        #     xaxis_rangeslider_visible=False
        # )

        # fig.show()
