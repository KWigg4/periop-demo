# 1. Base image: Ubuntu + a pinned R version, maintained by the Rocker project.
#    Pinning the tag (4.4.1, not "latest") is what makes the build reproducible.
#    rocker/r-ver also points CRAN at a dated Posit Package Manager snapshot,
#    so package versions are frozen to the date that R version was current.
FROM rocker/r-ver:4.4.1

# 2. Install R packages. This is its own layer, placed BEFORE copying app code,
#    so editing app.R doesn't force Docker to reinstall packages (layer caching).
RUN install2.r --error --skipinstalled \
    shiny bslib dplyr ggplot2 DT \
 && rm -rf /tmp/downloaded_packages

# 3. Run as a non-root user (good practice for anything client-facing).
RUN useradd --create-home shiny
WORKDIR /home/shiny/app

# 4. Copy the app in. Changes here only rebuild from this step down.
COPY --chown=shiny:shiny app.R .
USER shiny

# 5. Document the port the app listens on (doesn't publish it; `docker run -p` does).
EXPOSE 3838

# 6. The command the container runs on start. host 0.0.0.0 is essential:
#    Shiny's default (127.0.0.1) is only reachable from inside the container.
CMD ["R", "--quiet", "-e", "shiny::runApp('.', host = '0.0.0.0', port = 3838)"]
