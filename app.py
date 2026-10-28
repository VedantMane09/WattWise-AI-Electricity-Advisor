from flask import Flask, render_template, request, jsonify, Response
import sqlite3
import csv
import io
import os
from datetime import datetime

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "wattwise.db")

# The ranges/defaults are illustrative starting points, not universal specifications.
# Replace them with manufacturer data or measured values whenever available.
APPLIANCE_CATALOG = [
    {"name": "LED Bulb", "category": "Lighting", "min_w": 5, "max_w": 15, "default_w": 9, "note": "Check bulb or packaging label."},
    {"name": "Ceiling Fan", "category": "Cooling", "min_w": 28, "max_w": 100, "default_w": 75, "note": "Motor rating and speed affect power use."},
    {"name": "Table Fan", "category": "Cooling", "min_w": 25, "max_w": 70, "default_w": 50, "note": "Check the appliance rating label."},
    {"name": "Television", "category": "Entertainment", "min_w": 40, "max_w": 200, "default_w": 100, "note": "Screen size and display type matter."},
    {"name": "Laptop", "category": "Computing", "min_w": 30, "max_w": 180, "default_w": 65, "note": "Adapter rating is not the same as constant actual draw."},
    {"name": "Desktop Computer", "category": "Computing", "min_w": 100, "max_w": 500, "default_w": 200, "note": "Actual draw depends on components and workload."},
    {"name": "Refrigerator", "category": "Kitchen", "min_w": 80, "max_w": 300, "default_w": 150, "note": "Compressor cycles on/off; rated watts alone can overestimate use."},
    {"name": "Air Conditioner", "category": "Cooling", "min_w": 700, "max_w": 2500, "default_w": 1500, "note": "Input power varies by capacity, inverter operation, and conditions."},
    {"name": "Washing Machine", "category": "Laundry", "min_w": 300, "max_w": 2000, "default_w": 500, "note": "Heater and wash program can change energy per cycle."},
    {"name": "Electric Iron", "category": "Household", "min_w": 700, "max_w": 2200, "default_w": 1200, "note": "Thermostat cycles; actual average may be lower."},
    {"name": "Microwave Oven", "category": "Kitchen", "min_w": 700, "max_w": 1800, "default_w": 1200, "note": "Input power differs from cooking output power."},
    {"name": "Electric Kettle", "category": "Kitchen", "min_w": 1000, "max_w": 2200, "default_w": 1500, "note": "Usually used for short periods."},
    {"name": "Water Heater / Geyser", "category": "Bathroom", "min_w": 1000, "max_w": 3000, "default_w": 2000, "note": "Actual use depends on heating duration and thermostat."},
    {"name": "Water Pump", "category": "Utility", "min_w": 250, "max_w": 1500, "default_w": 750, "note": "Use the motor nameplate rating where possible."},
    {"name": "Dishwasher", "category": "Kitchen", "min_w": 1200, "max_w": 2400, "default_w": 1800, "note": "Heating cycle affects energy per wash."},
    {"name": "Air Cooler", "category": "Cooling", "min_w": 100, "max_w": 250, "default_w": 180, "note": "Pump and fan operation affect power use."},
    {"name": "Rice Cooker", "category": "Kitchen", "min_w": 300, "max_w": 1000, "default_w": 700, "note": "Heating and keep-warm modes differ."},
    {"name": "Router / Modem", "category": "Electronics", "min_w": 5, "max_w": 25, "default_w": 12, "note": "Often operates continuously."},
    {"name": "Phone Charger", "category": "Electronics", "min_w": 5, "max_w": 30, "default_w": 15, "note": "Power varies by charger and charging stage."},
    {"name": "Other Appliance", "category": "Other", "min_w": 1, "max_w": 5000, "default_w": 100, "note": "Enter the actual rating if known."},
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                rate REAL NOT NULL DEFAULT 8.0,
                days_per_month INTEGER NOT NULL DEFAULT 30
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                watts REAL NOT NULL,
                quantity INTEGER NOT NULL,
                hours_per_day REAL NOT NULL,
                days_per_month INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'Estimated',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("INSERT OR IGNORE INTO settings (id, rate, days_per_month) VALUES (1, 8.0, 30)")

def settings():
    with get_db() as conn:
        row = conn.execute("SELECT rate, days_per_month FROM settings WHERE id=1").fetchone()
        return {"rate": float(row["rate"]), "days_per_month": int(row["days_per_month"])}

def get_items():
    s = settings()
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM appliances ORDER BY id DESC").fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["daily_kwh"] = item["watts"] * item["quantity"] * item["hours_per_day"] / 1000
        item["monthly_kwh"] = item["daily_kwh"] * item["days_per_month"]
        item["monthly_cost"] = item["monthly_kwh"] * s["rate"]
        items.append(item)
    return items

def summary(items, rate):
    total_kwh = sum(i["monthly_kwh"] for i in items)
    total_daily = sum(i["daily_kwh"] for i in items)
    total_cost = total_kwh * rate
    top = max(items, key=lambda x: x["monthly_kwh"], default=None)
    return {
        "total_monthly_kwh": total_kwh,
        "total_daily_kwh": total_daily,
        "total_monthly_cost": total_cost,
        "top_appliance": top["name"] if top else "—",
        "top_kwh": top["monthly_kwh"] if top else 0,
        "item_count": len(items)
    }

def safe_float(value, field, minimum=0, maximum=100000):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number.")
    if number < minimum or number > maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}.")
    return number

