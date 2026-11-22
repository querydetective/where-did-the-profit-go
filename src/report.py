"""Step 5: the deliverables a manager actually opens.
Reads reports/findings.json and the warehouse, writes:
  reports/profit_investigation.xlsx   (Excel workbook with native charts)
  reports/dashboard.html              (one self-contained page, no server needed)
  reports/executive_memo.md / .docx   (short memo with the recommendations)
  reports/experiment_decision.md / .docx and reports/customer_value_plan.md / .docx (Acts 2 and 3)"""
import base64, json, sqlite3
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches
from config import WAREHOUSE, REPORTS

F = json.load(open(REPORTS / "findings.json"))
P24, P25 = F["pnl"]["2024"], F["pnl"]["2025"]
B = F["bridge"]; S = F["ab_stats"]; AU = {r["year"]: r for r in F["aurora"]["by_year"]}
money = lambda v: f"${v / 1e6:,.2f}M" if abs(v) >= 1e6 else (f"${v / 1000:,.0f}K" if abs(v) >= 1000 else f"${v:,.0f}")
signed = lambda v: ("+" if v >= 0 else "-") + money(abs(v))
E = json.load(open(REPORTS / "experiment.json")); C = json.load(open(REPORTS / "customers.json"))
ER = {r["arm"]: r for r in E["results"]}
LABELS = dict(volume="More volume", discounts="Discounts", mix="Sales mix", shipping="Shipping", returns="Returns", product_cost="Product cost")

def headline():
    return (f"Net sales grew {F['growth']['net_sales_pct']}% in 2025, but contribution profit fell "
            f"{abs(F['growth']['profit_pct'])}%, from {money(P24['contribution_profit'])} to {money(P25['contribution_profit'])}.")

def recommendations():
    return [
        ("Stop the sitewide 20% discount",
         f"Discounts cost {money(-B['discounts'])} of profit. The September test showed 20% off moved conversion by only "
         f"+{S['conv_lift_pts']} points (p = {S['conv_p']}, not significant) while cutting product profit by "
         f"${-S['profit_diff_per_customer']:.2f} per customer (95% CI {S['profit_ci95'][0]} to {S['profit_ci95'][1]})."),
        ("Re-bid heavy-parcel shipping",
         f"Since April 2025 heavy orders go to SwiftShip at about twice the old rate. Shipping them at the ParcelPro heavy rate "
         f"would have saved {money(F['shipping_extra'])} in 2025."),
        ("Claim the Aurora lamp defect from the supplier",
         f"Aurora Standing Lamp returns jumped from {AU[2024]['return_rate_pct']}% to {AU[2025]['return_rate_pct']}%; "
         f"{AU[2025]['defective_units']} units came back 'Defective - flickering' (May to Oct 2025 batch), costing "
         f"{money(AU[2025]['return_cost'])}. Recover the cost and add an incoming quality check."),
        ("Price Smart Home for margin, not just volume",
         f"Smart Home earns about 20% product margin and grew to about a quarter of sales; the mix shift cost "
         f"{money(-B['mix'])}. Review pricing, bundles and ad spend for the category."),
        ("Fix the dashboard before the next board meeting",
         f"The current dashboard reads the raw exports and shows {F['naive_dashboard']['growth_pct']}% growth instead of "
         f"{F['growth']['net_sales_pct']}%: orders exported by both systems during the migration add about "
         f"{money(F['naive_dashboard']['inflated_by'])} of revenue that never happened."),
    ]

