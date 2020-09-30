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
This [notebook](https://nbviewer.jupyter.org/github/webartifex/urban-meal-delivery/blob/develop/notebooks/00_clean_data.ipynb)
cleans the data extensively
and maps them onto the [ORM models](https://github.com/webartifex/urban-meal-delivery/tree/develop/src/urban_meal_delivery/db)
defined in the `urban-meal-delivery` package
that is developed in the [src/](https://github.com/webartifex/urban-meal-delivery/tree/develop/src) folder
and contains all source code to drive the analyses.

Due to a non-disclosure agreement with the UDP,
neither the raw nor the cleaned data are published as of now.
However, previews of the data can be seen throughout the [notebooks/](https://github.com/webartifex/urban-meal-delivery/tree/develop/notebooks) folders.


### Real-time Demand Forecasting

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
are structured in the [pyproject.toml](https://github.com/webartifex/urban-meal-delivery/blob/develop/pyproject.toml) file
into dependencies related to only the `urban-meal-delivery` source code package
and dependencies used to run the [Jupyter](https://jupyter.org/) environment
with the analyses.

Contributions are welcome.
Use the [issues](https://github.com/webartifex/urban-meal-delivery/issues) tab.
The project is licensed under the [MIT license](https://github.com/webartifex/urban-meal-delivery/blob/develop/LICENSE.txt).
