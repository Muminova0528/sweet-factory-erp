# Sweet Factory ERP — Cloud Network Architecture Report
## BTEC Level 3 IT Unit 6: Networking in the Cloud
### Learning Aims A & B — Network Architecture and Remote OS Services

---

## 1. Introduction

Sweet Factory is a UK-based confectionery manufacturer producing cakes, chocolates, and cookies. This document describes the cloud network architecture underpinning the company's Enterprise Resource Planning (ERP) system, covering the design rationale, networking standards, remote services, and client-cloud interaction protocols.

The ERP system consolidates Production Management, Customer Relationship Management (CRM), and Warehouse Management System (WMS) into a single cloud-native platform hosted on Amazon Web Services (AWS).

---

## 2. Cloud Network Architecture (A.P1, A.P2)

### 2.1 Architecture Overview

The Sweet Factory ERP uses a **three-tier cloud architecture** deployed within an AWS Virtual Private Cloud (VPC):

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS (443) / HTTP (80→443)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              ROUTE 53 (DNS + Health Checks)                      │
│              erp.sweetfactory.com → ALB                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌─────────── VPC: 10.0.0.0/16 ─────────────────────────────────────┐
│                                                                   │
│  ┌──── PUBLIC SUBNETS (DMZ) ──────────────────────────────────┐   │
│  │  10.0.1.0/24 (us-east-1a)   10.0.2.0/24 (us-east-1b)      │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────┐               │   │
│  │  │    Application Load Balancer (ALB)       │               │   │
│  │  │    • SSL/TLS Termination                 │               │   │
│  │  │    • Listener Rules (path-based routing) │               │   │
│  │  │    • WAF Integration                     │               │   │
│  │  └─────────────────────────────────────────┘               │   │
│  │                                                             │   │
│  │  ┌──────────────────┐  ┌──────────────────┐               │   │
│  │  │  NAT Gateway     │  │  Internet Gateway │               │   │
│  │  │  10.0.1.x        │  │  (IGW)            │               │   │
│  │  └──────────────────┘  └──────────────────┘               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                       │
│  ┌──── PRIVATE SUBNETS (Application Tier) ───────────────────┐   │
│  │  10.0.3.0/24 (us-east-1a)   10.0.4.0/24 (us-east-1b)      │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────┐               │   │
│  │  │    ECS Fargate Cluster                   │               │   │
│  │  │    • FastAPI Application (Docker)        │               │   │
│  │  │    • Auto Scaling: 2–10 tasks            │               │   │
│  │  │    • CPU Target: 70%                     │               │   │
│  │  └─────────────────────────────────────────┘               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                       │
│  ┌──── ISOLATED SUBNETS (Database Tier) ─────────────────────┐   │
│  │  10.0.5.0/24 (us-east-1a)   10.0.6.0/24 (us-east-1b)      │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────┐               │   │
│  │  │    RDS PostgreSQL 16 (Multi-AZ)          │               │   │
│  │  │    • Primary: us-east-1a                 │               │   │
│  │  │    • Standby: us-east-1b (auto-failover) │               │   │
│  │  │    • Encrypted at rest (AES-256)         │               │   │
│  │  └─────────────────────────────────────────┘               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──── VPN GATEWAY ──────────────────────────────────────────┐   │
│  │  Site-to-Site VPN → Factory Office (BGP routing)          │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

### 2.2 IP Addressing Scheme

| Subnet | CIDR Block | Availability Zone | Purpose |
|--------|-----------|-------------------|---------|
| Public A | 10.0.1.0/24 | us-east-1a | ALB, NAT Gateway |
| Public B | 10.0.2.0/24 | us-east-1b | ALB (HA), Bastion |
| Private A | 10.0.3.0/24 | us-east-1a | ECS Application |
| Private B | 10.0.4.0/24 | us-east-1b | ECS Application (HA) |
| DB A | 10.0.5.0/24 | us-east-1a | RDS Primary |
| DB B | 10.0.6.0/24 | us-east-1b | RDS Standby |

