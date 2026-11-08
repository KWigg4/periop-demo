fit <- lm(mpg ~ wt, data=mtcars)
class(fit)
# lm
unclass(fit)
# unstrips all the things, so the model obj is just a list (coeffs, residuals, fitted values, etc.)
# basically nothing magical, just a list iwth the label "lm" stuck on it.

x <- list(metric="cases", n_bad=2)
x
# prints it the boring default way, list a list ($metric and $n_bad)
class(x) <- "qc_result"
# the label is attached, but R doesn't know anything special about qc_result yet, so it 
# still prints the boring way (with a line at the bottom showing the class)
x

# STEP 4: Teach R how to print things with that label: 
print.qc_result <- function(x, ...){
  cat("QC check on", x$metric, ":", x$n_bad, "rows need review\n")
}

x

# THAT'S ALL S3 is: a list with a label, plus functions named something.label


# You can write your own generic: 
n_bad <- function(x, ...) UseMethod("n_bad")
n_bad.qc_result <- function(x, ...) x$n_bad
n_bad(x)

# trying it with summary 
summary.qc_result <- function(x, ...){
  cat("PASS: all rows of", object$metric, "match the legacy report\n")
} else {
  cat("REVIEW:", object$n_bad, "rows of", object$metric, "need closer review")
}

