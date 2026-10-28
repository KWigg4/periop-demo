# Periop Insights (demo) -------------------------------------------------
# A small OR-performance dashboard on simulated data, modeled loosely on the
# kind of product described in the Huron Clinical Insights role.
# Metrics: case volume, first-case on-time starts (FCOTS), turnover time,
# and block utilization against a 75% target.

library(shiny)
library(bslib)
library(dplyr)
library(ggplot2)
library(DT)

# Simulated data ----------------------------------------------------------
set.seed(2027)

rooms    <- sprintf("OR-%02d", 1:8)
services <- c("Orthopedics", "General Surgery", "Cardiac",
              "Neurosurgery", "Urology", "Gynecology")

all_days <- seq(as.Date("2026-07-01"), as.Date("2026-09-30"), by = "day")
weekdays_only <- all_days[!format(all_days, "%u") %in% c("6", "7")]

block_start <- 7.5 * 60   # 07:30, minutes after midnight
block_end   <- 15.5 * 60  # 15:30
block_mins  <- block_end - block_start
on_time_threshold <- 5    # minutes late still counted as on time

sim_room_day <- function(date, room) {
  n        <- sample(2:5, 1)
  service  <- sample(services, 1)                  # one service owns the block
  duration <- round(rlnorm(n, log(95), 0.35))      # case length, minutes
  turnover <- round(rlnorm(n, log(30), 0.30))      # gap before each case
  turnover[1] <- 0
  first_delay <- max(0, round(rnorm(1, mean = 6, sd = 10)))

  start <- block_start + first_delay +
    cumsum(turnover) + cumsum(c(0, head(duration, -1)))

  data.frame(
    date = date,
    room = room,
    service = service,
    case_seq = seq_len(n),
    start_min = start,
    end_min = start + duration,
    duration = duration,
    turnover = ifelse(seq_len(n) == 1, NA, turnover),
    first_case_delay = c(first_delay, rep(NA, n - 1))
  )
}

grid <- expand.grid(date = weekdays_only, room = rooms,
                    stringsAsFactors = FALSE)
cases <- do.call(rbind, lapply(seq_len(nrow(grid)), function(i) {
  sim_room_day(grid$date[i], grid$room[i])
}))

pct <- function(x, digits = 0) paste0(round(100 * x, digits), "%")

# UI ------------------------------------------------------------------------
theme <- bs_theme(
  version = 5,
  primary = "#0F5257",   # surgical teal
  secondary = "#5B6770",
  bg = "#FFFFFF",
  fg = "#1F2A30",
  base_font = font_collection("system-ui", "-apple-system",
                              "Segoe UI", "Roboto", "sans-serif")
)

ui <- page_sidebar(
  title = "Periop Insights (demo, simulated data)",
  theme = theme,
  sidebar = sidebar(
    width=300,
    dateRangeInput("dates", "Date range",
                   start = min(cases$date), end = max(cases$date),
                   min = min(cases$date), max = max(cases$date)),
    checkboxGroupInput("services", "Services", choices = services,
                   selected = services),
    helpText("Block hours 07:30 to 15:30. A first case counts as on time ",
             "if it starts within 5 minutes of schedule.")
  ),
  layout_columns(
    fill = FALSE,
    value_box("Cases", textOutput("n_cases")),
    value_box("First-case on-time starts", textOutput("fcots")),
    value_box("Median turnover", textOutput("turnover")),
    value_box("Block utilization", textOutput("util"))
  ),
  layout_columns(
    card(card_header("Utilization by room (dashed line = 75% target)"),
         plotOutput("room_plot")),
    card(card_header("First-case on-time starts by week"),
         plotOutput("fcots_plot"))
  ),
  card(card_header("Summary by service"), DTOutput("service_table"))
)

# Server --------------------------------------------------------------------
server <- function(input, output, session) {

  filtered <- reactive({
    req(input$services, input$dates)
    out <- cases |>
      filter(date >= input$dates[1], date <= input$dates[2],
             service %in% input$services)
    validate(need(nrow(out) > 0, "No cases match these filters. Widen the date range or add a service."))
    out
  })

  room_days <- reactive({
    filtered() |>
      group_by(date, room, service) |>
      summarise(
        in_block = sum(pmax(0, pmin(end_min, block_end) - pmax(start_min, block_start))),
        first_delay = first_case_delay[case_seq == 1],
        .groups = "drop"
      ) |>
      mutate(util = in_block / block_mins,
             on_time = first_delay <= on_time_threshold)
  })

  output$n_cases  <- renderText(format(nrow(filtered()), big.mark = ","))
  output$fcots    <- renderText(pct(mean(room_days()$on_time)))
  output$turnover <- renderText(paste(median(filtered()$turnover, na.rm = TRUE), "min"))
  output$util     <- renderText(pct(mean(room_days()$util)))

  output$room_plot <- renderPlot({
    room_days() |>
      group_by(room) |>
      summarise(util = mean(util)) |>
      ggplot(aes(room, util)) +
      geom_col(fill = "#0F5257", width = 0.7) +
      geom_hline(yintercept = 0.75, linetype = "dashed", colour = "#C77D0A", linewidth = 0.8) +
      scale_y_continuous(labels = pct, limits = c(0, 1.05)) +
      labs(x = NULL, y = "Average utilization") +
      theme_minimal(base_size = 14)
  })

  output$fcots_plot <- renderPlot({
    room_days() |>
      mutate(week = as.Date(cut(date, "week"))) |>
      group_by(week) |>
      summarise(fcots = mean(on_time)) |>
      ggplot(aes(week, fcots)) +
      geom_line(colour = "#0F5257", linewidth = 1) +
      geom_point(colour = "#0F5257", size = 2) +
      scale_y_continuous(labels = pct, limits = c(0, 1)) +
      labs(x = "Week starting", y = "On-time first cases") +
      theme_minimal(base_size = 14)
  })

  output$service_table <- renderDT({
    util_by_service <- room_days() |>
      group_by(service) |>
      summarise(`Block utilization` = pct(mean(util), 1),
                `First-case on time` = pct(mean(on_time), 1))

    filtered() |>
      group_by(service) |>
      summarise(Cases = n(),
                `Median case length (min)` = median(duration),
                `Median turnover (min)` = median(turnover, na.rm = TRUE)) |>
      left_join(util_by_service, by = "service") |>
      rename(Service = service) |>
      datatable(rownames = FALSE, options = list(dom = "t", pageLength = 10))
  })
}

shinyApp(ui, server)
