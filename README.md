# CYBER OPS

**English** | [Türkçe](#türkçe)

A Django-based OSINT / reconnaissance console for authorized security research. Seven integrated modules, analysis reports stored in MySQL, and long-running scans handled via Redis + django-rq.

---

## English

### Features

| Module | Route | Description |
|--------|-------|-------------|
| DNS Recon | `/dns-scan/` | DNS records, subdomain discovery, WHOIS, web fingerprint (Wappalyzer), optional site snapshot |
| Network Intel | `/network-intel/` | GeoIP, RDAP (ipwhois), TLS, DNS intel, security headers, DNSBL |
| Image OSINT | `/image-osint/` | EXIF metadata read/write (Pillow, piexif) |
| Email OSINT | `/email-osint/` | Validation, footprint, Holehe account discovery |
| Username OSINT | `/username-osint/` | Sherlock, Maigret, GitHub (parallel engines) |
| Nmap Scan | `/nmap-scan/` | Port scan & service detection (`python-nmap`) |
| Analysis | `/analiz/` | Save reports as JSON, manual analyst notes, dashboard history |

**UI:** Collapsible sidebar, dark/light theme toggle, top operation bar (background job queue chips), command dashboard with scan queue table.

**Background jobs:** DNS, network, email, username, and nmap scans are enqueued to Redis; an RQ worker runs them while you continue using other modules. After submit you are redirected to the dashboard; progress appears in the top bar and on the dashboard queue table.

### Tech stack

- **Backend:** Django 6, Python 3.12
- **Database:** MySQL 8.4
- **Queue:** Redis 7 + django-rq
- **OSINT:** dnspython, python-whois, httpx, python-Wappalyzer, ipwhois, Holehe, Sherlock, Maigret, python-nmap

### Prerequisites

- Python 3.12+
- MySQL 8
- Redis 7 (recommended; Redis 5 works with `protocol: 2` in settings)
- **Nmap binary** on PATH ([download](https://nmap.org/download.html)) — `python-nmap` is only a wrapper
- Optional: `GITHUB_TOKEN` env var to reduce GitHub API rate limits

> **Legal notice:** Use only on targets you are authorized to test. The authors are not responsible for misuse.

### Quick start (Windows — recommended)

**Hybrid mode:** infra in Docker, Django + worker on the host.

```powershell
# 1. Infra (MySQL + Redis + phpMyAdmin)
scripts\start_infra.bat

# 2. First time only
env\Scripts\activate
pip install -r requirements.txt
python manage.py migrate

# 3. Web + worker in one step (opens worker in a second window)
scripts\start_dev.bat
```

Open **http://127.0.0.1:8000**

### Local setup (manual)

```bash
git clone <your-repo-url>
cd DjangoApp

python -m venv env
# Windows
env\Scripts\activate
# Linux / macOS
source env/bin/activate

pip install -r requirements.txt
```

Create the MySQL database:

```sql
CREATE DATABASE __django_app_db__ CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Copy environment template:

```bash
copy .env.example .env   # Windows
cp .env.example .env     # Linux / macOS
```

Run migrations and start services:

```bash
python manage.py migrate
python manage.py runserver
```

Start Redis and the RQ worker (separate terminals):

```bash
# Redis — Docker example
docker run -d -p 6379:6379 --name cyberops-redis redis:7-alpine

# Worker — Windows (no fork)
python manage.py rqworker default --worker-class rq.worker.SimpleWorker

# Worker — Linux / macOS
python manage.py rqworker default
```

### Windows helper scripts

| Script | Purpose |
|--------|---------|
| `scripts\start_dev.bat` | **Recommended:** RQ worker (new window) + `runserver` |
| `scripts\start_local_worker.bat` | RQ worker only (`SimpleWorker` for Windows) |
| `scripts\start_infra.bat` | Docker: MySQL + Redis + phpMyAdmin (`--profile infra`) |
| `scripts\start_docker.bat` | Docker: full stack (`--profile infra` + `--profile app`) |
| `scripts\stop_docker.bat` | Stop Docker Compose stack |
| `scripts\stop_local_worker.bat` | Info: how to close the worker window |

### Background scan queue — how it works

1. Submit a scan on DNS / Network / Email / Username / Nmap.
2. Job is enqueued to Redis → redirect to **dashboard** with a success message.
3. **Top bar:** chip shows *Running* → *Done* (click to open results).
4. **Dashboard:** *Scan queue* table lists all session jobs.
5. **Worker terminal:** must stay open (`Listening on default...`).

Image OSINT runs synchronously on the page (file upload).

To disable the queue and run scans synchronously (full-page wait):

```bash
set SCAN_USE_BACKGROUND_QUEUE=false   # Windows CMD
$env:SCAN_USE_BACKGROUND_QUEUE="false" # PowerShell
export SCAN_USE_BACKGROUND_QUEUE=false # Linux / macOS
```

### Docker setup

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose).

Copy `.env` from `.env.example` and set `MYSQL_ROOT_PASSWORD` = `DJANGO_DB_PASSWORD`.

#### Compose profiles

| Profile | Services | Use case |
|---------|----------|----------|
| `infra` | MySQL, Redis, phpMyAdmin | Local Django + local worker |
| `app` | Web, RQ worker | Full containerized app (needs `infra` too) |

Without `--profile`, nothing starts. Examples:

```bash
# Infra only — run Django on host
docker compose --profile infra up -d

# Full stack
docker compose --profile infra --profile app up --build -d
```

**Port conflict:** If old containers already use `3306` / `6379` / `8080`, stop them first or keep using them and skip `start_infra.bat`.

| Service | URL / Port |
|---------|------------|
| Web app | http://localhost:8000 |
| phpMyAdmin | http://localhost:8080 |
| MySQL | `localhost:3306` |
| Redis | `localhost:6379` |

Containers: `cyberops-web`, `cyberops-worker`, `cyberops-mysql`, `cyberops-redis`, `cyberops-phpmyadmin`

```bash
docker compose --profile infra --profile app logs -f web worker
docker compose --profile infra --profile app down
docker compose --profile infra --profile app down -v   # + delete volumes
```

Migrations run automatically on container start via `docker/entrypoint.sh`.

### Troubleshooting

| Issue | Fix |
|-------|-----|
| `unknown command HELLO` (Redis) | Use Redis 7, or keep `REDIS_CLIENT_KWARGS: {protocol: 2}` in `config/settings.py` |
| `os.fork` on Windows worker | Use `--worker-class rq.worker.SimpleWorker` (included in `start_local_worker.bat`) |
| Worker exits after first job | Restart with `start_local_worker.bat` / `start_dev.bat` |
| Compose stuck on `up` | Ports busy — `docker ps`, stop conflicting containers |
| Full-page preloader on scan | Restart `runserver`, hard refresh (`Ctrl+F5`); worker must be running |
| Wappalyzer import error | `pip install -r requirements.txt` (`python-Wappalyzer`, `setuptools<82`) |
| Nmap binary not found | Install Nmap, add to PATH, restart terminal |

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | (dev key) | Django secret — change in production |
| `DJANGO_DEBUG` | `true` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hosts |
| `DJANGO_DB_NAME` | `__django_app_db__` | MySQL database name |
| `DJANGO_DB_USER` | `root` | MySQL user |
| `DJANGO_DB_PASSWORD` | — | MySQL password |
| `DJANGO_DB_HOST` | `127.0.0.1` | MySQL host (`db` in Docker app containers) |
| `DJANGO_DB_PORT` | `3306` | MySQL port |
| `REDIS_HOST` | `127.0.0.1` | Redis host (`redis` in Docker app containers) |
| `REDIS_PORT` | `6379` | Redis port |
| `SCAN_USE_BACKGROUND_QUEUE` | `true` | Enable django-rq background scans |
| `GITHUB_TOKEN` | — | Optional GitHub API token |

See [`.env.example`](.env.example) for a full template.

### Project structure

```
DjangoApp/
├── app/
│   ├── core/          # Models (Analiz, AnalizItem)
│   └── web/
│       ├── services/  # OSINT & scan logic
│       ├── tasks/     # RQ background tasks
│       └── views/     # URL views per module
├── config/            # Django settings, urls, wsgi
├── templates/         # HTML templates
├── static/            # CSS, JS (theme, preloader, scan job tracker)
├── scripts/           # Windows .bat helpers
├── docker/            # entrypoint.sh
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── manage.py
```

### Nmap on Windows

1. Install from [nmap.org/download.html](https://nmap.org/download.html)
2. Check **Add Nmap to system PATH**
3. Restart terminal and verify: `nmap --version`

Without Nmap on PATH, the scan module returns a “binary not found” error.

---

## Türkçe

### Özellikler

| Modül | URL | Açıklama |
|-------|-----|----------|
| DNS Recon | `/dns-scan/` | DNS kayıtları, subdomain keşfi, WHOIS, web fingerprint (Wappalyzer), isteğe bağlı site snapshot |
| Network Intel | `/network-intel/` | GeoIP, RDAP (ipwhois), TLS, DNS intel, güvenlik header’ları, DNSBL |
| Image OSINT | `/image-osint/` | EXIF metadata okuma/yazma (Pillow, piexif) |
| Email OSINT | `/email-osint/` | Doğrulama, footprint, Holehe hesap keşfi |
| Username OSINT | `/username-osint/` | Sherlock, Maigret, GitHub (paralel motorlar) |
| Nmap Scan | `/nmap-scan/` | Port tarama ve servis tespiti (`python-nmap`) |
| Analiz | `/analiz/` | JSON rapor kaydı, manuel analist notları, panel geçmişi |

**Arayüz:** Açılır-kapanır sidebar, koyu/açık tema, üst işlem çubuğu (kuyruk chip’leri), komuta paneli ve tarama kuyruğu tablosu.

**Arka plan işleri:** DNS, network, email, username ve nmap taramaları Redis kuyruğuna alınır; gönderimden sonra dashboard’a yönlendirilirsiniz. İlerleme üst barda ve paneldeki kuyruk tablosunda görünür.

### Teknoloji

- **Backend:** Django 6, Python 3.12
- **Veritabanı:** MySQL 8.4
- **Kuyruk:** Redis 7 + django-rq
- **OSINT:** dnspython, python-whois, httpx, python-Wappalyzer, ipwhois, Holehe, Sherlock, Maigret, python-nmap

### Gereksinimler

- Python 3.12+
- MySQL 8
- Redis 7 (önerilir; Redis 5 için `settings.py` içinde `protocol: 2`)
- **Nmap binary** PATH’te ([indir](https://nmap.org/download.html))
- İsteğe bağlı: `GITHUB_TOKEN`

> **Yasal uyarı:** Yalnızca test etme yetkiniz olan hedeflerde kullanın.

### Hızlı başlangıç (Windows — önerilen)

**Hibrit mod:** altyapı Docker’da, Django + worker bilgisayarda.

```powershell
# 1. Altyapı (MySQL + Redis + phpMyAdmin)
scripts\start_infra.bat

# 2. İlk kurulum
env\Scripts\activate
pip install -r requirements.txt
python manage.py migrate

# 3. Web + worker tek komut (worker ayrı pencerede açılır)
scripts\start_dev.bat
```

Tarayıcı: **http://127.0.0.1:8000**

### Yerel kurulum (manuel)

```bash
git clone <repo-url>
cd DjangoApp

python -m venv env
env\Scripts\activate          # Windows
source env/bin/activate       # Linux / macOS

pip install -r requirements.txt
```

```sql
CREATE DATABASE __django_app_db__ CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
copy .env.example .env      # Windows
python manage.py migrate
python manage.py runserver
```

Worker (ayrı terminal):

```powershell
# Windows
scripts\start_local_worker.bat

# Linux / macOS
python manage.py rqworker default
```

### Windows script’leri

| Script | İşlev |
|--------|--------|
| `scripts\start_dev.bat` | **Önerilen:** worker (yeni pencere) + runserver |
| `scripts\start_local_worker.bat` | Sadece RQ worker (`SimpleWorker`) |
| `scripts\start_infra.bat` | Docker altyapı (`--profile infra`) |
| `scripts\start_docker.bat` | Tam Docker stack |
| `scripts\stop_docker.bat` | Compose stack’i durdur |
| `scripts\stop_local_worker.bat` | Worker penceresini kapatma bilgisi |

### Arka plan kuyruğu — nasıl takip edilir?

1. Modülde hedef girip **Tara**’ya basın.
2. İş Redis’e alınır → **dashboard**’a yönlendirilirsiniz.
3. **Üst bar:** chip *Çalışıyor* → *Tamam* (sonuç için tıklayın).
4. **Dashboard:** *Tarama kuyruğu* tablosu.
5. **Worker terminali** açık kalmalı: `Listening on default...`

Image OSINT dosya yüklemesi sayfada senkron çalışır.

Kuyruğu kapatmak için `.env`:

```text
SCAN_USE_BACKGROUND_QUEUE=false
```

### Docker ile kurulum

`.env.example` → `.env`; `MYSQL_ROOT_PASSWORD` = `DJANGO_DB_PASSWORD`.

#### Compose profile’ları

| Profile | Servisler | Kullanım |
|---------|-----------|----------|
| `infra` | MySQL, Redis, phpMyAdmin | Yerel Django + yerel worker |
| `app` | Web, RQ worker | Tam Docker ( `infra` ile birlikte ) |

Profile olmadan hiçbir servis başlamaz:

```bash
docker compose --profile infra up -d
docker compose --profile infra --profile app up --build -d
```

**Port çakışması:** `3306` / `6379` / `8080` doluysa eski konteynerleri durdurun veya onları kullanıp `start_infra.bat` çalıştırmayın.

| Servis | Adres |
|--------|--------|
| Uygulama | http://localhost:8000 |
| phpMyAdmin | http://localhost:8080 |
| MySQL | `localhost:3306` |
| Redis | `localhost:6379` |

Konteynerler: `cyberops-web`, `cyberops-worker`, `cyberops-mysql`, `cyberops-redis`, `cyberops-phpmyadmin`

### Sorun giderme

| Sorun | Çözüm |
|-------|--------|
| `unknown command HELLO` | Redis 7 kullanın veya `REDIS_CLIENT_KWARGS: {protocol: 2}` |
| `os.fork` (Windows) | `SimpleWorker` — `start_local_worker.bat` |
| Worker ilk işten sonra kapanır | Worker’ı `start_dev.bat` ile yeniden başlatın |
| Compose takılı kalır | Port çakışması — `docker ps` |
| Tam ekran preloader | `runserver` + worker yeniden, `Ctrl+F5` |
| Wappalyzer hatası | `pip install -r requirements.txt` |
| Nmap bulunamadı | Nmap kur, PATH’e ekle |

### Ortam değişkenleri

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `DJANGO_SECRET_KEY` | (dev) | Production’da değiştirin |
| `DJANGO_DEBUG` | `true` | Debug |
| `DJANGO_DB_*` | — | MySQL bağlantısı |
| `REDIS_HOST` / `REDIS_PORT` | `127.0.0.1` / `6379` | Redis |
| `SCAN_USE_BACKGROUND_QUEUE` | `true` | Arka plan kuyruğu |

Tam liste: [`.env.example`](.env.example)

### Proje yapısı

```
DjangoApp/
├── app/core/          # Modeller
├── app/web/           # Servisler, task’lar, view’lar
├── config/            # Django ayarları
├── templates/         # HTML
├── static/            # CSS, JS (tema, kuyruk takibi)
├── scripts/           # Windows .bat
├── docker-compose.yml
└── manage.py
```

### Windows’ta Nmap

1. [nmap.org/download.html](https://nmap.org/download.html) → installer
2. **Add Nmap to system PATH** işaretleyin
3. `nmap --version` ile doğrulayın

---

## License

Add your license here (e.g. MIT) before publishing to GitHub.