def experiment_points():
    b, c, a = ER["B"], ER["C"], E["annual"]
    mob = next(r for r in E["by_device"] if r["device"] == "mobile" and r["arm"] == "C")
    return [
        ("Ship the new product page (C), starting with mobile",
         f"Conversion rose from {ER['A']['conversion_pct']}% to {c['conversion_pct']}% (+{c['conv_lift_rel_pct']}%, p = {c['p']}, below the 0.025 bar for two comparisons). "
         f"On mobile the lift was +{mob['lift_rel_pct']}%. Profit per visitor: +${c['profit_diff_per_visitor']:.2f} (97.5% CI {c['profit_ci'][0]} to {c['profit_ci'][1]}): "
         f"likely positive, about {money(a['C_profit'])} a year, with no discount and no rise in returns."),
        ("Do not launch the 10% off banner (B)",
         f"Conversion +{b['conv_lift_rel_pct']}% (p = {b['p']}, not significant) and profit per visitor fell ${-b['profit_diff_per_visitor']:.2f} "
         f"(CI {b['profit_ci'][0]} to {b['profit_ci'][1]}): about {money(-a['B_profit'])} a year lost. Its strong first weeks were a novelty effect."),
        ("Keep the testing rules",
         "Size the test before launch, check the split, remove bots and duplicate visitors, and decide only at the planned end date."),
    ]

def customer_points():
    p, m = C["pareto"], C["model"]; plan = {r["segment"]: r for r in C["plan"]}; ch = {r["acquisition_channel"]: r for r in C["channels"]}
    return [
        ("Protect the Champions",
         f"The top 20% of customers earn {p['top20_share']}% of profit. Champions are {plan['Champions']['customers_now']} customers worth about "
         f"${plan['Champions']['expected_12m_profit']:.0f} each next year: early access and service, not discounts."),
        ("Turn new customers into second-time buyers",
         f"New / promising customers are worth about ${plan['New / promising']['expected_12m_profit']:.0f} each next year, more than Loyal ones. "
         f"A welcome series that earns the second order is the best use of budget (up to ${plan['New / promising']['max_spend_per_customer']:.0f} per customer)."),
        ("Move budget from Paid Social to Email & Referral",
         f"A 2024 Paid Social customer earned ${ch['Paid Social']['two_year_profit']:.0f} over two years, against ${ch['Paid Social']['spend_per_new_customer']:.0f} "
         f"of 2025 spend per new customer. Email & Referral: ${ch['Email & Referral']['two_year_profit']:.0f} earned for ${ch['Email & Referral']['spend_per_new_customer']:.0f}."),
        ("Target with the model, not past spend",
         f"Picking the top 20% by the model reached {m['capture_model']}% of the next half-year's profit, vs {m['capture_segment']}% with RFM segments "
         f"and {m['capture_past_profit']}% by past profit."),
    ]

def small_memo(path, title, re_, bottom, points, chart, method):
    md = f"# Memo: {title}\n\n**To:** Leadership team, Harbor & Hearth\n**From:** Data analytics\n**Re:** {re_}\n\n## Bottom line\n{bottom}\n\n## Recommendations\n" + \
         "\n".join(f"{i}. **{t}.** {d}" for i, (t, d) in enumerate(points, 1)) + f"\n\n## How we know\n{method}\n"
    (REPORTS / f"{path}.md").write_text(md, encoding="utf-8")
    doc = Document(); st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    doc.add_heading(f"Memo: {title}", 0)
    for lab, v in (("To:", "Leadership team, Harbor & Hearth"), ("From:", "Data analytics"), ("Re:", re_)):
        p = doc.add_paragraph(); p.add_run(lab + " ").bold = True; p.add_run(v)
    doc.add_heading("Bottom line", 1); doc.add_paragraph(bottom)
    doc.add_picture(str(REPORTS / "charts" / chart), width=Inches(6.3))
    doc.add_heading("Recommendations", 1)
    for t, d in points:
        p = doc.add_paragraph(style="List Number"); p.add_run(t + ". ").bold = True; p.add_run(d)
    doc.add_heading("How we know", 1); doc.add_paragraph(method)
    doc.save(REPORTS / f"{path}.docx"); return REPORTS / f"{path}.docx"