**Subnet sizing rationale:** /24 provides 251 usable IP addresses per subnet. The application layer (10.0.3.x and 10.0.4.x) can scale to 251 ECS tasks per subnet, well exceeding the Auto Scaling maximum of 10 concurrent tasks. Database subnets are deliberately isolated with no internet route.

**VPC CIDR 10.0.0.0/16** was chosen to avoid overlap with the factory office network (192.168.0.0/24) and provide room for future expansion.

### 2.3 Routing Architecture

**Internet Gateway (IGW):** Provides bidirectional internet access for public subnets. The ALB and NAT Gateway reside here.

**NAT Gateway:** Allows outbound-only internet access for private subnet instances (e.g., pulling Docker images from ECR, sending to CloudWatch). No inbound traffic is permitted through NAT, ensuring application servers are never directly reachable from the internet.

**Route Tables:**

| Route Table | Destination | Target |
|-------------|-------------|--------|
| Public RT | 0.0.0.0/0 | Internet Gateway |
| Private RT | 0.0.0.0/0 | NAT Gateway |
| Private RT | 10.0.0.0/16 | local |
| DB RT | 10.0.0.0/16 | local (only — no internet route) |

**VPN Gateway:** Enables encrypted site-to-site IPsec VPN from the Sweet Factory office to the VPC. BGP routing propagates the office CIDR (192.168.0.0/24) to the private route table, allowing office workstations to reach the ERP without traversing the public internet.

### 2.4 Security Groups

Security groups act as stateful virtual firewalls at the instance level:

**ALB Security Group:**
- Inbound: TCP 443 from 0.0.0.0/0 (HTTPS)
- Inbound: TCP 80 from 0.0.0.0/0 (redirect to HTTPS)
- Outbound: TCP 8000 to App SG

**Application Security Group:**
- Inbound: TCP 8000 from ALB SG only
- Inbound: TCP 22 from Bastion SG (SSH for debugging)
- Outbound: TCP 5432 to DB SG
- Outbound: TCP 443 to 0.0.0.0/0 (ECR, CloudWatch, Secrets Manager)

**Database Security Group:**
- Inbound: TCP 5432 from App SG only
- No outbound internet access

This implements **least-privilege network access**: the database is completely isolated from the internet, and the application layer is only reachable through the load balancer.

---

## 3. Network Standards and Protocols (A.P2, A.M1)

### 3.1 Transport Layer Security

The ERP enforces **TLS 1.2/1.3** for all client-facing communications:

- **TLS 1.3** (preferred): Reduces handshake latency with 1-RTT (one round-trip time) versus TLS 1.2's 2-RTT. Eliminates deprecated cipher suites.
- **Certificate:** AWS Certificate Manager (ACM) issues an RSA-2048 certificate for `erp.sweetfactory.com`, auto-renewed 60 days before expiry.
- **Cipher suites supported:** TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256

**HTTP Strict Transport Security (HSTS):** All responses include `Strict-Transport-Security: max-age=31536000; includeSubDomains`, preventing browsers from attempting HTTP connections in future.

### 3.2 Application Layer Protocols

**REST over HTTP/1.1 and HTTP/2:**
- The ALB supports HTTP/2 between client and ALB, upgrading connection multiplexing.
- FastAPI endpoints follow RESTful conventions: resources are nouns (`/api/v1/products`), HTTP verbs define operations (GET, POST, PUT, DELETE).
- JSON (RFC 8259) is used for request/response payloads.
- Pagination follows cursor-based patterns: `?page=1&limit=20`.

**JWT Authentication (RFC 7519):**
- Access tokens expire in 30 minutes; refresh tokens in 7 days.
- Signed with HS256 (HMAC-SHA256).
- Transmitted via `Authorization: Bearer <token>` header — never in cookies or URLs.

