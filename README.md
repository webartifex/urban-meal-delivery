# Urban Meal Delivery

This repository holds code
analyzing the data of an undisclosed urban meal delivery platform
operating in France from January 2016 to January 2017.
The goal is to
optimize the platform's delivery process involving independent couriers.


## Structure

The analysis is structured into three aspects
that iteratively build on each other.

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
are structured in the [pyproject.toml](https://github.com/webartifex/urban-meal-delivery/blob/main/pyproject.toml) file
into dependencies related to only the `urban-meal-delivery` source code package
and dependencies used to run the [Jupyter](https://jupyter.org/) environment
with the analyses.

Contributions are welcome.
Use the [issues](https://github.com/webartifex/urban-meal-delivery/issues) tab.
The project is licensed under the [MIT license](https://github.com/webartifex/urban-meal-delivery/blob/main/LICENSE.txt).
