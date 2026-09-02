# CYBER OPS — Project Detail / Proje Detayı

> **Last reviewed:** September 2026  
> **Stack:** Django 6 · Python 3.12 · MySQL 8.4 · Redis 7 · django-rq

---

## Table of Contents / İçindekiler

1. [Overview / Genel Bakış](#1-overview--genel-bakış)
2. [Project Structure / Proje Yapısı](#2-project-structure--proje-yapısı)
3. [Python Packages / Python Paketleri](#3-python-packages--python-paketleri)
4. [Infrastructure / Altyapı](#4-infrastructure--altyapı)
5. [Application Architecture / Uygulama Mimarisi](#5-application-architecture--uygulama-mimarisi)
6. [OSINT Modules / OSINT Modülleri](#6-osint-modules--osint-modülleri)
7. [Scan Queue System / Tarama Kuyruğu](#7-scan-queue-system--tarama-kuyruğu)
8. [Frontend & UI / Arayüz](#8-frontend--ui--arayüz)
9. [Configuration / Yapılandırma](#9-configuration--yapılandırma)
10. [Scripts & Deployment / Betikler ve Dağıtım](#10-scripts--deployment--betikler-ve-dağıtım)
11. [Data Models / Veri Modelleri](#11-data-models--veri-modelleri)
12. [URL Map / URL Haritası](#12-url-map--url-haritası)

---

## 1. Overview / Genel Bakış

### English

**CYBER OPS** is a Django-based OSINT (Open Source Intelligence) and reconnaissance console. It provides six investigative modules plus a unified analysis/reporting layer. Scans can run synchronously or in a Redis-backed background queue so analysts can submit long-running jobs and continue working in other modules.

Key characteristics:

- **Modular service layer** — each OSINT domain has dedicated Python services under `app/web/services/`
- **Hybrid deployment** — Docker for infrastructure (MySQL, Redis, phpMyAdmin) + local Django/RQ worker on Windows, or full Docker stack
- **Session-based job tracking** — background scans tracked per browser session (max 30 jobs)
- **Report persistence** — full JSON reports saved to MySQL with manual analyst items
- **Dark/light theme**, collapsible sidebar, topbar operation tracker with cancel support

> ⚠️ For authorized targets only. Use only on systems you own or have explicit permission to test.

### Türkçe

**CYBER OPS**, Django tabanlı bir OSINT (Açık Kaynak İstihbarat) ve keşif konsoludur. Altı araştırma modülü ve birleşik analiz/raporlama katmanı sunar. Taramalar senkron çalışabilir veya Redis destekli arka plan kuyruğunda yürütülebilir; analist uzun süren işleri başlatıp diğer modüllerde çalışmaya devam edebilir.

Temel özellikler:

- **Modüler servis katmanı** — her OSINT alanı `app/web/services/` altında ayrı Python servislerine sahip
- **Hibrit dağıtım** — altyapı için Docker (MySQL, Redis, phpMyAdmin) + Windows’ta yerel Django/RQ worker, veya tam Docker stack
- **Oturum tabanlı iş takibi** — arka plan taramaları tarayıcı oturumu başına izlenir (en fazla 30 iş)
- **Rapor kalıcılığı** — tam JSON raporlar MySQL’e kaydedilir, manuel analist maddeleri eklenebilir
- **Koyu/açık tema**, katlanabilir kenar çubuğu, iptal destekli üst bar işlem izleyici

> ⚠️ Yalnızca yetkili hedefler için. Yalnızca sahip olduğunuz veya test izniniz olan sistemlerde kullanın.

---

## 2. Project Structure / Proje Yapısı

### English

```
DjangoApp/
├── app/                        # Django applications
│   ├── core/                   # Data models (Analiz, AnalizItem)
│   │   ├── models.py
│   │   ├── apps.py
│   │   └── migrations/
│   └── web/                    # Main web application
│       ├── urls.py             # Root URL router
│       ├── context_processors.py
│       ├── views/              # Per-module views + scan job API
│       │   ├── dashboard.py
│       │   ├── dns_scan/
│       │   ├── network/
│       │   ├── image_osint/
│       │   ├── email_osint/
│       │   ├── username_osint/
│       │   ├── nmap_scan/
│       │   ├── scan_job/       # Queue status & cancel API
│       │   └── analiz/         # Report save/detail/export
│       ├── services/           # Business logic
│       │   ├── common/         # scanJobService, analizService, fileUpload
│       │   ├── dns/
│       │   ├── network/
│       │   ├── email/
│       │   ├── username/
│       │   ├── nmap/
│       │   └── image/
│       └── tasks/
│           └── scan_tasks.py   # RQ worker entry points
├── config/                     # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── templates/                  # HTML (base, pages, partials)
├── static/                     # CSS & JavaScript
├── media/                      # Uploads & site snapshots (runtime)
├── scripts/                    # Windows .bat helpers
├── docker/
│   └── entrypoint.sh
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── requirements.txt
├── .env / .env.example
└── README.md
```

### Türkçe

```
DjangoApp/
├── app/                        # Django uygulamaları
│   ├── core/                   # Veri modelleri (Analiz, AnalizItem)
│   │   ├── models.py
│   │   ├── apps.py
│   │   └── migrations/
│   └── web/                    # Ana web uygulaması
│       ├── urls.py             # Kök URL yönlendirici
│       ├── context_processors.py
│       ├── views/              # Modül view’ları + tarama işi API
│       │   ├── dashboard.py
│       │   ├── dns_scan/
│       │   ├── network/
│       │   ├── image_osint/
│       │   ├── email_osint/
│       │   ├── username_osint/
│       │   ├── nmap_scan/
│       │   ├── scan_job/       # Kuyruk durumu ve iptal API
│       │   └── analiz/         # Rapor kaydet/detay/dışa aktar
│       ├── services/           # İş mantığı
│       │   ├── common/         # scanJobService, analizService, fileUpload
│       │   ├── dns/
│       │   ├── network/
│       │   ├── email/
│       │   ├── username/
│       │   ├── nmap/
│       │   └── image/
│       └── tasks/
│           └── scan_tasks.py   # RQ worker giriş noktaları
├── config/                     # Django proje yapılandırması
├── templates/                  # HTML şablonları
├── static/                     # CSS ve JavaScript
├── media/                      # Yüklemeler ve site anlık görüntüleri
├── scripts/                    # Windows .bat yardımcıları
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── requirements.txt
└── README.md
```

### Layer Responsibilities / Katman Sorumlulukları

| Layer / Katman | Path | EN | TR |
|----------------|------|----|----|
| Views | `app/web/views/` | HTTP request handling, form POST, template rendering | HTTP istekleri, form POST, şablon render |
| Services | `app/web/services/` | OSINT logic, external API calls, parsing | OSINT mantığı, harici API çağrıları, ayrıştırma |
| Tasks | `app/web/tasks/` | Background worker functions (RQ) | Arka plan worker fonksiyonları (RQ) |
| Models | `app/core/models.py` | Persistent report storage | Kalıcı rapor depolama |
| Templates | `templates/` | Server-side HTML | Sunucu tarafı HTML |
| Static | `static/` | Client-side CSS/JS | İstemci tarafı CSS/JS |

---

## 3. Python Packages / Python Paketleri

### English — `requirements.txt`

| Package | Version | Purpose |
|---------|---------|---------|
| **Django** | ≥6.0 | Web framework |
| **mysqlclient** | ≥2.2.0 | MySQL database driver |
| **python-dotenv** | ≥1.0.0 | Load `.env` configuration |
| **dnspython** | — | DNS record lookups, subdomain discovery |
| **python-whois** | — | WHOIS queries (DNS module) |
| **httpx** | — | HTTP client (headers, snapshots, APIs) |
| **python-Wappalyzer** | ≥0.3.1 | Web technology fingerprinting |
| **setuptools** | <82 | Required by python-Wappalyzer (pkg_resources) |
| **Pillow** | — | Image processing, EXIF read |
| **piexif** | — | EXIF write for JPEG (Image OSINT) |
| **holehe** | — | Email account discovery across sites |
| **sherlock-project** | — | Username search across social platforms |
| **maigret** | — | Deep username OSINT (standard/deep modes) |
| **python-nmap** | — | Nmap scan wrapper (requires nmap binary) |
| **ipwhois** | ≥1.3.0 | RDAP/ASN/GeoIP for Network Intel |
| **django-rq** | ≥2.10 | Django integration for Redis Queue |
| **redis** | ≥5.0 | Redis client for job queue |

### Optional / Not in requirements.txt

| Package | Purpose | Install |
|---------|---------|---------|
| **playwright** | Site snapshot (rendered DOM + assets) in DNS module | `pip install playwright && playwright install chromium` |
| **nmap** (system binary) | Port scanning for Nmap module | OS package / [nmap.org](https://nmap.org) |

### Türkçe — `requirements.txt`

| Paket | Sürüm | Amaç |
|-------|-------|------|
| **Django** | ≥6.0 | Web çatısı |
| **mysqlclient** | ≥2.2.0 | MySQL veritabanı sürücüsü |
| **python-dotenv** | ≥1.0.0 | `.env` yapılandırması yükleme |
| **dnspython** | — | DNS kayıt sorguları, alt alan adı keşfi |
| **python-whois** | — | WHOIS sorguları (DNS modülü) |
| **httpx** | — | HTTP istemcisi (header, snapshot, API) |
| **python-Wappalyzer** | ≥0.3.1 | Web teknoloji parmak izi |
| **setuptools** | <82 | python-Wappalyzer bağımlılığı (pkg_resources) |
| **Pillow** | — | Görüntü işleme, EXIF okuma |
| **piexif** | — | JPEG EXIF yazma (Image OSINT) |
| **holehe** | — | E-posta hesap keşfi (site bazlı) |
| **sherlock-project** | — | Kullanıcı adı araması (sosyal platformlar) |
| **maigret** | — | Derin kullanıcı adı OSINT (standard/deep) |
| **python-nmap** | — | Nmap tarama sarmalayıcısı (nmap binary gerekir) |
| **ipwhois** | ≥1.3.0 | RDAP/ASN/GeoIP (Network Intel) |
| **django-rq** | ≥2.10 | Redis Queue Django entegrasyonu |
| **redis** | ≥5.0 | İş kuyruğu Redis istemcisi |

### İsteğe Bağlı / requirements.txt dışında

| Paket | Amaç | Kurulum |
|-------|------|---------|
| **playwright** | Site anlık görüntüsü (DNS modülü) | `pip install playwright && playwright install chromium` |
| **nmap** (sistem binary) | Nmap modülü port taraması | İşletim sistemi paketi |

### External Services Used / Kullanılan Harici Servisler

| Service | Module | EN | TR |
|---------|--------|----|----|
| crt.sh | DNS | Certificate transparency subdomain discovery | Sertifika şeffaflığı alt alan keşfi |
| Shodan InternetDB | Network | Passive exposure data | Pasif maruziyet verisi |
| DNSBL lists | Network | IP/domain reputation | IP/alan adı itibarı |
| GitHub API | Username | Profile lookup (optional `GITHUB_TOKEN`) | Profil araması (isteğe bağlı token) |
| Gravatar | Email | Email hash → avatar check | E-posta hash → avatar kontrolü |

---

## 4. Infrastructure / Altyapı

### English

| Component | Technology | Default Port | Role |
|-----------|------------|--------------|------|
| Web app | Django 6 + Gunicorn (Docker) / runserver (dev) | 8000 | HTTP UI & API |
| Database | MySQL 8.4 | 3306 | Reports, analiz storage |
| Queue broker | Redis 7 | 6379 | Background scan jobs |
| Worker | django-rq / RQ (`SimpleWorker` on Windows) | — | Executes scan tasks |
| DB admin | phpMyAdmin | 8080 | Optional MySQL UI |

**Docker Compose profiles:**

- `infra` — MySQL, Redis, phpMyAdmin only
- `app` — web + worker containers (requires `infra`)

**Recommended Windows dev flow:**

1. `scripts\start_infra.bat` — start Docker infra
2. `py manage.py migrate`
3. `scripts\start_dev.bat` — RQ worker (new window) + runserver

### Türkçe

| Bileşen | Teknoloji | Varsayılan Port | Rol |
|---------|-----------|-----------------|-----|
| Web uygulaması | Django 6 + Gunicorn (Docker) / runserver (dev) | 8000 | HTTP arayüz ve API |
| Veritabanı | MySQL 8.4 | 3306 | Raporlar, analiz depolama |
| Kuyruk aracısı | Redis 7 | 6379 | Arka plan tarama işleri |
| Worker | django-rq / RQ (Windows’ta `SimpleWorker`) | — | Tarama görevlerini çalıştırır |
| DB yönetimi | phpMyAdmin | 8080 | İsteğe bağlı MySQL arayüzü |

**Docker Compose profilleri:**

- `infra` — yalnızca MySQL, Redis, phpMyAdmin
- `app` — web + worker konteynerleri (`infra` gerekir)

**Önerilen Windows geliştirme akışı:**

1. `scripts\start_infra.bat` — Docker altyapısını başlat
2. `py manage.py migrate`
3. `scripts\start_dev.bat` — RQ worker (yeni pencere) + runserver

---

## 5. Application Architecture / Uygulama Mimarisi

### English

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (Tailwind CDN + static JS/CSS)                     │
│  ├── Sidebar navigation                                     │
│  ├── Topbar scan job tracker (poll /scan-job/active/)       │
│  └── Module pages (forms → POST)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────┐
│  Django (app/web/views/)                                    │
│  └── dispatch_scan() → queue or sync                        │
└──────────┬─────────────────────────────┬────────────────────┘
           │                             │
    ┌──────▼──────┐               ┌──────▼──────┐
    │  MySQL      │               │  Redis/RQ   │
    │  (Analiz)   │               │  (scan jobs)│
    └─────────────┘               └──────┬──────┘
                                         │
                                  ┌──────▼──────┐
                                  │ RQ Worker   │
                                  │ scan_tasks  │
                                  └──────┬──────┘
                                         │
                                  ┌──────▼──────┐
                                  │  Services   │
                                  │  (OSINT)    │
                                  └─────────────┘
```

**Installed Django apps:** `core`, `web`, `django_rq` (+ Django built-ins)

**Key design patterns:**

- **Service-oriented** — views are thin; logic lives in `services/`
- **Unified scan dispatch** — `scanJobService.dispatch_scan()` handles queue/sync for all scan modules
- **Payload contract** — worker tasks return `{ context_updates, analiz, error }`
- **Session job registry** — `scan_jobs` session key tracks job IDs, targets, return paths

### Türkçe

```
┌─────────────────────────────────────────────────────────────┐
│  Tarayıcı (Tailwind CDN + static JS/CSS)                    │
│  ├── Kenar çubuğu navigasyon                                │
│  ├── Üst bar tarama işi izleyici (/scan-job/active/)        │
│  └── Modül sayfaları (form → POST)                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────┐
│  Django (app/web/views/)                                    │
│  └── dispatch_scan() → kuyruk veya senkron                  │
└──────────┬─────────────────────────────┬────────────────────┘
           │                             │
    ┌──────▼──────┐               ┌──────▼──────┐
    │  MySQL      │               │  Redis/RQ   │
    │  (Analiz)   │               │  (tarama)   │
    └─────────────┘               └──────┬──────┘
                                         │
                                  ┌──────▼──────┐
                                  │ RQ Worker   │
                                  │ scan_tasks  │
                                  └──────┬──────┘
                                         │
                                  ┌──────▼──────┐
                                  │  Servisler  │
                                  │  (OSINT)    │
                                  └─────────────┘
```

**Yüklü Django uygulamaları:** `core`, `web`, `django_rq` (+ Django yerleşik)

**Temel tasarım kalıpları:**

- **Servis odaklı** — view’lar ince; mantık `services/` içinde
- **Birleşik tarama yönlendirme** — `scanJobService.dispatch_scan()` tüm modüller için kuyruk/senkron yönetir
- **Payload sözleşmesi** — worker görevleri `{ context_updates, analiz, error }` döner
- **Oturum iş kaydı** — `scan_jobs` oturum anahtarı iş ID, hedef ve dönüş yollarını tutar

---

## 6. OSINT Modules / OSINT Modülleri

### DNS Recon — `/dns-scan/`

| | English | Türkçe |
|---|---------|--------|
| **Service** | `dnsServices.py`, `siteSnapshot.py` | Aynı |
| **Features** | A/AAAA/CNAME/MX/NS/TXT/SOA/CAA/SRV records; reverse DNS (PTR); crt.sh + wordlist subdomain discovery; WHOIS; HTTP headers, cookies, Wappalyzer tech stack; optional Playwright site snapshot → `media/site_snapshots/` | A/AAAA/CNAME/MX/NS/TXT/SOA/CAA/SRV kayıtları; ters DNS (PTR); crt.sh + wordlist alt alan keşfi; WHOIS; HTTP header, cookie, Wappalyzer teknoloji yığını; isteğe bağlı Playwright site snapshot |
| **Queue** | Yes (`run_dns_scan`) | Evet |

### Network Intel — `/network-intel/`

| | English | Türkçe |
|---|---------|--------|
| **Service** | `NetworkIntelService.py` | Aynı |
| **Features** | Domain or IP input; IPv4/IPv6 resolution; GeoIP + ASN (ipwhois); RDAP; Shodan InternetDB; DNS intel (SPF/DMARC/MX/NS); TLS certificate; security headers audit; DNSBL reputation; infrastructure classification + threat score | Alan adı veya IP; IPv4/IPv6 çözümleme; GeoIP + ASN; RDAP; Shodan InternetDB; DNS intel; TLS sertifikası; güvenlik header denetimi; DNSBL itibarı; altyapı sınıflandırma + tehdit skoru |
| **Queue** | Yes (`run_network_intel`) | Evet |

### Email OSINT — `/email-osint/`

| | English | Türkçe |
|---|---------|--------|
| **Services** | `emailOsintService.py`, `emailValidationService.py`, `emailFootprintService.py`, `holeheAccountService.py` | Aynı |
| **Features** | Email validation/normalization; MX, SPF, DMARC, NS; Gravatar hash; WHOIS; disposable domain check; Holehe account discovery (async) | E-posta doğrulama/normalizasyon; MX, SPF, DMARC, NS; Gravatar hash; WHOIS; tek kullanımlık domain kontrolü; Holehe hesap keşfi |
| **Queue** | Yes (`run_email_osint`) | Evet |

### Username OSINT — `/username-osint/`

| | English | Türkçe |
|---|---------|--------|
| **Services** | `usernameOsintService.py`, `sherlockScanService.py`, `maigretScanService.py`, `githubProfileService.py`, `usernameMergeService.py`, `usernameRiskService.py`, `usernameValidationService.py` | Aynı |
| **Features** | Validation; optional variant generation; parallel Sherlock + Maigret + GitHub; scan modes: quick / standard / deep; merge + risk scoring; DB cache for Sherlock/Maigret results | Doğrulama; isteğe bağlı varyant üretimi; paralel Sherlock + Maigret + GitHub; tarama modları: quick / standard / deep; birleştirme + risk skoru; Sherlock/Maigret sonuç önbelleği |
| **Queue** | Yes (`run_username_osint`) | Evet |

### Nmap Scan — `/nmap-scan/`

| | English | Türkçe |
|---|---------|--------|
| **Service** | `nmapScanService.py` | Aynı |
| **Features** | Profiles: quick (top 100), standard (top 1000 + service), deep (all ports); requires **nmap on PATH**; parses hosts, ports, services | Profiller: quick, standard, deep; **PATH’te nmap** gerekir; host, port, servis ayrıştırma |
| **Queue** | Yes (`run_nmap_scan`) | Evet |

### Image OSINT — `/image-osint/`

| | English | Türkçe |
|---|---------|--------|
| **Services** | `imageMetadataService.py`, `imageMetadataWriteService.py` | Aynı |
| **Features** | File upload; EXIF read (Pillow): basic info, tags, GPS; EXIF write for JPEG (piexif); uploads → `media/uploads/metadata/` | Dosya yükleme; EXIF okuma: temel bilgi, etiketler, GPS; JPEG EXIF yazma; yüklemeler → `media/uploads/metadata/` |
| **Queue** | **No** — synchronous on request | **Hayır** — istek üzerinde senkron |

### Analiz (Reports) — `/analiz/`

| | English | Türkçe |
|---|---------|--------|
| **Routes** | Save, detail, JSON export, manual item add/delete | Kaydet, detay, JSON dışa aktar, manuel madde ekle/sil |
| **Purpose** | Persist full JSON reports + analyst notes to MySQL; attach save widget to scan results | Tam JSON raporları + analist notlarını MySQL’e kaydet; tarama sonuçlarına kaydet widget’ı ekle |

---

## 7. Scan Queue System / Tarama Kuyruğu

### English

**Flow:**

1. User submits scan form (POST)
2. `dispatch_scan()` checks `SCAN_USE_BACKGROUND_QUEUE`
3. If enabled → job enqueued to Redis `default` queue → session registered → redirect to dashboard
4. RQ worker picks job → `scan_tasks.run_*()` → returns result payload
5. User opens result via topbar chip or `?job_id=` URL
6. `fetch_job_payload()` resolves status; `apply_scan_payload()` renders results

**Job API endpoints:**

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/scan-job/active/` | List session jobs with status |
| GET | `/scan-job/<id>/status/` | Single job status |
| POST | `/scan-job/<id>/cancel/` | Cancel one job |
| POST | `/scan-job/cancel-all/` | Cancel all pending jobs |

**Job statuses:** `pending`, `finished`, `failed`, `cancelled`, `missing`

**Settings:** 1h job timeout, 24h result TTL, max 30 jobs per session, Redis protocol 2 (`REDIS_CLIENT_KWARGS`)

**Windows note:** Worker uses `SimpleWorker` (no `fork()`). Long-running scans may not stop instantly on cancel; session flag marks UI as cancelled.

### Türkçe

**Akış:**

1. Kullanıcı tarama formunu gönderir (POST)
2. `dispatch_scan()` `SCAN_USE_BACKGROUND_QUEUE` değerini kontrol eder
3. Açıksa → iş Redis `default` kuyruğuna alınır → oturuma kaydedilir → dashboard’a yönlendirilir
4. RQ worker işi alır → `scan_tasks.run_*()` → sonuç payload döner
5. Kullanıcı üst bar chip veya `?job_id=` URL ile sonucu açar
6. `fetch_job_payload()` durumu çözer; `apply_scan_payload()` sonuçları render eder

**İş API uçları:**

| Metot | URL | Amaç |
|-------|-----|------|
| GET | `/scan-job/active/` | Oturum işlerini durumla listele |
| GET | `/scan-job/<id>/status/` | Tek iş durumu |
| POST | `/scan-job/<id>/cancel/` | Tek iş iptal |
| POST | `/scan-job/cancel-all/` | Tüm bekleyen işleri iptal |

**İş durumları:** `pending`, `finished`, `failed`, `cancelled`, `missing`

**Ayarlar:** 1 saat iş zaman aşımı, 24 saat sonuç TTL, oturum başına en fazla 30 iş, Redis protokol 2

**Windows notu:** Worker `SimpleWorker` kullanır (`fork()` yok). Uzun taramalar iptalde anında durmayabilir; oturum bayrağı arayüzde iptal gösterir.

---

## 8. Frontend & UI / Arayüz

### English

| Asset | Path | Purpose |
|-------|------|---------|
| `base.html` | `templates/` | Layout: sidebar, topbar, theme, CSRF meta |
| `theme.css` / `theme.js` | `static/` | Dark/light mode toggle |
| `ui.css` | `static/` | Global UI polish (cards, forms, tables) |
| `sidebar.js` | `static/` | Collapsible sidebar (desktop + mobile) |
| `preloader.js/css` | `static/` | Hacker-themed loading overlay (sync scans) |
| `scan_job_tracker.js/css` | `static/` | Topbar job chips, polling, cancel buttons |
| `analiz_kaydet.js/css` | `static/` | Right-dock report save widget |
| `pages/*.css` | `static/css/pages/` | Per-module page styles |

**External CDN:** Tailwind CSS, Google Fonts (IBM Plex Mono, Rajdhani, Material Symbols)

### Türkçe

| Varlık | Yol | Amaç |
|--------|-----|------|
| `base.html` | `templates/` | Düzen: kenar çubuğu, üst bar, tema, CSRF meta |
| `theme.css` / `theme.js` | `static/` | Koyu/açık mod geçişi |
| `ui.css` | `static/` | Genel arayüz iyileştirmeleri |
| `sidebar.js` | `static/` | Katlanabilir kenar çubuğu |
| `preloader.js/css` | `static/` | Hacker temalı yükleme ekranı (senkron taramalar) |
| `scan_job_tracker.js/css` | `static/` | Üst bar iş chip’leri, polling, iptal butonları |
| `analiz_kaydet.js/css` | `static/` | Sağ dock rapor kaydet widget’ı |
| `pages/*.css` | `static/css/pages/` | Modül bazlı sayfa stilleri |

**Harici CDN:** Tailwind CSS, Google Fonts, Material Symbols

---

## 9. Configuration / Yapılandırma

### Environment Variables / Ortam Değişkenleri

| Variable | Default | EN | TR |
|----------|---------|----|----|
| `DJANGO_DEBUG` | `true` | Debug mode | Hata ayıklama modu |
| `DJANGO_SECRET_KEY` | (dev key) | Session/crypto secret | Oturum/şifreleme anahtarı |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed HTTP hosts | İzin verilen HTTP host’ları |
| `DJANGO_DB_*` | see `.env.example` | MySQL connection | MySQL bağlantısı |
| `REDIS_*` | `127.0.0.1:6379` | Queue broker | Kuyruk aracısı |
| `SCAN_USE_BACKGROUND_QUEUE` | `true` | Enable async scans | Arka plan taramalarını aç |
| `GITHUB_TOKEN` | — | Optional GitHub API rate limit | İsteğe bağlı GitHub API limiti |
| `MYSQL_PORT`, `WEB_PORT`, etc. | — | Docker Compose port overrides | Docker port eşlemeleri |

### Key Django Settings / Önemli Django Ayarları

| Setting | Value | EN | TR |
|---------|-------|----|----|
| `INSTALLED_APPS` | `core`, `web`, `django_rq` | Custom + queue app | Özel + kuyruk uygulaması |
| `DATABASES` | MySQL, `CONN_MAX_AGE=600` | Persistent connections | Kalıcı bağlantılar |
| `RQ_QUEUES.default` | Redis + `protocol: 2` | Fixes Redis 5 HELLO issue | Redis 5 HELLO sorununu giderir |
| `MEDIA_ROOT` | `media/` | Uploads & snapshots | Yüklemeler ve snapshot’lar |
| `STATICFILES_DIRS` | `static/` | Dev static files | Geliştirme static dosyaları |

---

## 10. Scripts & Deployment / Betikler ve Dağıtım

### English

| Script | Command / Action |
|--------|-------------------|
| `scripts/start_infra.bat` | `docker compose --profile infra up -d` |
| `scripts/start_dev.bat` | Opens worker window + `runserver` |
| `scripts/start_local_worker.bat` | RQ worker with `SimpleWorker` (Windows) |
| `scripts/start_rqworker.bat` | Minimal worker launcher |
| `scripts/start_docker.bat` | Full stack: infra + app |
| `scripts/stop_docker.bat` | Stop Compose stack |
| `scripts/stop_local_worker.bat` | Instructions to close worker window |

**Docker container commands** (`docker/entrypoint.sh`):

- `web` — wait for MySQL/Redis, migrate, start Gunicorn
- `worker` — wait for deps, start `rqworker default`

### Türkçe

| Betik | Komut / Eylem |
|-------|---------------|
| `scripts/start_infra.bat` | `docker compose --profile infra up -d` |
| `scripts/start_dev.bat` | Worker penceresi + `runserver` açar |
| `scripts/start_local_worker.bat` | `SimpleWorker` ile RQ worker (Windows) |
| `scripts/start_rqworker.bat` | Minimal worker başlatıcı |
| `scripts/start_docker.bat` | Tam stack: infra + app |
| `scripts/stop_docker.bat` | Compose stack’i durdur |
| `scripts/stop_local_worker.bat` | Worker penceresini kapatma talimatı |

**Docker konteyner komutları** (`docker/entrypoint.sh`):

- `web` — MySQL/Redis bekle, migrate, Gunicorn başlat
- `worker` — bağımlılıkları bekle, `rqworker default` başlat

---

## 11. Data Models / Veri Modelleri

### English

**`Analiz`** (`analiz` table)

| Field | Type | Description |
|-------|------|-------------|
| `target` | CharField(255) | Scan target (domain, email, username, IP, etc.) |
| `module` | CharField(32) | One of: dns_scan, network_intel, image_osint, email_osint, username_osint, nmap_scan |
| `analyst_note` | TextField | Free-text analyst note |
| `report_json` | JSONField | Full scan report payload |
| `created_at` | DateTimeField | Auto timestamp |

**`AnalizItem`** (`analiz_item` table)

| Field | Type | Description |
|-------|------|-------------|
| `analiz` | FK → Analiz | Parent report |
| `key` | CharField(512) | Finding key/label |
| `value` | TextField | Finding value/detail |

### Türkçe

**`Analiz`** (`analiz` tablosu)

| Alan | Tip | Açıklama |
|------|-----|----------|
| `target` | CharField(255) | Tarama hedefi (alan adı, e-posta, kullanıcı adı, IP vb.) |
| `module` | CharField(32) | Modül: dns_scan, network_intel, image_osint, email_osint, username_osint, nmap_scan |
| `analyst_note` | TextField | Serbest analist notu |
| `report_json` | JSONField | Tam tarama raporu |
| `created_at` | DateTimeField | Otomatik zaman damgası |

**`AnalizItem`** (`analiz_item` tablosu)

| Alan | Tip | Açıklama |
|------|-----|----------|
| `analiz` | FK → Analiz | Üst rapor |
| `key` | CharField(512) | Bulgu anahtarı/etiketi |
| `value` | TextField | Bulgu değeri/detayı |

---

## 12. URL Map / URL Haritası

| URL | Name | Module / Modül |
|-----|------|----------------|
| `/` | `dashboard` | Command dashboard / Komuta paneli |
| `/dns-scan/` | `dns_scan` | DNS recon |
| `/network-intel/` | `network_intel` | Network intel |
| `/image-osint/` | `image_osint` | Image OSINT |
| `/email-osint/` | `email_osint` | Email OSINT |
| `/username-osint/` | `username_osint` | Username OSINT |
| `/nmap-scan/` | `nmap_scan` | Nmap scan |
| `/scan-job/active/` | `scan_jobs_active` | Queue API — active jobs |
| `/scan-job/<id>/cancel/` | `scan_job_cancel` | Queue API — cancel job |
| `/scan-job/cancel-all/` | `scan_jobs_cancel_all` | Queue API — cancel all |
| `/scan-job/<id>/status/` | `scan_job_status` | Queue API — job status |
| `/analiz/kaydet/` | — | Save report |
| `/analiz/<pk>/` | `analiz_detail` | Report detail |
| `/analiz/<pk>/json/` | `analiz_json` | JSON export |
| `/admin/` | — | Django admin |

---

## Quick Reference / Hızlı Referans

### English

```powershell
# 1. Start infrastructure
scripts\start_infra.bat

# 2. Migrate database
py manage.py migrate

# 3. Start dev (worker + server)
scripts\start_dev.bat

# 4. Open app
# http://127.0.0.1:8000
```

**Prerequisites:** Python 3.12, Docker Desktop (for infra), virtualenv at `env/`, nmap on PATH (Nmap module), optional Playwright for site snapshots.

### Türkçe

```powershell
# 1. Altyapıyı başlat
scripts\start_infra.bat

# 2. Veritabanı migrate
py manage.py migrate

# 3. Geliştirme ortamı (worker + sunucu)
scripts\start_dev.bat

# 4. Uygulamayı aç
# http://127.0.0.1:8000
```

**Gereksinimler:** Python 3.12, Docker Desktop (altyapı için), `env/` sanal ortam, PATH’te nmap (Nmap modülü), site snapshot için isteğe bağlı Playwright.

---

*See also / Ayrıca bakınız: [README.md](README.md)*
