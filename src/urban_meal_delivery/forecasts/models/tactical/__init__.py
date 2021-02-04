"""Forecasting `*Model`s to predict demand for tactical purposes.

The `*Model`s in this module predict only a small number (e.g., one)
of time steps into the near future and are used to implement the UDP's
predictive routing strategies.

They are classified into "horizontal", "vertical", and "real-time" models
with respect to what historic data they are trained on and how often they
are re-trained on the day to be predicted. For the details, check section
"3.6 Forecasting Models" in the paper "Real-time Demand Forecasting for an
Urban Delivery Platform".

For the paper check:
    https://github.com/webartifex/urban-meal-delivery-demand-forecasting/blob/main/paper.pdf
    https://www.sciencedirect.com/science/article/pii/S1366554520307936
"""  # noqa:RST215