**WebSocket consideration:** Real-time dashboard updates could use WebSocket (RFC 6455). Currently implemented via polling every 30 seconds; WebSocket upgrade is planned for v2.1.

### 3.3 Network Time Protocol (NTP)

All ECS tasks synchronize clocks with AWS Time Sync Service (169.254.169.123), an NTP server based on GPS and atomic clocks. This ensures log timestamps, JWT expiry calculations, and audit trail records are consistent across all instances.

### 3.4 DNS Resolution

Route 53 hosts the `sweetfactory.com` zone:
- `erp.sweetfactory.com` → ALB DNS name (A record alias)
- `api.sweetfactory.com` → Same ALB, different path rule
- Health checks every 30 seconds; failover routing for disaster recovery.

### 3.5 Quality of Service (QoS) and Rate Limiting

NGINX rate limiting protects against denial-of-service and brute-force:
- API endpoints: 100 requests per minute per IP
- Authentication: 10 requests per minute per IP (prevents password spraying)

AWS WAF rules block known malicious IP ranges, SQL injection patterns, and XSS attempts.

---

## 4. Remote OS Services (B.P3, B.P4)

### 4.1 Container-Based Compute: AWS ECS Fargate

Rather than provisioning EC2 virtual machines, Sweet Factory uses **AWS ECS Fargate** — a serverless container runtime. This means:

- **No OS to manage:** Fargate handles the underlying host OS, patching, and kernel updates.
- **Task isolation:** Each container task runs in its own micro-VM (Firecracker technology), providing kernel-level isolation.
- **Resource specification:** Each task is allocated 0.5 vCPU and 1GB RAM. At peak load (10 tasks), total capacity is 5 vCPU and 10GB RAM.

The containerised FastAPI application runs on Python 3.12 with Uvicorn ASGI server (4 worker processes per container).

### 4.2 Docker Container Architecture

```dockerfile
# Multi-stage build
FROM python:3.12-slim AS builder   # Build stage: install dependencies
FROM python:3.12-slim AS production # Runtime: copy only what's needed

# Non-root user for security
RUN useradd -m sweetfactory
USER sweetfactory

# Uvicorn with 4 workers
CMD ["uvicorn", "app.main:app", "--workers", "4"]
```

**Multi-stage builds** reduce the final image size from ~800MB to ~180MB by excluding build tools (compilers, pip cache) from the production image.

### 4.3 Database: PostgreSQL on RDS

AWS RDS manages the PostgreSQL instance as a fully managed service:

| Feature | Configuration |
|---------|---------------|
| Engine | PostgreSQL 16.x |
| Instance | db.t3.medium (2 vCPU, 4GB RAM) |
| Storage | 100GB gp3 SSD, autoscaling to 500GB |
| Multi-AZ | Enabled (synchronous replication to standby) |
| Backup | Automated daily snapshots, 7-day retention |
| Encryption | AES-256 at rest (AWS KMS) |
| SSL | Required for all connections (ssl-mode=require) |

**Connection pooling:** The application uses SQLAlchemy's async engine with `pool_size=20` and `max_overflow=40`, limiting maximum concurrent DB connections to 60 per task (600 total at max scale). PostgreSQL `max_connections` is set to 200, so connection pooling is critical to prevent exhaustion.

### 4.4 NGINX Reverse Proxy

NGINX acts as a reverse proxy between the ALB and FastAPI:

```nginx
upstream sweetfactory_api {
    least_conn;           # Route to least-loaded upstream
    server api:8000;
    keepalive 64;         # Maintain persistent connections
}
```

NGINX provides:
- **SSL termination** (in local dev; ALB handles this in production)
- **Gzip compression:** Reduces payload size by 60-80% for JSON responses
- **Response caching:** GET requests cached for 60 seconds
- **Security headers:** X-Frame-Options, Content-Security-Policy, X-XSS-Protection

### 4.5 Secrets Management

