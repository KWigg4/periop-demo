# qc_comparison.R
# An S3 class that compares an Insights app's metrics to a client's
# legacy report (e.g., Power BI) and flags rows that need review.
#
# Pieces of S3 shown here:
#   1. A function that builds the object and attaches a class label
#   2. Methods for existing generics: print(), summary(), as.data.frame()
#   3. A brand-new generic of our own, n_mismatches(), using UseMethod()


# ---- 1. Build the object ---------------------------------------------------

qc_compare <- function(app, legacy, by, metric, tolerance = 0.01) {
  # Check inputs before doing anything
  stopifnot(is.data.frame(app), is.data.frame(legacy))
  needed <- c(by, metric)
  for (src in c("app", "legacy")) {
    missing_cols <- setdiff(needed, names(get(src)))
    if (length(missing_cols) > 0) {
      stop(src, " is missing column(s): ", paste(missing_cols, collapse = ", "))
    }
  }

  # Line up the two sources; all = TRUE keeps rows found in only one source
  merged <- merge(app[needed], legacy[needed], by = by, all = TRUE,
                  suffixes = c("_app", "_legacy"))
  a <- merged[[paste0(metric, "_app")]]
  l <- merged[[paste0(metric, "_legacy")]]

  merged$diff     <- a - l
  merged$pct_diff <- ifelse(!is.na(l) & l != 0, (a - l) / l, NA)

  # Assign a status to every row
  status <- rep("mismatch", nrow(merged))
  status[is.na(a)] <- "missing in app"
  status[!is.na(a) & is.na(l)] <- "missing in legacy"
  ok <- !is.na(a) & !is.na(l) &
    (merged$diff == 0 | (!is.na(merged$pct_diff) & abs(merged$pct_diff) <= tolerance))
  status[ok] <- "match"
  merged$status <- status

  # The S3 part: an ordinary list with a class label attached
  structure(
    list(
      results   = merged,
      by        = by,
      metric    = metric,
      tolerance = tolerance,
      created   = Sys.time()
    ),
    class = "qc_comparison"
  )
}


# ---- 2. Methods for generics R already has ---------------------------------

# print() runs automatically when you type the object's name in the console
print.qc_comparison <- function(x, ...) {
  counts <- table(factor(x$results$status,
                         levels = c("match", "mismatch",
                                    "missing in app", "missing in legacy")))
  cat("<qc_comparison>\n")
  cat("Metric:    ", x$metric, "\n")
  cat("Compared by:", paste(x$by, collapse = ", "), "\n")
  cat("Tolerance: ", paste0(x$tolerance * 100, "%"), "\n\n")
  for (s in names(counts)) cat(sprintf("  %-18s %d\n", s, counts[[s]]))
  n_bad <- sum(counts) - counts[["match"]]
  cat("\nResult:", if (n_bad == 0) "PASS" else paste("REVIEW", n_bad, "row(s)"), "\n")
  invisible(x)  # print methods return the object invisibly by convention
}

# summary() shows the rows that need attention
summary.qc_comparison <- function(object, ...) {
  flagged <- object$results[object$results$status != "match", ]
  if (nrow(flagged) == 0) {
    cat("All rows match within tolerance.\n")
  } else {
    cat("Rows needing review:\n\n")
    print(flagged, row.names = FALSE)
  }
  invisible(flagged)
}

# as.data.frame() lets the results flow into a table, a Shiny DT, or a CSV
as.data.frame.qc_comparison <- function(x, ...) {
  x$results
}


# ---- 3. A new generic of our own -------------------------------------------

# The generic: UseMethod() looks at the class and dispatches
n_mismatches <- function(x, ...) {
  UseMethod("n_mismatches")
}

# The method for our class
n_mismatches.qc_comparison <- function(x, ...) {
  sum(x$results$status != "match")
}

# The fallback for any other class
n_mismatches.default <- function(x, ...) {
  stop("n_mismatches() doesn't know how to handle an object of class ",
       paste(class(x), collapse = "/"))
}