def recommendations(items, rate):
    if not items:
        return [{
            "level": "info",
            "title": "Start with your first appliance",
            "body": "Add appliances to estimate consumption and receive tailored energy-saving suggestions."
        }]
    total = sum(i["monthly_kwh"] for i in items)
    recs = []
    ranked = sorted(items, key=lambda x: x["monthly_kwh"], reverse=True)
    if total > 0 and ranked:
        top = ranked[0]
        share = top["monthly_kwh"] / total * 100
        if share >= 25:
            recs.append({
                "level": "high",
                "title": f"{top['name']} is your largest estimated consumer",
                "body": f"It accounts for about {share:.0f}% of the listed monthly usage ({top['monthly_kwh']:.1f} kWh). Review its usage schedule and actual rating before changing settings."
            })
        else:
            recs.append({
                "level": "info",
                "title": "Review your highest-use appliance",
                "body": f"{top['name']} has the highest estimated use at {top['monthly_kwh']:.1f} kWh/month. Small changes here may have a noticeable effect."
            })
    for item in ranked:
        if item["hours_per_day"] >= 8 and item["monthly_kwh"] > 0:
            recs.append({
                "level": "medium",
                "title": f"Check the daily runtime of {item['name']}",
                "body": f"It is entered as running {item['hours_per_day']:g} hours/day. If some usage is unnecessary, reducing it by 1 hour/day could save about {(item['watts'] * item['quantity'] / 1000 * item['days_per_month'] * rate):.2f} per month at your entered tariff, assuming constant rated power."
            })
            break
    high_cost = [i for i in ranked if i["monthly_cost"] >= 200]
    if high_cost:
        item = high_cost[0]
        recs.append({
            "level": "medium",
            "title": f"Review the cost estimate for {item['name']}",
            "body": f"The estimate is ₹{item['monthly_cost']:.2f}/month. For appliances that cycle or vary their power (such as refrigerators and inverter ACs), use measured kWh or manufacturer energy data for a better estimate."
        })
    recs.append({
        "level": "info",
        "title": "Improve estimate accuracy",
        "body": "Replace generic wattage estimates with the appliance nameplate or manufacturer specifications. A plug-in energy meter or smart meter reading can provide better real-world energy data for compatible appliances."
    })
    return recs[:4]

@app.route("/")
def index():
    init_db()
    return render_template("index.html", catalog=APPLIANCE_CATALOG, settings=settings())

@app.get("/api/state")
def api_state():
    init_db()
    s = settings()
    items = get_items()
    return jsonify({"items": items, "settings": s, "summary": summary(items, s["rate"]), "recommendations": recommendations(items, s["rate"])})

@app.get("/api/catalog")
def api_catalog():
    q = request.args.get("q", "").strip().lower()
    results = [x for x in APPLIANCE_CATALOG if q in x["name"].lower() or q in x["category"].lower()]
    return jsonify(results)

@app.post("/api/items")
def add_item():
    init_db()
    data = request.get_json(silent=True) or {}
    try:
        name = str(data.get("name", "")).strip()
        category = str(data.get("category", "Other")).strip() or "Other"
        if not name or len(name) > 80:
            raise ValueError("Enter an appliance name (maximum 80 characters).")
        watts = safe_float(data.get("watts"), "Wattage", 0.1, 100000)
        quantity = int(safe_float(data.get("quantity"), "Quantity", 1, 1000))
        hours = safe_float(data.get("hours_per_day"), "Hours per day", 0, 24)
        days = int(safe_float(data.get("days_per_month", 30), "Days per month", 1, 31))
        source = str(data.get("source", "Estimated"))
        if source not in ("Estimated", "Appliance label", "Manufacturer specification", "Measured"):
            source = "Estimated"
        with get_db() as conn:
            conn.execute(
                "INSERT INTO appliances (name, category, watts, quantity, hours_per_day, days_per_month, source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, category, watts, quantity, hours, days, source, datetime.now().isoformat(timespec="seconds"))
            )
        return jsonify({"ok": True})
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