Sensitive credentials (DB passwords, JWT secrets, API keys) are stored in **AWS Secrets Manager**, not in environment variables or code:

1. Secrets Manager stores the credential encrypted with AES-256 (KMS).
2. ECS task role has IAM permission to read specific secrets via `secretsmanager:GetSecretValue`.
3. Application retrieves secrets at startup via AWS SDK.
4. Automatic rotation every 90 days (DB password rotation supported natively).

This eliminates credential leakage through environment variable exposure or container image scanning.

---

## 5. Client-Cloud Interaction (B.P4, B.M2)

### 5.1 Request Flow Diagram

```
Browser/Client
     │
     │ HTTPS Request (TLS 1.3)
     ▼
Route 53 (DNS resolution)
     │
     ▼
Application Load Balancer
     │ • SSL termination
     │ • Health check routing (only healthy targets)
     │ • Path-based rules (/api/* → API target group)
     ▼
ECS Fargate Task (FastAPI)
     │ • JWT validation
     │ • Business logic
     │ • Input validation (Pydantic)
     ▼
RDS PostgreSQL
     │ • Async query execution
     │ • Connection pool
     ▼
     │ JSON Response
     ▼
Client Browser
```

### 5.2 Authentication Flow

```
1. Client sends: POST /api/v1/auth/login
   Body: {"username": "admin", "password": "Admin@123!"}

2. Server:
   a. Looks up user by username (UserRepository)
   b. Verifies bcrypt hash (passlib)
   c. If valid, creates JWT access token (30min) + refresh token (7d)
   d. Returns: {"access_token": "eyJ...", "token_type": "bearer"}

3. Client stores tokens in memory (not localStorage for XSS protection)

4. Subsequent requests:
   GET /api/v1/erp/products
   Authorization: Bearer eyJ...

5. Server middleware validates JWT:
   a. Decode header.payload.signature
   b. Verify signature with SECRET_KEY
   c. Check exp (expiry) claim
   d. Load user from database
   e. Inject user into request context

6. When access token expires:
   POST /api/v1/auth/refresh
   Body: {"refresh_token": "eyJ..."}
   → Returns new access token
```

### 5.3 API Response Standards

All API responses follow consistent patterns:

