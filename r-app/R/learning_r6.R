# install.packages("R6")
library(R6)

Deployment <- R6Class("Deployment",
  public = list(
    client=NULL, 
    status="not started"
  ))
# r6class creates a blueprint called Deployment, saying every 
#   deployment has a client and a status. `Deployment$new()` 

d <- Deployment$new()
d$client <- "Health System A"
d$client
d$status

