"""Build portable Power BI data marts and six evidence-based page mockups."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
OUT = ROOT / "powerbi" / "data"
MOCK = ROOT / "powerbi" / "mockups"
NAVY, TEAL, AQUA, AMBER, RED, GREY, BG = (
    "#0B3A53", "#147D92", "#27A6A1", "#E9A23B", "#C5524A", "#6F7D89", "#F5F7F9"
)


def _read_json(path: Path) -> dict[str, float]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_data() -> dict[str, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {
        "segment_performance": ART / "metrics" / "segment_performance.csv",
        "pricing_scores": ART / "pricing" / "policy_pricing_scores.csv",
        "reserve_quarter": ART / "reserving" / "reserve_by_accident_quarter.csv",
        "development_factors": ART / "reserving" / "development_factors.csv",
        "claim_triage": ART / "fraud" / "claim_triage_scores.csv",
        "frequency_coefficients": ART / "pricing" / "frequency_coefficients.csv",
        "severity_coefficients": ART / "pricing" / "severity_coefficients.csv",
    }
    frames = {name: pd.read_csv(path) for name, path in sources.items()}
    # Synthetic truth remains in the source artifact for offline evaluation, but
    # is deliberately removed from the operational Power BI claim table.
    frames["claim_triage"] = frames["claim_triage"].drop(
        columns=["fraud_synthetic_truth", "ultimate_incurred_synthetic_truth"]
    )
    for name, frame in frames.items():
        frame.to_csv(OUT / f"{name}.csv", index=False)

    triangle = pd.read_csv(ART / "reserving" / "cumulative_paid_triangle.csv")
    triangle = triangle.melt(
        id_vars="accident_quarter", var_name="development_quarter", value_name="cumulative_paid"
    ).dropna(subset=["cumulative_paid"])
    triangle["development_quarter"] = triangle["development_quarter"].astype(int)
    triangle.to_csv(OUT / "paid_triangle_long.csv", index=False)
    frames["paid_triangle_long"] = triangle

    portfolio = _read_json(ART / "metrics" / "portfolio_kpis.json")
    portfolio["valuation_date"] = _read_json(ART / "run_manifest.json")["valuation_date"]
    pd.DataFrame([portfolio]).to_csv(OUT / "portfolio_kpis.csv", index=False)

    validation_rows: list[dict[str, object]] = []
    for module, rel_path in {
        "pricing": "pricing/pricing_metrics.json",
        "reserving": "reserving/reserve_metrics.json",
        "fraud_triage": "fraud/triage_metrics.json",
    }.items():
        for metric, value in _read_json(ART / rel_path).items():
            validation_rows.append({"module": module, "metric": metric, "value": value})
    pd.DataFrame(validation_rows).to_csv(OUT / "validation_kpis.csv", index=False)
    return frames | {"portfolio": pd.DataFrame([portfolio])}


def _canvas(title: str, subtitle: str):
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.text(0.04, 0.95, title, fontsize=20, weight="bold", color=NAVY)
    fig.text(0.04, 0.915, subtitle, fontsize=9, color=GREY)
    return fig


def _card(fig, x, label, value, color=NAVY):
    ax = fig.add_axes([x, 0.79, 0.205, 0.095], facecolor="white")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_color("#DDE4E8")
    ax.text(0.04, 0.65, label, transform=ax.transAxes, fontsize=9, color=GREY)
    ax.text(0.04, 0.16, value, transform=ax.transAxes, fontsize=18, weight="bold", color=color)


def _style(ax, title):
    ax.set_facecolor("white"); ax.set_title(title, loc="left", fontsize=11, weight="bold", color=NAVY)
    ax.grid(axis="y", alpha=.15)
    for spine in ax.spines.values(): spine.set_color("#DDE4E8")
    ax.tick_params(labelsize=8, colors=GREY)


def _save(fig, name):
    fig.text(.04, .018, "SYNTHETIC DATA • analytical indication • human decision support", fontsize=8, color=RED)
    fig.savefig(MOCK / name, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def _mockups(f: dict[str, pd.DataFrame]) -> None:
    MOCK.mkdir(parents=True, exist_ok=True)
    k = f["portfolio"].iloc[0]
    seg = f["segment_performance"]
    veh = seg[seg.dimension == "vehicle_segment"].sort_values("earned_premium")

    fig = _canvas("Executive Technical Performance", "Is the portfolio technically profitable, and where is action required?")
    _card(fig, .04, "Earned premium", f"₺{k.earned_premium/1e9:.2f}B")
    _card(fig, .275, "Incurred claims", f"₺{k.incurred_claims/1e6:.1f}M")
    _card(fig, .51, "Loss ratio", f"{k.loss_ratio:.1%}", AMBER)
    _card(fig, .745, "Combined ratio", f"{k.combined_ratio:.1%}", RED)
    ax = fig.add_axes([.04,.46,.44,.27]); _style(ax,"Premium and incurred claims by vehicle segment")
    y=np.arange(len(veh)); ax.barh(y,veh.earned_premium/1e6,color=TEAL,label="Earned premium"); ax.barh(y,veh.incurred_claims/1e6,color=AMBER,alpha=.85,label="Incurred")
    ax.set_yticks(y,veh.segment); ax.legend(fontsize=8,frameon=False)
    ax = fig.add_axes([.53,.46,.43,.27]); _style(ax,"Loss ratio by vehicle segment")
    colors=[RED if v>.75 else TEAL for v in veh.loss_ratio]; ax.barh(y,veh.loss_ratio,color=colors); ax.axvline(.75,color=RED,ls="--",lw=1); ax.set_yticks(y,veh.segment); ax.xaxis.set_major_formatter(lambda x,p:f"{x:.0%}")
    ax=fig.add_axes([.04,.09,.92,.28]); _style(ax,"Management attention table")
    ax.axis("off"); t=veh.sort_values("loss_ratio",ascending=False)[["segment","policy_count","claim_frequency","average_severity","loss_ratio"]].head(6).copy(); t.claim_frequency=t.claim_frequency.map("{:.1%}".format); t.average_severity=t.average_severity.map(lambda x:f"₺{x/1000:.0f}K"); t.loss_ratio=t.loss_ratio.map("{:.1%}".format)
    ax.table(cellText=t.values,colLabels=["Segment","Policies","Frequency","Severity","Loss ratio"],loc="center",cellLoc="left",colLoc="left").scale(1,1.45)
    _save(fig,"01_executive_performance.png")

    fig=_canvas("Frequency & Severity Drivers","Separate claim occurrence from claim cost before pricing action")
    _card(fig,.04,"Claim frequency",f"{k.claim_frequency:.2%}"); _card(fig,.275,"Average severity",f"₺{k.average_incurred_severity/1000:.0f}K"); _card(fig,.51,"Claim count",f"{int(k.claim_count):,}"); _card(fig,.745,"Loss cost",f"₺{k.incurred_claims/k.exposure_years:,.0f}")
    ax=fig.add_axes([.05,.16,.55,.55]); _style(ax,"Vehicle segments: frequency × severity")
    ax.scatter(veh.claim_frequency,veh.average_severity,s=np.sqrt(veh.incurred_claims)/8,c=veh.loss_ratio,cmap="RdYlGn_r",edgecolor="white",lw=1)
    for _,r in veh.iterrows(): ax.annotate(r.segment,(r.claim_frequency,r.average_severity),xytext=(5,4),textcoords="offset points",fontsize=8)
    ax.axvline(k.claim_frequency,color=GREY,ls="--"); ax.axhline(k.average_incurred_severity,color=GREY,ls="--"); ax.xaxis.set_major_formatter(lambda x,p:f"{x:.0%}"); ax.yaxis.set_major_formatter(lambda x,p:f"₺{x/1000:.0f}K")
    coef=f["frequency_coefficients"].query("feature != 'intercept'").assign(distance=lambda d:(d.multiplicative_effect-1).abs()).nlargest(8,"distance").sort_values("multiplicative_effect")
    ax=fig.add_axes([.65,.16,.31,.55]); _style(ax,"Largest frequency model effects"); ax.barh(coef.feature,coef.multiplicative_effect,color=[RED if x>1 else TEAL for x in coef.multiplicative_effect]); ax.axvline(1,color=GREY,lw=1)
    _save(fig,"02_frequency_severity.png")

    p=f["pricing_scores"]
    fig=_canvas("Pricing Adequacy & Scenario Review","Current premium compared with model-indicated technical premium")
    indicated=p.indicated_technical_premium.sum(); adequacy=p.annual_written_premium.sum()/indicated; under=(p.pricing_action=="Review increase").mean()
    _card(fig,.04,"Written premium",f"₺{p.annual_written_premium.sum()/1e9:.2f}B"); _card(fig,.275,"Indicated premium",f"₺{indicated/1e9:.2f}B"); _card(fig,.51,"Adequacy index",f"{adequacy:.2f}",RED if adequacy<1 else TEAL); _card(fig,.745,"Increase review",f"{under:.1%}",AMBER)
    ax=fig.add_axes([.04,.15,.45,.56]); _style(ax,"Pricing adequacy distribution"); ax.hist(p.pricing_adequacy_index.clip(0,2.5),bins=35,color=TEAL,alpha=.9); ax.axvline(1,color=RED,ls="--")
    action=p.groupby("pricing_action").agg(policies=("policy_id","count"),premium_gap=("indicated_technical_premium","sum"),current=("annual_written_premium","sum")); action["gap"]=action.premium_gap-action.current
    ax=fig.add_axes([.56,.15,.40,.56]); _style(ax,"Policies and indicated premium gap")
    ax.bar(action.index,action.policies,color=[RED,TEAL,AMBER][:len(action)]); ax.tick_params(axis="x",rotation=12)
    for i,v in enumerate(action.policies): ax.text(i,v,f"{v:,}\n₺{action.gap.iloc[i]/1e6:.0f}M",ha="center",va="bottom",fontsize=8)
    _save(fig,"03_pricing_adequacy.png")

    c=f["claim_triage"]
    fig=_canvas("Claims Operations & Open Inventory","Where are claim backlogs and delayed files accumulating?")
    open_c=c[c.claim_status=="Open"]
    _card(fig,.04,"Open claims",f"{len(open_c):,}"); _card(fig,.275,"Open claim rate",f"{len(open_c)/len(c):.1%}"); _card(fig,.51,"Case reserve",f"₺{c.case_reserve.sum()/1e6:.1f}M"); _card(fig,.745,"Avg report delay",f"{c.report_delay_days.mean():.1f} days")
    mix=pd.crosstab(c.claim_type,c.claim_status)
    ax=fig.add_axes([.04,.16,.44,.55]); _style(ax,"Claim status by type"); mix.plot.barh(stacked=True,ax=ax,color=[TEAL,AMBER]); ax.legend(frameon=False,fontsize=8)
    ageing=pd.cut((pd.Timestamp("2025-12-31")-pd.to_datetime(open_c.report_date)).dt.days,[-1,30,90,180,365,9999],labels=["0–30","31–90","91–180","181–365","365+"]).value_counts().sort_index()
    ax=fig.add_axes([.55,.16,.41,.55]); _style(ax,"Open inventory ageing"); ax.bar(ageing.index.astype(str),ageing.values,color=[TEAL,TEAL,AMBER,RED,RED])
    for i,v in enumerate(ageing.values): ax.text(i,v,f"{v:,}",ha="center",va="bottom",fontsize=8)
    _save(fig,"04_claims_operations.png")

    r=f["reserve_quarter"]; tri=f["paid_triangle_long"]; piv=tri.pivot(index="accident_quarter",columns="development_quarter",values="cumulative_paid")
    fig=_canvas("Reserving & IBNR","Method comparison, development maturity, and synthetic backtest")
    _card(fig,.04,"Latest paid",f"₺{r.latest_paid.sum()/1e6:.1f}M"); _card(fig,.275,"Chain Ladder IBNR",f"₺{r.chain_ladder_ibnr.sum()/1e6:.1f}M"); _card(fig,.51,"BF IBNR",f"₺{r.bf_ibnr.sum()/1e6:.1f}M"); _card(fig,.745,"Method gap",f"₺{(r.chain_ladder_ibnr.sum()-r.bf_ibnr.sum())/1e6:.1f}M",AMBER)
    ax=fig.add_axes([.04,.14,.43,.57]); _style(ax,"Cumulative paid triangle (₺M)"); im=ax.imshow(piv/1e6,aspect="auto",cmap="Blues"); ax.set_yticks(range(len(piv.index)),piv.index); ax.set_xticks(range(len(piv.columns)),piv.columns); fig.colorbar(im,ax=ax,shrink=.7)
    ax=fig.add_axes([.54,.14,.42,.57]); _style(ax,"Ultimate by accident quarter"); x=np.arange(len(r)); ax.plot(x,r.chain_ladder_ultimate/1e6,color=NAVY,marker="o",label="Chain Ladder"); ax.plot(x,r.bf_ultimate/1e6,color=AMBER,marker="o",label="BF"); ax.bar(x,r.latest_paid/1e6,color=TEAL,alpha=.5,label="Latest paid"); ax.set_xticks(x,r.accident_quarter,rotation=45); ax.legend(frameon=False,fontsize=8)
    _save(fig,"05_reserving_ibnr.png")

    reviewed=c[c.review_recommended.astype(str).str.lower().isin(["true","1"])]
    tm=_read_json(ART/"fraud"/"triage_metrics.json")
    fig=_canvas("Human Review Queue & Governance","Explainable prioritization with no automated claim action")
    _card(fig,.04,"Review queue",f"{len(reviewed):,}"); _card(fig,.275,"Alert rate",f"{tm['alert_rate']:.1%}"); _card(fig,.51,"Precision / lift",f"{tm['precision_at_alert_rate']:.1%} / {tm['precision_lift_vs_random']:.2f}×"); _card(fig,.745,"Automated denials",f"{tm['automated_claim_denials']}",TEAL)
    pr=reviewed.review_priority.value_counts()
    ax=fig.add_axes([.04,.16,.35,.55]); _style(ax,"Review priority"); ax.bar(pr.index,pr.values,color=[RED,AMBER,TEAL][:len(pr)]); [ax.text(i,v,f"{v:,}",ha="center",va="bottom",fontsize=8) for i,v in enumerate(pr.values)]
    reasons=reviewed.reason_codes.fillna("").str.split("|").explode().str.strip(); reasons=reasons[reasons.ne("")].value_counts().head(8).sort_values()
    ax=fig.add_axes([.45,.16,.51,.55]); _style(ax,"Reason-code composition"); ax.barh(reasons.index,reasons.values,color=TEAL)
    _save(fig,"06_human_review_governance.png")


def main() -> None:
    frames = _write_data()
    _mockups(frames)
    print(f"Power BI assets built: {len(list(OUT.glob('*.csv')))} tables, {len(list(MOCK.glob('*.png')))} mockups")


if __name__ == "__main__":
    main()