**Success (200/201):**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "limit": 20,
  "pages": 3
}
```

**Error (4xx/5xx):**
```json
{
  "detail": "Product with SKU 'CAKE-001' already exists",
  "status_code": 409
}
```

**Validation Error (422):**
```json
{
  "detail": [
    {"loc": ["body", "unit_price"], "msg": "must be positive", "type": "value_error"}
  ]
}
```

### 5.4 Optimisation Techniques (B.M2)

**Database Query Optimisation:**
- Async SQLAlchemy prevents blocking I/O: while one query awaits DB, other requests are processed.
- Indexed columns: email, username, SKU, order status, created_at for range queries.
- Eager loading with `selectinload` avoids N+1 query problems on relational data.

**Caching Strategy:**
- NGINX caches GET responses for 60 seconds: reduces DB load for frequently-read data.
- Future: Redis layer for session data and computed dashboard statistics.

**Payload Optimisation:**
- Gzip compression reduces JSON payload by ~70%.
- Pagination prevents unbounded result sets from overwhelming memory.
- Field selection: endpoints return only necessary fields, not full ORM objects.

**Connection Pooling:**
- SQLAlchemy pool (size=20, overflow=40) reuses established DB connections.
- NGINX `keepalive 64` maintains persistent HTTP/1.1 connections to upstream.

**Auto Scaling:**
- ALB target tracking scales ECS tasks when CPU exceeds 70%.
- Scale-in when CPU drops below 30% for 5 minutes (cooldown prevents oscillation).
- Minimum 2 tasks ensure high availability; maximum 10 tasks control cost.

---

## 6. Comparison of Cloud Network Architectures (A.M1)

### 6.1 Architecture Patterns Evaluated

| Architecture | Description | Sweet Factory Fit |
|-------------|-------------|------------------|
| Monolithic VM | Single EC2 instance, all components | ✗ Single point of failure, no scaling |
| Microservices + K8s | Separate services per domain, Kubernetes | ✗ Over-complex for current scale |
| **3-Tier on ECS** | ALB + Fargate + RDS, chosen approach | ✓ Balance of simplicity and scale |
| Serverless (Lambda) | Function-per-endpoint, no servers | ✗ Cold start latency unacceptable for ERP |
| Multi-Region Active-Active | Two regions, Route 53 failover | ✗ Cost-prohibitive for SME |

### 6.2 Cloud Provider Comparison

| Feature | AWS | Azure | Google Cloud |
|---------|-----|-------|--------------|
| Container orchestration | ECS Fargate | ACI / AKS | Cloud Run / GKE |
| Managed PostgreSQL | RDS | Azure Database | Cloud SQL |
| Load balancing | ALB | Application GW | Cloud Load Balancing |
| DNS | Route 53 | Azure DNS | Cloud DNS |
| VPN Gateway | Site-to-Site VPN | VPN Gateway | Cloud VPN |
| WAF | AWS WAF | Azure WAF | Cloud Armor |
| **Market share (2025)** | **31%** | **25%** | **12%** |
| UK data centres | ✓ eu-west-2 (London) | ✓ UK South | ✓ europe-west2 |

**AWS was selected** due to market leadership, the widest service ecosystem, mature documentation, and the team's existing AWS certifications. The `eu-west-2` (London) region also satisfies UK GDPR data residency requirements.

### 6.3 Network Topology: Star vs Mesh

The Sweet Factory architecture uses a **hub-and-spoke (star) topology**:
- Hub: VPC with centralised routing
- Spokes: Factory office (via VPN), external users (via internet)

An alternative **mesh topology** would connect all offices directly via VPN peering — appropriate if Sweet Factory opens multiple facilities, but unnecessary for the current single-site operation.

---

## 7. Advantages and Limitations (A.D1)

### 7.1 Advantages

**Scalability:** ECS Auto Scaling responds to demand within 90 seconds. During peak periods (e.g., Christmas confectionery orders), capacity increases automatically without manual intervention.

**High Availability:** Multi-AZ deployment means a full availability zone failure (data centre outage) causes automatic RDS failover in under 60 seconds, with ALB routing only to healthy ECS tasks.

**Security:** Network segmentation (public/private/DB subnets), least-privilege security groups, WAF, TLS everywhere, and Secrets Manager constitute defence-in-depth.

**Managed Services:** RDS eliminates DBA overhead (patching, backups, failover). Fargate eliminates OS management. The team focuses on application development.

**Cost Efficiency:** Pay-per-use Fargate (charged per vCPU-second) versus always-on EC2. At 2 tasks off-peak and 10 at peak, costs scale with actual usage.

### 7.2 Limitations

**Vendor Lock-in:** AWS-specific services (RDS, ECS, Route 53) create migration complexity. Mitigation: containerised application is portable; database is standard PostgreSQL.

**Latency for VPN Users:** Factory office users access ERP via VPN, adding ~5-15ms latency compared to direct connection. Acceptable for ERP use cases.

**Cold Start Latency:** Fargate task startup takes 30-60 seconds. Auto Scaling minimum of 2 tasks prevents cold starts reaching end users.

**Cost at Scale:** At maximum 10 tasks running 24/7, monthly Fargate cost is approximately £180/month (0.04048 vCPU-hour × 10 tasks × 720 hours). RDS Multi-AZ adds approximately £120/month. Total infrastructure ~£380/month, appropriate for the business scale.

---

*Document covers BTEC Unit 6 Learning Aims A.P1, A.P2, A.M1, A.D1, B.P3, B.P4, B.M2*
*Sweet Factory ERP Project — Academic Year 2025–2026*