def memo_act2():
    return small_memo("experiment_decision", "the website test", "Follow-up experiment, Jan to Apr 2026",
        f"The new product page (C) raised conversion by {ER['C']['conv_lift_rel_pct']}% and should ship, starting with mobile. "
        f"The 10% off banner (B) did not reliably raise conversion and lost money on every visitor.",
        experiment_points(), "08_exp_results.png",
        f"{E['cleaning']['clean_visitors']:,} visitors after removing {E['cleaning']['bots']:,} bot rows and {E['cleaning']['multi_arm_visitors']} visitors seen in two arms. "
        f"Sample size was set before launch ({E['plan']['visitors_per_arm']:,} per arm). The split was even after cleaning (p = {E['srm']['clean_p']}), "
        "and the decision was made at the planned end date, not when a daily p-value first dipped.")

def memo_act3():
    return small_memo("customer_value_plan", "which customers to invest in", "Customer value and marketing spend",
        f"{C['pareto']['top20_share']}% of profit comes from the top 20% of customers. Spend should follow expected value: protect Champions, "
        "win the second order from new customers, and move acquisition budget toward channels whose customers pay back.",
        customer_points(), "12_segments.png",
        "Every order's contribution profit was rebuilt from the warehouse and reconciles to the P&L to the dollar. Segments use recency and frequency; "
        "they were checked by setting them on 30 Jun 2025 and watching who bought from July to December. The model was tested on customers it never saw.")

