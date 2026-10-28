# TODO (Ben)

Things only you can do, by phase. Details are in [PLAN.md](PLAN.md).

## Phase 1: Foundations

- [x] **Install uv** (Python and the workspace; it downloads Python 3.13 itself):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [x] **Install Docker** in WSL, either Docker Desktop on Windows with WSL integration turned on for this distro, or Docker Engine inside WSL (`sudo apt install docker.io docker-compose-v2`, then `sudo usermod -aG docker $USER`). Only needed for Phase 1 E (containers); day-to-day development runs natively.
  - [x] The socket still says "permission denied": open a new WSL terminal (or `newgrp docker`) so the `docker` group applies, then check with `docker run --rm hello-world`.
- [x] **Create the GitHub repo** (`uwent/agweather2`, public; PLAN.md Q3), then add it as `origin`.
- [x] Answer PLAN.md Q1–Q3 (now D17–D19).
- [ ] **Server request to IT** (Phase 1 gate): send the Server requirements section of `docs/project-plan.md`, with the pilot's measured sizes once `docs/pilot.md` exists. Ask for EC2, the EBS data volume and RDS in the same region and AZ.
- [ ] Optional: put the Open-Meteo API key in `.env` as `OPEN_METEO_API_KEY` (needed from Phase 4).

## Phase 3: Model library (ahead of time)

- [x] **Copy the Shiny apps in** from OneDrive, with their data and `.rds` fixtures, to `tmp/shiny/` (Crop Risk Tool, alfalfa, potato volunteer). The git repos alone lack the data the parity tests need.
