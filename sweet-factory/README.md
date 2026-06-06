# 🍬 Sweet Factory Cloud ERP Platform

> **BTEC Unit 6: Networking in the Cloud** — Learning Aims A, B, C, D  
> Professional Cloud-Native ERP/CRM/WMS Platform on AWS

---

## 📋 Project Overview

Sweet Factory is a comprehensive cloud-native ERP platform for a confectionery manufacturer.
It unifies **Production Management (ERP)**, **Customer Relationship (CRM)**, and **Warehouse Management (WMS)**
into a single secure AWS-hosted platform.

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python 3.12 |
| Database | PostgreSQL 16 (RDS) |
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Container | Docker + Docker Compose |
| Cloud | AWS (VPC, ALB, RDS, ECS, Route53) |
| CI/CD | GitHub Actions |
| Proxy | NGINX |

---

## 🏗️ AWS Architecture

```
Internet
    │
    ▼
Route53 (DNS: sweetfactory.com)
    │
    ▼
Application Load Balancer (Public Subnets: us-east-1a, us-east-1b)
    │
    ▼
Auto Scaling Group (ECS Fargate Tasks)
    │
    ├── FastAPI App Containers (Port 8000)
    │
    ▼
VPC: 10.0.0.0/16
    ├── Public Subnet  10.0.1.0/24  (us-east-1a) → ALB, NAT GW
    ├── Public Subnet  10.0.2.0/24  (us-east-1b) → ALB, NAT GW
    ├── Private Subnet 10.0.3.0/24  (us-east-1a) → App Servers
    ├── Private Subnet 10.0.4.0/24  (us-east-1b) → App Servers
    └── Private Subnet 10.0.5.0/24  (us-east-1a) → RDS PostgreSQL
        Private Subnet 10.0.6.0/24  (us-east-1b) → RDS PostgreSQL (Standby)

Internet Gateway → Public Subnets
NAT Gateway      → Private Subnets (outbound only)
VPN Gateway      → Site-to-Site VPN (Office ↔ Cloud)
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 18+ (for frontend tooling)

### 1. Clone & Setup
```bash
git clone https://github.com/your-org/sweet-factory.git
cd sweet-factory
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start with Docker Compose
```bash
docker-compose up --build
```

### 3. Run Database Migrations
```bash
docker-compose exec api alembic upgrade head
docker-compose exec api python scripts/seed_data.py
```

### 4. Access the Platform
| Service | URL |
|---------|-----|
| Frontend | http://localhost:80 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| pgAdmin | http://localhost:5050 |

**Default Admin Credentials:**
- Email: `admin@sweetfactory.com`
- Password: `Admin@2024!`

---

## 📁 Project Structure

```
sweet-factory/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # Route handlers
│   │   ├── services/             # Business logic
│   │   ├── repositories/         # Data access layer
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── core/                 # Config, security, database
│   │   └── middleware/           # Auth, logging, CORS
│   ├── tests/
│   ├── alembic/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── static/css/
│   ├── static/js/
│   └── templates/
├── nginx/
│   └── nginx.conf
├── infrastructure/
│   ├── aws/                      # CloudFormation templates
│   └── terraform/                # Terraform IaC
├── .github/workflows/            # CI/CD pipelines
├── docs/                         # Architecture diagrams, API docs
├── tests/load/                   # Load testing scripts
└── docker-compose.yml
```

---

## 🔐 Security Architecture

- **JWT Authentication** with refresh tokens
- **RBAC** (Role-Based Access Control) with 5 roles
- **HTTPS** enforced via ALB + ACM certificates
- **Security Groups** — least privilege principle
- **Private Subnets** — database never exposed to internet
- **Secrets Manager** — no hardcoded credentials
- **WAF** — Web Application Firewall on ALB

---

## 📊 API Modules

| Module | Base Path | Description |
|--------|-----------|-------------|
| Auth | `/api/v1/auth` | Login, logout, token refresh |
| ERP | `/api/v1/erp` | Production, batches, ingredients |
| CRM | `/api/v1/crm` | Customers, orders, distributors |
| WMS | `/api/v1/wms` | Warehouses, inventory, shipments |
| Dashboard | `/api/v1/dashboard` | Analytics & KPIs |

---

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Load tests (100 users)
locust -f tests/load/locustfile.py --users 100 --spawn-rate 10

# Load tests (2000 users)
locust -f tests/load/locustfile.py --users 2000 --spawn-rate 50
```

---

## ☁️ AWS Deployment

```bash
# Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file infrastructure/aws/main.yaml \
  --stack-name sweet-factory-prod \
  --capabilities CAPABILITY_IAM

# Or use Terraform
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

---

## 📈 Auto Scaling Policy

- **Scale Out**: CPU > 70% → Add 1 instance (max 10)
- **Scale In**: CPU < 30% → Remove 1 instance (min 2)
- **Cooldown**: 300 seconds

---

## 🎓 BTEC Learning Aims Coverage

| Criterion | Coverage |
|-----------|----------|
| A.P1 | Cloud network architectures (VPC, subnets) — `docs/network-architecture.md` |
| A.P2 | Network communication in cloud — API + Security Groups |
| A.M1 | Network standards comparison — `docs/cloud-comparison.md` |
| A.D1 | Cloud environment impact analysis — `docs/performance-analysis.md` |
| B.P3 | Remote OS services deployment — Docker + ECS deployment |
| B.P4 | Remote client ↔ cloud interaction — JWT auth flow |
| B.M2 | Remote optimization efficiency — Auto Scaling implementation |
| C.P5 | Network solution design — AWS CloudFormation templates |
| C.P6 | Network solution implementation — Working deployment |
| C.M3 | Performance & scalability testing — Locust load tests |
| C.D2 | Performance justification — Load test results |
| D.P7 | Network improvement recommendations — `docs/improvements.md` |
| D.P8 | Network improvements implementation — NGINX caching, CDN |
| D.M4 | Improvement testing — Performance benchmarks |
| D.D3 | Improvement justification — Before/after comparison |
