# WattWise AI — Electricity Consumption Advisor

A responsive local web application for estimating household electricity use, comparing appliances, and generating explainable rule-based energy-saving suggestions.

## Features
- Responsive dashboard for laptop, tablet, and mobile widths
- Appliance library with example wattage ranges and default estimates
- Add, edit, and delete appliances
- Wattage source labels: Estimated, Appliance label, Manufacturer specification, Measured
- Daily and monthly kWh and estimated cost calculations
- Doughnut and bar charts (drawn locally with CSS; no chart package required)
- Explainable rule-based recommendations
- What-if savings simulator
- CSV report export
- SQLite storage on the computer running the app
- Editable electricity tariff

## Requirements
- Python 3.10 or newer recommended
- VS Code
- Internet is not required for the app logic. The CSS includes an optional Google Fonts import; if offline, the browser falls back to system fonts.

## Run in VS Code

1. Extract the ZIP file.
2. Open the `wattwise_ai` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. Create a virtual environment (recommended):

   Windows:
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   macOS/Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

5. Install Flask:
   ```bash
   python -m pip install -r requirements.txt
   ```

6. Start the app:
   ```bash
   python app.py
   ```

7. Open the local address shown in the terminal, normally `http://127.0.0.1:5000`.

To stop the server, press `Ctrl+C` in the terminal.

## First use
1. Click **Add an appliance**.
2. Search for an appliance, such as Ceiling Fan or LED Bulb.
3. Select the suggestion. The suggested wattage and category fill in automatically.
4. Adjust quantity, hours per day, and days used per month.
5. Choose the correct wattage source. Keep `Estimated` if you have not verified the rating.
6. Save. Dashboard cards, charts, and recommendations update.
7. Click the tariff pill in the top-right area to change the rate per kWh.
8. Use the savings simulator to compare current and proposed usage.
9. Export a CSV report from the top-right button.

## Calculation method
- Daily kWh = watts × quantity × hours per day ÷ 1000
- Monthly kWh = daily kWh × days used per month
- Estimated energy cost = monthly kWh × entered rate per kWh

## Accuracy and ethics
- Catalog values and ranges are illustrative defaults, not verified values for every appliance/model.
- Use the appliance nameplate, manufacturer specification, or measured energy data when available.
- Rated wattage does not always equal average real-world draw. Refrigerators cycle, inverter ACs vary their power, and heating appliances may cycle.
- The displayed cost is an energy-charge estimate. Real utility bills may include tariff slabs, fixed charges, taxes, duties, and other adjustments.
- Recommendations are based on transparent rules and user-entered data; they are not guaranteed savings or a scientifically validated prediction.
- Household data is stored in `wattwise.db` locally in the folder. Delete that file to remove all saved application data (after closing the app).

## AI concepts to explain in your project viva
- Knowledge representation: appliance catalogue and rule set
- Rule-based expert system: rules flag high usage and long daily runtime
- Forward-style inference: entered facts are evaluated against rules to produce recommendations
- Explainable AI: each recommendation includes its reason
- Ethics: transparency, data minimization, user control, and honest uncertainty

## Project structure
```text
wattwise_ai/
├── app.py
├── requirements.txt
├── README.md
├── wattwise.db       # created automatically when app runs
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```