# ---------------------------------------------------------------- Excel
def excel():
    con = sqlite3.connect(WAREHOUSE)
    monthly = pd.read_sql("SELECT * FROM mart_monthly_pnl ORDER BY month", con)
    path = REPORTS / "profit_investigation.xlsx"
    with pd.ExcelWriter(path, engine="xlsxwriter") as xw:
        wb = xw.book
        h1 = wb.add_format({"bold": True, "font_size": 16, "font_color": "#1e3a5f"})
        hd = wb.add_format({"bold": True, "bg_color": "#1e3a5f", "font_color": "white", "border": 1})
        usd = wb.add_format({"num_format": "$#,##0"}); pct = wb.add_format({"num_format": "0.0%"})
        wrap = wb.add_format({"text_wrap": True, "valign": "top"}); bold_top = wb.add_format({"bold": True, "text_wrap": True, "valign": "top"})

        ws = wb.add_worksheet("Summary"); xw.sheets["Summary"] = ws
        ws.write("A1", "Harbor & Hearth: where did the profit go?", h1); ws.write("A2", headline())
        ws.write_row("A4", ["Measure", "2024", "2025", "Change"], hd)
        rows = [("Net sales", "net_sales"), ("Discounts", "discounts"), ("Refunds", "refunds"), ("Product cost (COGS)", "cogs"),
                ("Shipping", "shipping"), ("Contribution profit", "contribution_profit"), ("Marketing (shown separately)", "marketing")]
        for i, (lab, k) in enumerate(rows, start=4):
            ws.write(i, 0, lab); ws.write(i, 1, P24[k], usd); ws.write(i, 2, P25[k], usd)
            ws.write_formula(i, 3, f"=C{i + 1}/B{i + 1}-1", pct, P25[k] / P24[k] - 1)
        ws.write("A13", "Profit bridge 2024 to 2025", h1); ws.write_row("A14", ["Step", "Effect on profit"], hd)
        steps = [("2024 profit", P24["contribution_profit"])] + [(LABELS[k], v) for k, v in B.items()] + [("2025 profit", P25["contribution_profit"])]
        for i, (lab, v) in enumerate(steps, start=14): ws.write(i, 0, lab); ws.write(i, 1, v, usd)
        ws.write(14 + len(steps), 0, "Difference (rounding only)"); ws.write_formula(14 + len(steps), 1, f"=SUM(B15:B{14 + len(steps) - 1})-B{14 + len(steps)}", usd, round(sum(v for _, v in steps[:-1]) - steps[-1][1]))
        ch = wb.add_chart({"type": "bar"}); ch.add_series({"name": "Effect on profit", "categories": ["Summary", 15, 0, 20, 0],
              "values": ["Summary", 15, 1, 20, 1],
              "points": [{"fill": {"color": "#16a34a" if v >= 0 else "#dc2626"}} for _, v in steps[1:-1]]})
        ch.set_title({"name": "What moved profit"}); ch.set_legend({"none": True}); ch.set_y_axis({"reverse": True, "label_position": "low"}); ch.set_x_axis({"num_format": "$#,##0,K", "major_gridlines": {"visible": True, "line": {"color": "#e5e7eb"}}})
        ws.insert_chart("F4", ch, {"x_scale": 1.25, "y_scale": 1.25})
        ws.write("A26", "Recommendations", h1)
        for i, (t, d) in enumerate(recommendations(), start=26):
            ws.write(i, 0, f"{i - 25}. {t}", bold_top); ws.merge_range(i, 1, i, 12, d, wrap); ws.set_row(i, 48)
        ws.set_column("A:A", 34); ws.set_column("B:C", 16); ws.set_column("D:D", 12)
        ws.set_landscape(); ws.fit_to_pages(1, 1); ws.hide_gridlines(2)

        monthly.to_excel(xw, "Monthly P&L", index=False)
        m = xw.sheets["Monthly P&L"]; m.set_column(0, 0, 10); m.set_column(1, len(monthly.columns), 14, usd); m.freeze_panes(1, 0)
        c2 = wb.add_chart({"type": "line"}); n = len(monthly); ci = list(monthly.columns).index("contribution_profit"); si = list(monthly.columns).index("net_sales")
        for col, color in ((si, "#94a3b8"), (ci, "#1e3a5f")):
            c2.add_series({"name": ["Monthly P&L", 0, col], "categories": ["Monthly P&L", 1, 0, n, 0], "values": ["Monthly P&L", 1, col, n, col], "line": {"color": color, "width": 2.5}})
        c2.set_title({"name": "Net sales vs contribution profit"}); m.insert_chart("B" + str(n + 4), c2, {"x_scale": 2, "y_scale": 1.3})

        for name, key in (("A-B test", "ab_test"), ("Discounts", "discounts"), ("Shipping", "shipping"), ("Returns 2025", "returns_top_2025"),
                          ("Category mix", "mix"), ("Cleaning log", "cleaning_log")):
            df = pd.DataFrame(F[key]); df.to_excel(xw, name, index=False)
            sh = xw.sheets[name]; sh.set_column(0, len(df.columns), 18); sh.freeze_panes(1, 0)
        pd.DataFrame(E["results"]).drop(columns=["profit_ci"]).to_excel(xw, "Experiment 2026", index=False)
        pd.DataFrame(E["by_device"]).to_excel(xw, "Experiment 2026", index=False, startrow=6)
        xw.sheets["Experiment 2026"].set_column(0, 20, 16)
        pd.DataFrame(C["segments"]).to_excel(xw, "Customer segments", index=False)
        pd.DataFrame(C["plan"]).to_excel(xw, "Customer segments", index=False, startrow=9)
        pd.DataFrame(C["channels"]).to_excel(xw, "Customer segments", index=False, startrow=18)
        xw.sheets["Customer segments"].set_column(0, 10, 20)
        ab = xw.sheets["A-B test"]; ab.write("A5", "Statistics", h1)
        for i, (k, v) in enumerate(S.items(), start=5): ab.write(i, 0, k); ab.write(i, 1, str(v))
    return path

# ---------------------------------------------------------------- HTML dashboard
def img(name):
    return "data:image/png;base64," + base64.b64encode((REPORTS / "charts" / name).read_bytes()).decode()

