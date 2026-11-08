# qc_demo.R
# Run this line by line (Ctrl+Enter) to see each piece of S3 in action.
setwd("C:/periop-demo/r-app/R")
source("qc_comparison.R")

# What the Insights app reports: monthly OR case counts by site
app <- data.frame(
  site  = rep(c("Main OR", "ASC North", "ASC South"), each = 3),
  month = rep(c("2026-01", "2026-02", "2026-03"), times = 3),
  cases = c(1398, 1412, 1450,  402, 398, 415,  288, 301, 0)
)
app <- app[!(app$site == "ASC South" & app$month == "2026-03"), ]  # a month missing from the app

# What the client's legacy Power BI report says
legacy <- data.frame(
  site  = rep(c("Main OR", "ASC North", "ASC South"), each = 3),
  month = rep(c("2026-01", "2026-02", "2026-03"), times = 3),
  cases = c(1398, 1437, 1450,  402, 400, 415,  288, 301, 296)
)

qc <- qc_compare(app, legacy, by = c("site", "month"), metric = "cases")

class(qc)          # the class label we attached
qc                 # typing the name calls print.qc_comparison()
summary(qc)        # calls summary.qc_comparison()
n_mismatches(qc)   # our own generic, dispatching to n_mismatches.qc_comparison()
head(as.data.frame(qc))

n_mismatches(app)  # a plain data frame: falls through to the default method and errors

# See which methods exist for our class
methods(class = "qc_comparison")