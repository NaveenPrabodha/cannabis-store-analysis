# Naveen — Full Setup & Deployment Guide (Windows + AWS)

A start-to-finish guide for running this project on a Windows PC, pushing
to your own GitHub account, and redeploying it to your existing AWS
infrastructure.

**Your starting situation**

- ✅ AWS account is yours (the existing EC2 + RDS are already provisioned)
- 🆕 GitHub account is different from the original (`dklochana`) — you'll
  need to host the repo + the container images under your account
- 💻 Local machine is Windows

This guide takes you through:

1. Install everything you need on Windows
2. Move the codebase to **your** GitHub account
3. Get the project running locally
4. Get GitHub Actions building Docker images under **your** account
5. Redeploy the live site on the existing AWS EC2

---

## Table of contents

1. [Inheriting the existing AWS setup](#1-inheriting-the-existing-aws-setup)
2. [Prerequisites — Windows install](#2-prerequisites--windows-install)
3. [Get the code under your GitHub account](#3-get-the-code-under-your-github-account)
4. [Local development on Windows](#4-local-development-on-windows)
5. [Configure GitHub for CI/CD](#5-configure-github-for-cicd)
6. [Build your container images](#6-build-your-container-images)
7. [Redeploy on the existing AWS EC2](#7-redeploy-on-the-existing-aws-ec2)
8. [Common operations](#8-common-operations)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Inheriting the existing AWS setup

The AWS resources are already provisioned and running. You do **not** need
to recreate EC2, RDS, security groups, or anything else in AWS. You just
need to bring two things over to your Windows machine: the SSH key and
the RDS password.

### 1.1 What's already running (and stays running)

| Resource | Identifier | What it does |
|---|---|---|
| EC2 instance | Public IP `51.21.167.48` (eu-north-1) | Runs nginx + frontend + backend containers + 4 systemd timers |
| RDS database | `cannabis-db.c98q8uawgkhl.eu-north-1.rds.amazonaws.com:5432` | Postgres 16, database `cannabis_analysis`, fully seeded |
| Security group (EC2) | `cannabis-ec2-sg` | Allows port 22 (SSH) + port 80 (HTTP) inbound |
| Security group (RDS) | `cannabis-rds-sg` | Allows port 5432 only from the EC2 security group |
| Systemd timers on EC2 | `scrape-ocs`, `scrape-hibuddy`, `scrape-agco`, `promo-duration` | Keep the database fresh on a schedule |

Nothing in this list changes when you move to Windows. The cloud doesn't
care which laptop is connecting — only that you have valid credentials.

### 1.2 What to copy from the original Mac to Windows

| Item | Where it is on Mac | Where it goes on Windows |
|---|---|---|
| `cannabis-key-v1.pem` (SSH private key) | `~/Downloads/cannabis-key-v1.pem` | Anywhere safe — e.g. `C:\Users\<you>\.ssh\cannabis-key-v1.pem` |
| RDS master password | In your head / password manager (you set it when creating RDS) | Same — you'll need it when running `psql` from EC2 |
| The repo source code | `/Users/lochana/Naveen/cannabis_store-analysis` | Just `git clone` from GitHub — no need to copy files |

### 1.3 Move the SSH key to Windows

Easiest option: email it to yourself, or use a USB drive, or use OneDrive.
Save it to a folder like `C:\Users\<you>\.ssh\`.

**Important — set Windows file permissions:**

Windows SSH refuses to use a key if it's readable by other users. Fix
it once in PowerShell:

```powershell
icacls C:\Users\<you>\.ssh\cannabis-key-v1.pem /inheritance:r /grant:r "$($env:USERNAME):R"
```

That command removes inherited permissions and grants read-only to just
your user.

### 1.4 Verify you can connect from Windows

In PowerShell:

```powershell
ssh -i C:\Users\<you>\.ssh\cannabis-key-v1.pem ec2-user@51.21.167.48
```

You should land in the EC2 shell with a prompt like
`[ec2-user@ip-172-31-43-199 ~]$`. While inside, sanity-check the live
deployment:

```bash
cd ~/cannabis-burlington-platform/infra
docker compose -f docker-compose.prod.yml ps
curl -s http://localhost/api/health
```

All three containers should be `running` and `/api/health` should
return `{"status":"ok","db_ok":true,...}`. If yes, you've inherited a
working deployment.

If SSH gives "Connection reset by peer":

- The EC2 Security Group's port 22 rule is set to "My IP" — but your
  Windows machine has a different IP than the original Mac. Edit the
  rule: AWS Console → EC2 → Security Groups → `cannabis-ec2-sg` →
  Inbound rules → edit the port 22 source to either your current IP or
  `0.0.0.0/0` (anywhere) for now.

### 1.5 What will change as you move to your GitHub account

Only one thing on the EC2 host actually needs to change: the
`GITHUB_USER` line in `infra/.env`. That value tells `docker compose`
which GitHub Container Registry namespace to pull images from.

Right now it's set to `dklochana`. After you publish your own images
under your account (covered in sections 5 and 6), you'll SSH in and
change that one line, then `docker compose pull` + `up -d`. That's the
entire handover.

Everything else — the EC2 instance itself, RDS, systemd timers, nginx
config, the seeded data — stays exactly as it is.

---

## 2. Prerequisites — Windows install

You have two paths on Windows. **Pick one.**

### Path A — Native PowerShell (simpler)

Open PowerShell as **Administrator** and install via `winget`:

```powershell
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
winget install PostgreSQL.PostgreSQL.16
winget install Git.Git
winget install astral-sh.uv
winget install GitHub.cli
```

After install, **close PowerShell and reopen it** so `PATH` updates take
effect. Verify each:

```powershell
python --version    # Python 3.12.x
node --version      # v20.x.x
psql --version      # psql (PostgreSQL) 16.x
uv --version
git --version
gh --version
```

If `psql` is not found, add `C:\Program Files\PostgreSQL\16\bin` to your
System `Path`:

1. Start menu → search "Environment Variables" → open it
2. Click **Environment Variables…**
3. Under **System variables**, select `Path` → **Edit**
4. **New** → paste the path above → **OK** all dialogs
5. Reopen PowerShell

### Path B — WSL2 + Ubuntu (recommended for parity with production)

This gives you a Linux environment inside Windows. Closer to how the
project runs on AWS.

In **PowerShell as Administrator**:

```powershell
wsl --install -d Ubuntu
```

Reboot when prompted. After reboot, Ubuntu finishes its first-run setup
(asks for a username + password). Then inside the Ubuntu shell:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip \
  nodejs npm postgresql-16 git curl build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
sudo apt install -y gh   # if not already there
```

From here on, the rest of this guide works the same — just run commands
in the Ubuntu shell instead of PowerShell.

For VS Code, install the **Remote - WSL** extension so you can open the
project from inside Ubuntu with a real Linux file system.

---

## 3. Get the code under your GitHub account

You need the repo under **your** account, not the original owner's,
because GitHub Actions will publish container images under whoever owns
the repo.

### Option A — Fork (keeps a link to the original)

1. Go to `https://github.com/DKLOCHANA/cannabis-burlington-platform`
2. Click **Fork** (top right) → select your account as the destination
3. Clone your fork locally:

```powershell
# PowerShell
cd C:\Users\<you>\Projects
git clone https://github.com/<YOUR_USERNAME>/cannabis-burlington-platform.git
cd cannabis-burlington-platform
```

```bash
# WSL2 / Linux
cd ~/projects
git clone https://github.com/<YOUR_USERNAME>/cannabis-burlington-platform.git
cd cannabis-burlington-platform
```

### Option B — Create a brand-new repo (no fork link)

If you'd rather start clean (no fork badge on GitHub), get the source
code first, then push it to a fresh repo of yours:

```powershell
# 1. Clone the original
git clone https://github.com/DKLOCHANA/cannabis-burlington-platform.git
cd cannabis-burlington-platform

# 2. Point origin at your new (empty) GitHub repo
git remote remove origin
git remote add origin https://github.com/<YOUR_USERNAME>/cannabis-burlington-platform.git

# 3. Push everything
git push -u origin main
```

You'll need to create the empty repo on GitHub first (no README, no
.gitignore, no license — leave it bare):

- Go to https://github.com/new
- Name: `cannabis-burlington-platform`
- Visibility: **Public** (recommended — keeps GHCR images free)
- Click **Create**

---

## 4. Local development on Windows

The goal of this section: confirm the project runs on your machine
before touching production.

### 4.1 Create the local database

**PowerShell:**

```powershell
# This will prompt for the postgres user password you set during install
psql -U postgres -c "CREATE DATABASE cannabis_analysis;"
```

**WSL2:**

```bash
sudo -u postgres createdb cannabis_analysis
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'admin';"
```

### 4.2 Backend setup

```powershell
# PowerShell — from the repo root
cd backend
copy .env.example .env
notepad .env
```

Edit `.env` to look like this (replace `YOUR_PASSWORD` with your local
Postgres password):

```
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/cannabis_analysis
SYNC_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/cannabis_analysis
CORS_ORIGINS=http://localhost:3000
ENV=local
APP_VERSION=0.1.0
LOG_LEVEL=INFO
```

Save and close Notepad. Then:

```powershell
uv sync
uv run alembic upgrade head
uv run python scripts\seed_from_csvs.py
```

The seed should report something like:
```
Final counts:
  dim_stores                 26
  dim_products             7127
  fct_prices               3459
  fct_price_history        3459
```

### 4.3 Pipeline setup

```powershell
cd ..\pipeline
copy ..\backend\.env .env
uv sync
uv run playwright install chromium
```

> **Windows gotcha:** If `playwright install` fails with a permissions
> error, close PowerShell and reopen it as Administrator just for this
> command.

### 4.4 Frontend setup

```powershell
cd ..\frontend
copy .env.example .env.local
```

Edit `.env.local` so it points at your local backend:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Then:

```powershell
npm install
```

### 4.5 Run the stack locally

You need **three PowerShell tabs** running side by side.

**Tab 1 — backend:**
```powershell
cd backend
uv run uvicorn app.main:app --reload
```
Should print `Uvicorn running on http://127.0.0.1:8000`.

**Tab 2 — frontend:**
```powershell
cd frontend
npm run dev
```
Should print `Ready in N seconds` and a URL.

**Tab 3 — sanity check:**
```powershell
curl http://localhost:8000/health
```
Should return JSON like `{"status":"ok","db_ok":true,...}`.

Then open `http://localhost:3000` in your browser. You should see the
homepage with featured products and hottest deals.

✅ If you can browse `/products`, `/stores`, `/deals` and they show data,
local dev works. Stop both tabs (Ctrl+C) and move to the next section.

---

## 5. Configure GitHub for CI/CD

Now we set things up so GitHub Actions can build your images and push
them to **your** GitHub Container Registry namespace.

### 5.1 Set the repo variable for the production API URL

The frontend bakes the API URL into its JavaScript bundle at build time.
GitHub Actions reads it from a repo variable.

1. Go to your repo on GitHub
2. **Settings** → **Secrets and variables** → **Actions** → **Variables**
   tab → **New repository variable**
3. Name: `PUBLIC_API_BASE_URL`
4. Value: `http://51.21.167.48/api`
   (this is the existing EC2 public IP — if you've launched a new EC2,
   use that one instead)
5. Click **Add variable**

### 5.2 Set up SSH access for the deploy workflow

The `.github/workflows/deploy.yml` workflow SSHes into EC2 to redeploy.
It needs two secrets.

1. **EC2_HOST** — your EC2 public IP (e.g. `51.21.167.48`)
2. **EC2_SSH_KEY** — the contents of your `.pem` file (the same one you
   use locally to SSH in)

To set them: **Settings** → **Secrets and variables** → **Actions** →
**Secrets** tab → **New repository secret**.

To get the SSH key content into your clipboard:

**PowerShell:**
```powershell
Get-Content C:\path\to\cannabis-key-v1.pem | Set-Clipboard
```

**WSL2 / Linux:**
```bash
cat ~/cannabis-key-v1.pem | xclip -selection clipboard
# (or just `cat` and copy manually)
```

Paste the entire content (including `-----BEGIN RSA PRIVATE KEY-----`
and `-----END RSA PRIVATE KEY-----` lines) into the secret value field.

---

## 6. Build your container images

### 6.1 Trigger the build

1. Push any commit to `main` (the workflow auto-runs on
   `backend/**` or `frontend/**` paths), **or**:
2. Manually trigger it: GitHub → **Actions** tab → **Build & push
   container images** → **Run workflow** (right side) → **Run workflow**

Watch the run. Both `backend` and `frontend` jobs should go green in
~1 min.

### 6.2 Make the packages public

By default, GHCR packages are private. The EC2 host needs to pull them
without authentication, so make them public:

1. Go to your GitHub profile → **Packages** tab
2. Click `cannabis-backend`
3. **Package settings** (right sidebar) → scroll down → **Change
   visibility** → **Public** → confirm
4. Repeat for `cannabis-frontend`

✅ Once both packages show "Public", the EC2 host can pull them.

### 6.3 Verify the images exist

```powershell
# PowerShell — uses Docker Desktop if installed, otherwise just web check
# Visit: https://github.com/<YOUR_USERNAME>?tab=packages
```

You should see two packages: `cannabis-backend` and `cannabis-frontend`,
both tagged `latest` + `sha-<commit>`.

---

## 7. Redeploy on the existing AWS EC2

The EC2 host and RDS database already exist. We just need to:

1. Point the EC2's local `docker-compose.prod.yml` at **your** GHCR
   namespace (via the `GITHUB_USER` env var)
2. Pull the new images
3. Restart the containers

### 7.1 SSH into EC2

**PowerShell:**
```powershell
ssh -i C:\path\to\cannabis-key-v1.pem ec2-user@51.21.167.48
```

**WSL2:**
```bash
# Copy the key into WSL home and fix permissions first if it's on C:
cp /mnt/c/path/to/cannabis-key-v1.pem ~/cannabis-key.pem
chmod 400 ~/cannabis-key.pem
ssh -i ~/cannabis-key.pem ec2-user@51.21.167.48
```

If SSH fails with "Connection reset by peer":

- Check the EC2's **Security Group** allows port 22 from your current IP
- Or temporarily set port 22 source to **Anywhere-IPv4** (0.0.0.0/0)

### 7.2 Update the repo on EC2 to point at your fork

```bash
cd ~/cannabis-burlington-platform
git remote set-url origin https://github.com/<YOUR_USERNAME>/cannabis-burlington-platform.git
git fetch
git reset --hard origin/main
```

### 7.3 Update the `.env` to use your GHCR namespace

```bash
cd ~/cannabis-burlington-platform/infra
nano .env
```

Change the first line from `GITHUB_USER=dklochana` to:

```
GITHUB_USER=<YOUR_USERNAME>
```

Save with `Ctrl+O` → Enter → `Ctrl+X`.

Verify (password masked):
```bash
sed 's/:[^@]*@/:***@/' .env
```

### 7.4 Pull your images + restart

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

All three containers should show `running` (backend will reach `healthy`
after ~30 seconds).

### 7.5 Smoke test

```bash
curl http://localhost/api/health
curl -sI http://localhost/ | head -5
```

Both should succeed. Then in your **browser**:

```
http://51.21.167.48
```

Hard refresh (`Ctrl+Shift+R`) to bypass cache. You should see your
running platform.

✅ If the homepage loads with data, you've successfully redeployed under
your own account.

---

## 8. Common operations

All commands run inside the EC2 SSH session unless noted.

### Push a code change

```powershell
# On your Windows machine
git add .
git commit -m "your message"
git push
```

Then on GitHub: **Actions** → **Build & push container images** → **Run
workflow** (or wait for auto-trigger). Once green:

```bash
# On EC2
cd ~/cannabis-burlington-platform/infra
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### See container status + logs

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f --tail=100
docker compose -f docker-compose.prod.yml logs backend
```

### See pipeline scrape schedule + recent runs

```bash
systemctl list-timers --all | grep -E 'scrape|promo'

psql "host=cannabis-db.c98q8uawgkhl.eu-north-1.rds.amazonaws.com user=postgres dbname=cannabis_analysis" \
  -c "SELECT run_id, job_name, status, started_at, rows_processed FROM pipeline_runs ORDER BY run_id DESC LIMIT 10;"
```

### Manually trigger a scraper

```bash
sudo systemctl start scrape-ocs.service
sudo journalctl -u scrape-ocs.service --since "5 min ago" --no-pager
```

### Restart a single container after changing nginx.conf

```bash
docker compose -f docker-compose.prod.yml restart nginx
```

### Check memory pressure (t3.micro is tight)

```bash
free -h
df -h /
```

### Stop everything (without losing data)

```bash
docker compose -f docker-compose.prod.yml down
```

Database is on RDS, so containers can come and go without data loss.

---

## 9. Troubleshooting

| Symptom | Where to look |
|---|---|
| `winget` not recognized | You're on Windows 10 older than 1809 — update Windows or download winget from the Microsoft Store |
| `psql` not found after install | Add `C:\Program Files\PostgreSQL\16\bin` to System `Path`, reopen PowerShell |
| `uv` not found after install | Close PowerShell completely and reopen — uv installer updates `PATH` for new sessions only |
| `playwright install` fails with permission error | Run PowerShell as Administrator for that one command |
| Backend `.env`: app crashes with `field required` | Both `DATABASE_URL` **and** `SYNC_DATABASE_URL` must be set |
| Local frontend can't reach backend | Confirm `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `frontend/.env.local`, and the backend tab is actually running |
| `psql -U postgres` says "password authentication failed" | Use the password you set during PostgreSQL install — not "admin" unless you chose that |
| WSL2 + Docker Desktop containers can't talk to host | In Docker Desktop → Settings → Resources → WSL Integration → enable your distro |
| GitHub Actions image build fails | Open the workflow run logs — usually a TypeScript error from `next build` or a missing dep |
| EC2 SSH "Connection reset by peer" | Security Group port 22 source is wrong — open it to Anywhere-IPv4 (0.0.0.0/0) temporarily to confirm |
| EC2 `docker compose pull` says "denied" | The GHCR packages are still private. Make them public per section 6.2 |
| Site loads but no data | `curl http://localhost/api/health` on EC2 — if `db_ok: false`, RDS credentials or security group |
| Browser shows old version after deploy | Hard-refresh (Ctrl+Shift+R). Browser caches the JS bundle aggressively |
| EC2 public IP changes (e.g. after stop/start) | Frontend image bakes the old IP. Either allocate an Elastic IP (free while attached) or rebuild the frontend image with the new `PUBLIC_API_BASE_URL` variable |
| `/api/products` returns `[]` everywhere | Seed didn't run. Re-run `uv run python backend/scripts/seed_from_csvs.py` against RDS from EC2 |

---

## Quick reference — what's where

| Resource | Location |
|---|---|
| Live site | `http://<EC2_IP>` |
| Swagger / API docs | `http://<EC2_IP>/docs` |
| Database | RDS endpoint, accessed only from EC2 |
| Container images | `https://github.com/<YOUR_USERNAME>?tab=packages` |
| CI workflows | `.github/workflows/docker-images.yml`, `deploy.yml`, `ci.yml` |
| Production compose file | `infra/docker-compose.prod.yml` |
| Nginx config | `infra/nginx.conf` (mounted into nginx container) |
| Systemd units | `infra/systemd/*.{service,timer}` (copied to `/etc/systemd/system/`) |
| Production env vars | `infra/.env` on EC2 (gitignored) |
| Pipeline scrape logs | `/var/log/cannabis-pipeline.log` on EC2 + `journalctl -u <unit>` |
| Pipeline run audit | `pipeline_runs` table in RDS |

---

## When you're done

You should have:

- A working local Windows dev environment (backend + frontend + Postgres
  all running)
- A fork or clone of the repo on **your** GitHub account
- Two container images on **your** GitHub Container Registry, public
- The existing EC2 + RDS serving traffic from **your** images
- The site reachable at `http://<EC2_IP>` in any browser

If anything in this guide didn't go as expected, the section 9
troubleshooting table covers the common ones — and the section 8 ops
commands are enough for day-to-day.