def dashboard():
    kpis = [("Net sales 2025", money(P25["net_sales"]), f"+{F['growth']['net_sales_pct']}% vs 2024", "up"),
            ("Contribution profit 2025", money(P25["contribution_profit"]), f"{F['growth']['profit_pct']}% vs 2024", "down"),
            ("Discounts given", money(P25["discounts"]), f"was {money(P24['discounts'])} in 2024", "down"),
            ("Aurora lamp return rate", f"{AU[2025]['return_rate_pct']}%", f"was {AU[2024]['return_rate_pct']}% in 2024", "down")]
    charts = [("02_profit_bridge.png", "Where the profit went"), ("01_sales_vs_profit.png", "Sales went up, profit went down"),
              ("03_ab_test.png", "The discount test: more buyers? Not proven. Less profit? Yes."), ("04_shipping.png", "Heavy-parcel shipping doubled in April 2025"),
              ("05_aurora_returns.png", "One lamp, one bad batch"), ("06_mix.png", "More low-margin Smart Home"), ("07_cohorts.png", "Customers still come back")]
    k_html = "".join(f'<div class="kpi {c}"><div class="lab">{l}</div><div class="val">{v}</div><div class="sub">{s}</div></div>' for l, v, s, c in kpis)
    r_html = "".join(f"<li><b>{t}.</b> {d}</li>" for t, d in recommendations())
    c_html = "".join(f'<figure><figcaption>{t}</figcaption><img src="{img(f)}" alt="{t}"></figure>' for f, t in charts)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Harbor &amp; Hearth Profit Review</title><style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#14213d;--dim:#5b6475;--navy:#1e3a5f;--red:#dc2626;--green:#16a34a;--line:#e3e6ec}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,Segoe UI,Roboto,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:28px 16px 60px}}h1{{margin:0 0 4px;font-size:28px}}.lead{{color:var(--dim);margin:0 0 22px;max-width:70ch}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:22px}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;border-top:4px solid var(--navy)}}
.kpi.up{{border-top-color:var(--green)}}.kpi.down{{border-top-color:var(--red)}}.lab{{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim)}}
.val{{font-size:30px;font-weight:700;margin:4px 0}}.sub{{color:var(--dim);font-size:13px}}
section{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 22px;margin-bottom:22px}}
ol{{margin:8px 0 0;padding-left:22px}}li{{margin:6px 0}}figure{{margin:0 0 22px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}}
figcaption{{font-weight:700;margin:0 0 8px}}figure img{{width:100%;height:auto;display:block}}footer{{color:var(--dim);font-size:13px}}
</style></head><body><main>
<h1>Where did the profit go?</h1><p class="lead">Harbor &amp; Hearth, 2024 vs 2025. {headline()}</p>
<div class="kpis">{k_html}</div>
<section><h2 style="margin:0">What to do</h2><ol>{r_html}</ol></section>
{c_html}
<h1 style="margin-top:36px">Act 2: the follow-up test</h1><p class="lead">Jan to Apr 2026 · {E['cleaning']['clean_visitors']:,} visitors · three arms</p>
<section><ol>{"".join(f"<li><b>{t}.</b> {d}</li>" for t, d in experiment_points())}</ol></section>
{"".join(f'<figure><figcaption>{t}</figcaption><img src="{img(f)}" alt="{t}"></figure>' for f, t in (("08_exp_results.png", "Results: conversion and profit per visitor"), ("09_exp_peeking.png", "Why we waited for the planned end date"), ("10_exp_device.png", "The new page works on mobile")))}
<h1 style="margin-top:36px">Act 3: which customers to invest in</h1><p class="lead">{C['pareto']['buyers']:,} customers who bought in 2024-2025</p>
<section><ol>{"".join(f"<li><b>{t}.</b> {d}</li>" for t, d in customer_points())}</ol></section>
{"".join(f'<figure><figcaption>{t}</figcaption><img src="{img(f)}" alt="{t}"></figure>' for f, t in (("11_pareto.png", "A few customers carry the profit"), ("12_segments.png", "Segments: customers vs profit"), ("13_holdout.png", "Segments predict who buys again"), ("14_targeting.png", "The model finds more of next year's profit"), ("15_channels.png", "Value by acquisition channel")))}
<footer>Built from the Harbor &amp; Hearth warehouse by run_pipeline.py. All data is synthetic. Contribution profit = net sales - refunds - product cost (net of resellable returns) - shipping; marketing is reported separately.</footer>
</main></body></html>"""
    path = REPORTS / "dashboard.html"; path.write_text(html, encoding="utf-8"); return path

# ---------------------------------------------------------------- Memo
def memo():
    bridge_lines = "\n".join(f"| {LABELS[k]} | {signed(v)} |" for k, v in sorted(B.items(), key=lambda kv: (kv[0] != "volume", kv[1])))
    recs = "\n".join(f"{i}. **{t}.** {d}" for i, (t, d) in enumerate(recommendations(), 1))
    md = f"""# Memo: where did the profit go?