@app.put("/api/items/<int:item_id>")
def edit_item(item_id):
    init_db()
    data = request.get_json(silent=True) or {}
    try:
        name = str(data.get("name", "")).strip()
        category = str(data.get("category", "Other")).strip() or "Other"
        if not name or len(name) > 80:
            raise ValueError("Enter an appliance name (maximum 80 characters).")
        watts = safe_float(data.get("watts"), "Wattage", 0.1, 100000)
        quantity = int(safe_float(data.get("quantity"), "Quantity", 1, 1000))
        hours = safe_float(data.get("hours_per_day"), "Hours per day", 0, 24)
        days = int(safe_float(data.get("days_per_month", 30), "Days per month", 1, 31))
        source = str(data.get("source", "Estimated"))
        if source not in ("Estimated", "Appliance label", "Manufacturer specification", "Measured"):
            source = "Estimated"
        with get_db() as conn:
            cur = conn.execute(
                "UPDATE appliances SET name=?, category=?, watts=?, quantity=?, hours_per_day=?, days_per_month=?, source=? WHERE id=?",
                (name, category, watts, quantity, hours, days, source, item_id)
            )
            if cur.rowcount == 0:
                return jsonify({"ok": False, "error": "Appliance not found."}), 404
        return jsonify({"ok": True})
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

@app.delete("/api/items/<int:item_id>")
def delete_item(item_id):
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM appliances WHERE id=?", (item_id,))
    return jsonify({"ok": True})

@app.post("/api/settings")
def update_settings():
    init_db()
    data = request.get_json(silent=True) or {}
    try:
        rate = safe_float(data.get("rate"), "Rate per unit", 0, 100000)
        days = int(safe_float(data.get("days_per_month", 30), "Days per month", 1, 31))
        with get_db() as conn:
            conn.execute("UPDATE settings SET rate=?, days_per_month=? WHERE id=1", (rate, days))
            conn.execute("UPDATE appliances SET days_per_month=?", (days,))
        return jsonify({"ok": True})
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

@app.post("/api/simulate")
def simulate():
    data = request.get_json(silent=True) or {}
    try:
        watts = safe_float(data.get("watts"), "Wattage", 0.1, 100000)
        quantity = int(safe_float(data.get("quantity"), "Quantity", 1, 1000))
        current = safe_float(data.get("current_hours"), "Current hours", 0, 24)
        proposed = safe_float(data.get("proposed_hours"), "Proposed hours", 0, 24)
        days = int(safe_float(data.get("days"), "Days per month", 1, 31))
        rate = safe_float(data.get("rate"), "Rate per unit", 0, 100000)
        current_kwh = watts * quantity * current * days / 1000
        proposed_kwh = watts * quantity * proposed * days / 1000
        saved_kwh = current_kwh - proposed_kwh
        return jsonify({
            "current_kwh": current_kwh,
            "proposed_kwh": proposed_kwh,
            "saved_kwh": saved_kwh,
            "saved_cost": saved_kwh * rate,
            "message": "This is a theoretical estimate assuming constant power while running. Negative savings means proposed usage is higher."
        })
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

@app.get("/report.csv")
def report_csv():
    init_db()
    s = settings()
    items = get_items()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["WattWise AI - Electricity Consumption Report"])
    writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")])
    writer.writerow(["Electricity rate (₹/kWh)", s["rate"]])
    writer.writerow([])
    writer.writerow(["Appliance", "Category", "Watts", "Quantity", "Hours/day", "Days/month", "Value source", "Daily kWh", "Monthly kWh", "Estimated monthly cost (₹)"])
    for i in items:
        writer.writerow([i["name"], i["category"], i["watts"], i["quantity"], i["hours_per_day"], i["days_per_month"], i["source"], round(i["daily_kwh"], 3), round(i["monthly_kwh"], 3), round(i["monthly_cost"], 2)])
    sm = summary(items, s["rate"])
    writer.writerow([])
    writer.writerow(["TOTAL", "", "", "", "", "", "", round(sm["total_daily_kwh"], 3), round(sm["total_monthly_kwh"], 3), round(sm["total_monthly_cost"], 2)])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=wattwise_energy_report.csv"})

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
