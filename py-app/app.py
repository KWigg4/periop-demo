# Periop Insights (demo) -- Python version ---------------------------------
# Same app as app.R, rewritten in Shiny for Python so you can compare the two
# line by line. pandas plays the role of dplyr; plotnine is a port of ggplot2.

import numpy as np
import pandas as pd
from plotnine import (aes, geom_col, geom_hline, geom_line, geom_point, ggplot,
                      labs, scale_y_continuous, theme_minimal)
from shiny import App, reactive, render, req, ui

# Simulated data -----------------------------------------------------------
rng = np.random.default_rng(2027)  # R's set.seed(); numbers won't match R's

ROOMS = [f"OR-{i:02d}" for i in range(1, 9)]
SERVICES = ["Orthopedics", "General Surgery", "Cardiac",
            "Neurosurgery", "Urology", "Gynecology"]
DAYS = pd.bdate_range("2026-07-01", "2026-09-30")  # business days only

BLOCK_START = 7.5 * 60   # 07:30, minutes after midnight
BLOCK_END = 15.5 * 60    # 15:30
BLOCK_MINS = BLOCK_END - BLOCK_START
ON_TIME_THRESHOLD = 5

TEAL, AMBER = "#0F5257", "#C77D0A"


def sim_room_day(date, room):
    n = rng.integers(2, 6)                              # 2 to 5 cases
    service = rng.choice(SERVICES)
    duration = np.round(rng.lognormal(np.log(95), 0.35, n))
    turnover = np.round(rng.lognormal(np.log(30), 0.30, n))
    turnover[0] = 0
    first_delay = max(0, round(rng.normal(6, 10)))

    start = (BLOCK_START + first_delay + np.cumsum(turnover)
             + np.concatenate([[0], np.cumsum(duration[:-1])]))

    return pd.DataFrame({
        "date": date,
        "room": room,
        "service": service,
        "case_seq": np.arange(1, n + 1),
        "start_min": start,
        "end_min": start + duration,
        "duration": duration,
        "turnover": np.where(np.arange(n) == 0, np.nan, turnover),
        "first_case_delay": [first_delay] + [np.nan] * (n - 1),
    })


cases = pd.concat([sim_room_day(d, r) for d in DAYS for r in ROOMS],
                  ignore_index=True)

def pct(x, digits=0):
    return f"{100 * x:.{digits}f}%"

# UI ------------------------------------------------------------------------
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_date_range("dates", "Date range",
                            start=DAYS.min().date(), end=DAYS.max().date(),
                            min=DAYS.min().date(), max=DAYS.max().date()),
        ui.input_checkbox_group("services", "Services",
                                choices=SERVICES, selected=SERVICES),
        ui.help_text("Block hours 07:30 to 15:30. A first case counts as on "
                     "time if it starts within 5 minutes of schedule."),
        width=300,
    ),
    ui.layout_columns(
        ui.value_box("Cases", ui.output_text("n_cases")),
        ui.value_box("First-case on-time starts", ui.output_text("fcots")),
        ui.value_box("Median turnover", ui.output_text("turnover")),
        ui.value_box("Block utilization", ui.output_text("util")),
        fill=False,
    ),
    ui.layout_columns(
        ui.card(ui.card_header("Utilization by room (dashed line = 75% target)"),
                ui.output_plot("room_plot")),
        ui.card(ui.card_header("First-case on-time starts by week"),
                ui.output_plot("fcots_plot")),
    ),
    ui.card(ui.card_header("Summary by service"),
            ui.output_data_frame("service_table")),
    title="Periop Insights (Python demo, simulated data)",
)


# Server --------------------------------------------------------------------
def server(input, output, session):

    @reactive.calc                      # like R: reactive({ ... })
    def filtered():
        req(input.services())
        start, end = input.dates()
        df = cases[(cases["date"] >= pd.Timestamp(start))
                   & (cases["date"] <= pd.Timestamp(end))
                   & cases["service"].isin(list(input.services()))]
        req(len(df) > 0)
        return df

    @reactive.calc
    def room_days():
        df = filtered().copy()
        df["in_block"] = (np.minimum(df["end_min"], BLOCK_END)
                          - np.maximum(df["start_min"], BLOCK_START)).clip(lower=0)
        rd = (df.groupby(["date", "room", "service"], as_index=False)
                .agg(in_block=("in_block", "sum"),
                     first_delay=("first_case_delay", "first")))
        rd["util"] = rd["in_block"] / BLOCK_MINS
        rd["on_time"] = rd["first_delay"] <= ON_TIME_THRESHOLD
        return rd

    @render.text
    def n_cases():
        return f"{len(filtered()):,}"

    @render.text
    def fcots():
        return pct(room_days()["on_time"].mean())

    @render.text
    def turnover():
        return f"{filtered()['turnover'].median():g} min"

    @render.text
    def util():
        return pct(room_days()["util"].mean())

    @render.plot
    def room_plot():
        d = room_days().groupby("room", as_index=False)["util"].mean()
        return (ggplot(d, aes("room", "util"))
                + geom_col(fill=TEAL, width=0.7)
                + geom_hline(yintercept=0.75, linetype="dashed", color=AMBER)
                + scale_y_continuous(labels=lambda xs: [pct(x) for x in xs],
                                     limits=(0, 1.05))
                + labs(x="", y="Average utilization")
                + theme_minimal(base_size=13))

    @render.plot
    def fcots_plot():
        rd = room_days()
        w = (rd.assign(week=rd["date"].dt.to_period("W-SUN").dt.start_time)
               .groupby("week", as_index=False)["on_time"].mean())
        return (ggplot(w, aes("week", "on_time"))
                + geom_line(color=TEAL)
                + geom_point(color=TEAL)
                + scale_y_continuous(labels=lambda xs: [pct(x) for x in xs],
                                     limits=(0, 1))
                + labs(x="Week starting", y="On-time first cases")
                + theme_minimal(base_size=13))

    @render.data_frame
    def service_table():
        by_service = (filtered().groupby("service")
                      .agg(cases=("duration", "size"),
                           med_len=("duration", "median"),
                           med_turn=("turnover", "median")))
        util = (room_days().groupby("service")
                .agg(util=("util", "mean"), fcots=("on_time", "mean")))
        out = by_service.join(util).reset_index()
        out["util"] = out["util"].map(lambda x: pct(x, 1))
        out["fcots"] = out["fcots"].map(lambda x: pct(x, 1))
        out.columns = ["Service", "Cases", "Median case length (min)",
                       "Median turnover (min)", "Block utilization",
                       "First-case on time"]
        return out


app = App(app_ui, server)