**To:** Leadership team, Harbor & Hearth
**From:** Data analytics
**Re:** 2025 profit decline

## Bottom line
{headline()} Growth was real, but three business decisions and one supplier problem gave more than all of it back.

## What moved profit (2024 to 2025)
| Driver | Effect on contribution profit |
|---|---|
{bridge_lines}
| **Total change** | **{signed(P25['contribution_profit'] - P24['contribution_profit'])}** |

## Recommendations
{recs}

## How we know
Seven raw exports from two order systems were cleaned (time zones, SKU case, test orders, migration duplicates), loaded into a SQLite warehouse with fact and dimension tables, and checked by 11 automated data-quality tests. Every figure above comes from that warehouse and is reproduced by one command: `python run_pipeline.py`.
"""
    (REPORTS / "executive_memo.md").write_text(md, encoding="utf-8")
    doc = Document(); st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    doc.add_heading("Memo: where did the profit go?", 0)
    for lab, v in (("To:", "Leadership team, Harbor & Hearth"), ("From:", "Data analytics"), ("Re:", "2025 profit decline")):
        p = doc.add_paragraph(); p.add_run(lab + " ").bold = True; p.add_run(v)
    doc.add_heading("Bottom line", 1); doc.add_paragraph(headline() + " Growth was real, but three business decisions and one supplier problem gave more than all of it back.")
    doc.add_heading("What moved profit (2024 to 2025)", 1)
    t = doc.add_table(rows=1, cols=2); t.style = "Light Grid Accent 1"; t.rows[0].cells[0].text = "Driver"; t.rows[0].cells[1].text = "Effect on contribution profit"
    for k, v in sorted(B.items(), key=lambda kv: (kv[0] != "volume", kv[1])):
        r = t.add_row().cells; r[0].text = LABELS[k]; r[1].text = signed(v)
    r = t.add_row().cells; r[0].text = "Total change"; r[1].text = signed(P25["contribution_profit"] - P24["contribution_profit"])
    doc.add_picture(str(REPORTS / "charts" / "02_profit_bridge.png"), width=Inches(6.3))
    doc.add_heading("Recommendations", 1)
    for tt, d in recommendations():
        p = doc.add_paragraph(style="List Number"); p.add_run(tt + ". ").bold = True; p.add_run(d)
    doc.add_heading("How we know", 1)
    doc.add_paragraph("Seven raw exports from two order systems were cleaned (time zones, SKU case, test orders, migration duplicates), loaded into a SQLite "
                      "warehouse with fact and dimension tables, and checked by 11 automated data-quality tests. Every figure comes from that warehouse "
                      "and is reproduced by one command: python run_pipeline.py.")
    doc.save(REPORTS / "executive_memo.docx")
    return REPORTS / "executive_memo.docx"

def main():
    print("Writing reports")
    for f in (excel, dashboard, memo, memo_act2, memo_act3): print("  saved", f().name)

if __name__ == "__main__":
    main()
