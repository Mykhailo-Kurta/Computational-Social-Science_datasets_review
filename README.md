# Computational Social Science — Data Visualization Projects

This repository contains two interactive data visualization projects created for the Computational Social Science course.

Both projects use HTML, CSS and JavaScript for the visualization part, while Python scripts are used for data preparation and analysis.

---

## Project 1 — Canada Climate Dashboard

The first project is an interactive dashboard based on Canadian climate data for 2025.

The dashboard includes:

- Monthly temperature comparison
- Interactive map of selected weather stations
- Temperature anomaly analysis
- Precipitation comparison
- Warmest and coldest station ranking
- Most and least precipitation station ranking

### Running the website

Open the project folder and start the website using a local web server.

For example, in Visual Studio Code:

1. Install the **Live Server** extension.
2. Open the project folder.
3. Open `index.html`.
4. Click **"Go Live"** in the bottom-right corner.
5. The dashboard will open in your browser.

A local web server is recommended because the website loads data from local files using JavaScript.

### Data preparation

`prepare_data.py` is used to process the original climate datasets and generate the compact data file used by the website.

The script uses relative paths, so the project can be moved to another computer without changing absolute Windows paths.

---

## Project 2 — Healthcare Spending & Health Outcomes

The second project explores the relationship between healthcare expenditure and selected health outcomes using World Health Organization (WHO) data.

The dashboard uses:

- Health expenditure per capita (USD), 2019
- Health expenditure as a percentage of GDP, 2019
- Breast cancer 5-year net survival, 2017–2021
- DTP3 vaccination coverage, 2019

The dashboard includes:

- Interactive world maps
- Healthcare expenditure comparisons
- Breast cancer survival visualization
- DTP3 vaccination comparison
- Interactive scatter plot
- Switching between expenditure measures on the X axis
- Switching between cancer survival and vaccination on the Y axis
- Comparison of observed outcomes with outcomes expected from a simple linear relationship

The analysis describes associations between the indicators and does not establish causal relationships.

### Running the website

The website can be opened using a local web server.

For example, in Visual Studio Code:

1. Install the **Live Server** extension.
2. Open the project folder.
3. Open the project's `index.html`.
4. Click **"Go Live"**.
5. The dashboard will open in your browser.

The website uses local CSV and map data files, so running it through a local web server is recommended.

### Data preparation

`prepare_data.py` reads the original WHO Excel files, selects the required periods, merges the datasets using WHO country codes, checks the resulting data and creates:

`who_health_2019.csv`

The processed dataset contains:

- `country_code`
- `country`
- `health_spending_usd`
- `health_spending_gdp`
- `cancer_survival`
- `dtp3`

---

## Dataset Size Parser

`parser.py` is a separate Python script used to determine the average dataset size on the websites being analyzed.

The script is not part of the visualization dashboards themselves. Its purpose is to collect and calculate dataset size information for the data analysis part of the assignment.

---

## Technologies

- HTML5
- CSS3
- JavaScript
- Python
- Pandas
- Chart.js
- D3.js
- TopoJSON
- Natural Earth / world-atlas map data
- OpenStreetMap / web mapping tools where applicable

---

## Project Structure

A typical project structure looks like this:

```text
project/
│
├── data/
│   ├── raw datasets
│   └── processed datasets
│
├── site/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── data files
│
├── prepare_data.py
├── parser.py
└── README.md
