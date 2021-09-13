# Urban Meal Delivery

This repository holds code
analyzing the data of an undisclosed urban meal delivery platform (UDP)
operating in France from January 2016 to January 2017.
The goal is to
optimize the platform's delivery process involving independent couriers.


## Structure

The analysis is structured into the following stages
that iteratively build on each other.


### Data Cleaning

The UDP provided its raw data as a PostgreSQL dump.
This [notebook](https://nbviewer.jupyter.org/github/webartifex/urban-meal-delivery/blob/main/research/01_clean_data.ipynb)
cleans the data extensively
and maps them onto the [ORM models](https://github.com/webartifex/urban-meal-delivery/tree/main/src/urban_meal_delivery/db)
defined in the `urban-meal-delivery` package
that is developed in the [src/](https://github.com/webartifex/urban-meal-delivery/tree/main/src) folder
and contains all source code to drive the analyses.

Due to a non-disclosure agreement with the UDP,
neither the raw nor the cleaned data are published as of now.
However, previews of the data can be seen throughout the [research/](https://github.com/webartifex/urban-meal-delivery/tree/main/research) folder.


### Tactical Demand Forecasting

Before any optimizations of the UDP's operations are done,
a **demand forecasting** system for *tactical* purposes is implemented.
To achieve that, the cities first undergo a **gridification** step
where each *pickup* location is assigned into a pixel on a "checker board"-like grid.
The main part of the source code that implements that is in this [file](https://github.com/webartifex/urban-meal-delivery/blob/main/src/urban_meal_delivery/db/grids.py#L60).
Visualizations of the various grids can be found in the [visualizations/](https://github.com/webartifex/urban-meal-delivery/tree/main/research/visualizations) folder
and in this [notebook](https://nbviewer.jupyter.org/github/webartifex/urban-meal-delivery/blob/main/research/03_grid_visualizations.ipynb).

Then, demand is aggregated on a per-pixel level
and different kinds of order time series are generated.
The latter are the input to different kinds of forecasting `*Model`s.
They all have in common that they predict demand into the *short-term* future (e.g., one hour)
and are thus used for tactical purposes, in particular predictive routing (cf., next section).
The details of how this works can be found in the first academic paper
published in the context of this research project
and titled "*Real-time Demand Forecasting for an Urban Delivery Platform*"
(cf., the [repository](https://github.com/webartifex/urban-meal-delivery-demand-forecasting) with the LaTeX files).
All demand forecasting related code is in the [forecasts/](https://github.com/webartifex/urban-meal-delivery/tree/main/src/urban_meal_delivery/forecasts) sub-package.


### Predictive Routing

### Shift & Capacity Planning


## Installation & Contribution

To play with the code developed for the analyses,
you can clone the project with [git](https://git-scm.com/)
and install the contained `urban-meal-delivery` package
and all its dependencies
in a [virtual environment](https://docs.python.org/3/tutorial/venv.html)
with [poetry](https://python-poetry.org/docs/):

`git clone https://github.com/webartifex/urban-meal-delivery.git`

and

`poetry install --extras research`

The `--extras` option is necessary as the non-develop dependencies
are structured in the [pyproject.toml](https://github.com/webartifex/urban-meal-delivery/blob/main/pyproject.toml) file
into dependencies related to only the `urban-meal-delivery` source code package
and dependencies used to run the [Jupyter](https://jupyter.org/) environment
with the analyses.

Contributions are welcome.
Use the [issues](https://github.com/webartifex/urban-meal-delivery/issues) tab.
The project is licensed under the [MIT license](https://github.com/webartifex/urban-meal-delivery/blob/main/LICENSE.txt).
