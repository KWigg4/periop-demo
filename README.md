# Periop Insights demo: Shiny + Docker practice

## 0. Setup
- Install Docker Desktop (Windows needs WSL 2 enabled; the installer walks you through it).
- Open this folder in Positron. Check Docker works in Positron's terminal: `docker run hello-world`
- Run the app natively first (open app.R, click Run App) so you know it works before containerizing.

## 1. Build and run
```
docker build -t periop-demo:0.1 .
docker run --rm -p 8080:3838 periop-demo:0.1
```
Open http://localhost:8080. Ctrl+C stops it.

Concepts: an **image** is the frozen recipe output (`docker build`); a **container** is a running
instance of it (`docker run`). `-p 8080:3838` maps your machine's port 8080 to the container's 3838.
`--rm` deletes the container when it stops.

## 2. Watch layer caching
Change the title text in app.R and rebuild as 0.2. The package install step says CACHED and the
build takes seconds. Now move `COPY app.R .` above the `RUN install2.r` line and rebuild: every code
change reinstalls packages. Move it back. Order layers from least- to most-frequently changed.

## 3. Tagging and rollback drill (this is in the job description)
```
docker build -t periop-demo:0.2 .
docker images periop-demo                 # both versions exist side by side
docker run -d --name periop -p 8080:3838 periop-demo:0.2     # -d = run in background
# "client reports a bug in 0.2" -> roll back:
docker stop periop && docker rm periop
docker run -d --name periop -p 8080:3838 periop-demo:0.1
```
Rollback is just running the previous immutable tag. Never overwrite a tag you've deployed.

## 4. Look inside
```
docker ps                       # running containers
docker logs periop              # Shiny's console output (where errors show up)
docker exec -it periop bash     # a shell inside the running container
docker image history periop-demo:0.2   # the layers and their sizes
```

## 5. Next steps
- docker compose: put the run flags in a `compose.yaml` so `docker compose up` does it all.
- renv: replace the `install2.r` line with `renv::restore()` from an renv.lock for exact versions.
- Shiny for Python version of this same app, in the same container pattern.
- Apple Silicon note: add `--platform linux/amd64` to build an image matching typical cloud servers.
